#!/usr/bin/env python3
"""Locus autopilot: run the sprint's stories unattended until the first thing that needs the OWNER.

    py -3 tools\\tracker\\autopilot.py --author-model <slug> --verifier-model <slug> [--max-steps 6] [--max-minutes 180] [--dry-run]

One step = one fresh headless `agy -p` session (Google Antigravity CLI) or one mechanical git/tool command. No session remembers
anything: the state lives in git and tracker/, and `backlog.py` (the board) derives it again before every step. This script only
dispatches what the board's NEXT ACTION would tell the owner to do; it never decides anything itself:

    TODO     --start US-nn, then the AUTHOR (model A) with prompt P1 + P6
    DOING    the AUTHOR again (prompt P1 + P6)
    VERIFY   the VERIFIER (a different model family) with prompt P2 + P7
    REWORK   the AUTHOR fixes the numbered findings, then the VERIFIER checks again (at most 2 rounds)
    MERGE    commit the verdict, guard --full, then merge --ff-only, verify.py, export_xlsx.py, commit the tracker (the board's MERGE steps)

It STOPS (exit 0) at every owner gate: no active sprint (planning), the sprint ended (review, retro), nothing left to start,
unanswered questions in tracker/handoff/US-nn-questions.md, the step or time budget, or the file tracker/.cache/STOP.
It STOPS (exit 1) on anything unexpected: an agent that fails, times out, does not return the Locus canary (AGENTS.md was not
loaded), makes no progress twice, a red guard, a refused board command. It refuses to start (exit 2) unless the commit hooks are on,
the guard shows 0 FAIL, the two models are different families, the owner variable LOCUS_ALLOW_GUARD_EDIT is NOT set, and a one-line
smoke question to each model returns the canary within 3 minutes (`agy -p` has hung without a terminal on some versions).
It never plans, accepts, retros, closes a sprint, pushes, or passes the owner variable or anything that looks like a key to an agent.
Every step is appended to tracker/.cache/autopilot.log.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import backlog as B  # noqa: E402  (this also puts tools/ on sys.path for locus_common)

OWNER_VAR = "LOCUS_ALLOW_GUARD_EDIT"
SECRET_ENV = re.compile(r"(TOKEN|SECRET|PASSWORD|PASSWD|API_?KEY)", re.I)
UNANSWERED = re.compile(r"^\s*Answer:\s*$", re.M)
CANARY_RX = re.compile(r"answer exactly `([^`]+)`")
MAX_PROMPT_CHARS = 28000  # the Windows command line is limited to 32767 characters
SMOKE_PROMPT = ("What is the Locus canary? Answer with the phrase from AGENTS.md and nothing else. "
                "Do not run any command and do not create or edit any file.")
INSTALL_HINT = "Install it with:  irm https://antigravity.google/cli/install.ps1 | iex   then run  agy  once to sign in, and close it."


class Stop(Exception):
    """End of the run. code 0 = an owner gate or a budget, 1 = something unexpected, 2 = refused to start."""

    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code, self.message = code, message


def parse_envelope(text: str) -> dict | None:
    """The JSON envelope `agy -p --output-format json` prints. Tolerates a banner or an update notice around it."""
    text = (text or "").strip()
    candidates = [text]
    lo, hi = text.find("{"), text.rfind("}")
    if 0 <= lo < hi:
        candidates.append(text[lo:hi + 1])
    candidates += [ln.strip() for ln in reversed(text.splitlines()) if ln.strip().startswith("{")]
    for c in candidates:
        try:
            data = json.loads(c)
        except ValueError:
            continue
        if isinstance(data, dict) and "status" in data:
            return data
    return None


def tail(text: str, n: int = 400) -> str:
    text = (text or "").strip()
    return text if len(text) <= n else "..." + text[-n:]


def sh(cmd: list[str], root: Path, timeout: int = 900, env: dict | None = None) -> tuple[int, str, str]:
    try:
        p = subprocess.run(cmd, cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=timeout, stdin=subprocess.DEVNULL, env=env)
    except subprocess.TimeoutExpired:
        return 124, "", f"timed out after {timeout}s: {' '.join(cmd[:3])}"
    return p.returncode, p.stdout or "", p.stderr or ""


def git(root: Path, *args: str) -> tuple[int, str, str]:
    return sh(["git", *args], root, timeout=120)


def tool(root: Path, rel: str, *args: str) -> list[str]:
    return [sys.executable, str(root / "tools" / rel), *args]


class Log:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)

    def add(self, **kv) -> None:
        kv = {"at": datetime.now().isoformat(timespec="seconds"), **kv}
        with self.path.open("a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(kv, ensure_ascii=False) + "\n")


def say(msg: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


# --------------------------------------------------------------------------- before the first step
def resolve_agy(spec: str) -> list[str]:
    parts = shlex.split(spec, posix=(os.name != "nt"))
    if not parts:
        raise Stop(2, "--agy is empty")
    exe = shutil.which(parts[0]) or (parts[0] if Path(parts[0]).is_file() else None)
    if not exe:
        raise Stop(2, f"agy was not found. {INSTALL_HINT}")
    if os.name == "nt" and exe.lower().endswith((".cmd", ".bat")):
        raise Stop(2, f"{exe} is a .cmd/.bat shim: cmd.exe would misread characters such as % & | < > in the prompts. Use the agy.exe the installer puts on PATH.")
    return [exe, *parts[1:]]


def canary_of(root: Path) -> str:
    p = root / "AGENTS.md"
    m = CANARY_RX.search(p.read_text(encoding="utf-8", errors="replace")) if p.is_file() else None
    if not m:
        raise Stop(2, "AGENTS.md has no line saying: answer exactly `<canary>`. The autopilot needs it to prove the agent loaded the rules.")
    return m.group(1)


def preflight(ctx: B.Ctx, args, agy: list[str] | None, log: Log) -> str:
    if os.environ.get(OWNER_VAR):
        raise Stop(2, f"{OWNER_VAR} is set in this window. The autopilot never runs with the owner variable.  Remove-Item Env:{OWNER_VAR}")
    fa, fv = B.family(args.author_model), B.family(args.verifier_model)
    if not fa or not fv or fa == fv:
        raise Stop(2, f"--author-model ({args.author_model}) and --verifier-model ({args.verifier_model}) must be different model families "
                      "(AGENTS.md law 12: the author never verifies), for example a Claude model and a Gemini model.")
    if not ctx.hooks_on():
        raise Stop(2, "the commit hooks are off. The autopilot runs only after the guard showed 0 FAIL and you turned them on:  git config core.hooksPath .githooks")
    canary = canary_of(ctx.root)
    if agy is not None:
        if not args.skip_model_check:
            rc, out, err = sh([*agy, "models"], ctx.root, timeout=120)
            if rc != 0:
                raise Stop(2, "`agy models` failed (not signed in?). Run  agy  once, sign in, close it. " + tail(err or out))
            for m in (args.author_model, args.verifier_model):
                if m not in out:
                    raise Stop(2, f"model '{m}' is not in the output of  agy models:\n{tail(out, 800)}")
        rc, out, err = sh(tool(ctx.root, "guard/check.py", "--full"), ctx.root, timeout=600)
        if rc != 0:
            raise Stop(2, "the guard shows FAIL before the first step. Fix those first (py -3 tools\\guard\\check.py --full names each one).\n" + tail(out, 800))
        if args.smoke_seconds > 0:
            smoke(ctx, args, agy, canary, log)
    return canary


# --------------------------------------------------------------------------- choosing the next action from the board
def refresh(root: Path, today: date) -> tuple[B.Ctx, dict]:
    ctx = B.Ctx(root, today)
    return ctx, B.derive(ctx)


def in_progress(ctx: B.Ctx, states: dict) -> list[str]:
    return [s["id"] for s in ctx.stories if states[s["id"]]["state"] in B.IN_PROGRESS]


def by_hand(ctx: B.Ctx, sid: str) -> None:
    if ctx.by_id[sid].get("autopilot") is False:
        raise Stop(0, f"{sid} is marked 'autopilot: false' in tracker/backlog.yaml: it needs you at the keyboard (it deletes folders, needs a real key, "
                      "a VM or a bot, or starts other programs). Do it by hand with the board (py -3 tools\\tracker\\backlog.py); the autopilot carries on after it is merged.")


def decide(ctx: B.Ctx, states: dict) -> tuple[str, str]:
    sv = B.sprint_view(ctx)
    if sv is None:
        raise Stop(0, "no sprint is active: planning is yours (py -3 tools\\tracker\\backlog.py prints the steps)")
    if ctx.today > sv["end"]:
        raise Stop(0, f"sprint {sv['id']} ended on {B.fmt(sv['end'])}: hold the review and the retro, close it, then plan the next one (the board prints the steps)")
    bad = [sid for sid, i in states.items() if i["state"] == "ANOMALY"]
    if bad:
        raise Stop(1, f"{', '.join(bad)} reached {ctx.main} without a complete handoff and an ACCEPT from another model: run what the board prints for ANOMALY")
    wip = in_progress(ctx, states)
    if len(wip) > 1:
        raise Stop(1, f"more than one story is in progress ({', '.join(wip)}); AGENTS.md law 12 allows one")
    if wip:
        sid = wip[0]
        by_hand(ctx, sid)
        return {"DOING": "author", "REWORK": "rework", "VERIFY": "verify", "MERGE": "merge"}[states[sid]["state"]], sid
    for sid in sv["stories"]:
        if sid in states and states[sid]["state"] == "TODO":
            by_hand(ctx, sid)
            return "start", sid
    waiting = [s["id"] for s in ctx.stories if states[s["id"]]["state"] == "REVIEW"]
    raise Stop(0, f"nothing is left to start in sprint {sv['id']}. Waiting for your demo: {', '.join(waiting) or 'none'}")


def stand_on_branch(ctx: B.Ctx, states: dict, sid: str) -> tuple[B.Ctx, dict]:
    br = states[sid]["branch"]
    if not br:
        raise Stop(1, f"{sid} has no branch task/{sid}-*")
    if ctx.cur != br:
        if ctx.dirty():
            raise Stop(1, f"uncommitted files on '{ctx.cur}' ({', '.join(ctx.dirty()[:4])}): the autopilot will not switch to {br} over them")
        rc, out, err = git(ctx.root, "switch", br)
        if rc != 0:
            raise Stop(1, f"git switch {br} failed: {tail(err or out)}")
        return refresh(ctx.root, ctx.today)
    return ctx, states


# --------------------------------------------------------------------------- one agent session
def clean_env(extra_keep: list[str]) -> dict:
    keep = {k.upper() for k in extra_keep}
    return {k: v for k, v in os.environ.items() if k != OWNER_VAR and (k.upper() in keep or not SECRET_ENV.search(k))}


def call_agent(args, agy: list[str], root: Path, model: str, prompt: str, canary: str, log: Log, label: str, limit_s: int | None = None) -> str:
    if len(prompt) > MAX_PROMPT_CHARS:
        raise Stop(1, f"{label}: the prompt has {len(prompt)} characters, more than a Windows command line takes ({MAX_PROMPT_CHARS}). Split the story.")
    timeout_s = limit_s or (args.agent_minutes + 5) * 60
    print_min = args.agent_minutes if limit_s is None else max(1, -(-limit_s // 60))
    cmd = [*agy, "-p", prompt, "--model", model, "--output-format", "json", "--print-timeout", f"{print_min}m", *shlex.split(args.agy_args)]
    t0 = time.time()
    try:
        p = subprocess.run(cmd, cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=timeout_s, stdin=subprocess.DEVNULL, env=clean_env(args.pass_env))
    except subprocess.TimeoutExpired:
        log.add(step=label, model=model, result="timeout")
        waited = f"{timeout_s // 60} minutes" if timeout_s % 60 == 0 else f"{timeout_s} seconds"
        raise Stop(1, f"{label}: agy did not answer within {waited} and was stopped. If it prints nothing until the timeout, "
                      "update agy (re-run its installer): a hang of `agy -p` without a terminal was reported on some versions.")
    secs = round(time.time() - t0)
    rec = {"step": label, "model": model, "rc": p.returncode, "seconds": secs, "stderr": tail(p.stderr, 1500), "stdout": tail(p.stdout, 1500)}
    if p.returncode != 0:
        log.add(**rec, result="agy failed")
        raise Stop(1, f"{label}: agy exited {p.returncode}: {tail(p.stderr or p.stdout)}")
    data = parse_envelope(p.stdout)
    if data is None:
        log.add(**rec, result="not json")
        raise Stop(1, f"{label}: agy did not print the JSON envelope (--output-format json): {tail(p.stdout)}")
    status = data.get("status")
    resp = str(data.get("response") or "")
    rec |= {"conversation_id": data.get("conversation_id"), "status": status, "response": tail(resp, 600)}
    if status != "SUCCESS":
        log.add(**rec, result="status")
        raise Stop(1, f"{label}: agy status {status}: {tail(str(data.get('error') or resp))}")
    if canary not in resp:
        log.add(**rec, result="no canary")
        raise Stop(1, f"{label}: the reply did not contain the Locus canary, so the agent did not load AGENTS.md. Run again with --inline-rules, "
                      "or open the folder locus-os (not 5_Locus) as the workspace.")
    if re.search(r"refus|denied|not permitted", p.stderr, re.I):
        say(f"note: agy reported a refused tool call; see {log.path.name}")
    log.add(**rec, result="ok")
    return resp


def smoke(ctx: B.Ctx, args, agy: list[str], canary: str, log: Log) -> None:
    """Two one-line sessions before any work: does `agy -p` return at all when it has no terminal (it has hung on some versions and
    machines), does each model slug answer, and does each session load AGENTS.md from this folder?"""
    for who, model in (("author", args.author_model), ("verifier", args.verifier_model)):
        say(f"smoke test: asking {model} (the {who}) for the canary")
        try:
            call_agent(args, agy, ctx.root, model, rules_text(ctx, args) + SMOKE_PROMPT, canary, log, f"smoke {who}", limit_s=args.smoke_seconds)
        except Stop as e:
            raise Stop(2, f"the smoke test failed and nothing was started. {e.message}\n"
                          "The test is one line long. If it hangs, `agy -p` does not work without a terminal on this machine or agy version: "
                          "update agy and try again; otherwise use the manual flow in the RUNBOOK (nothing is lost).") from None


def rules_text(ctx: B.Ctx, args) -> str:
    if not args.inline_rules:
        return ""
    return "The rules of this repository follow (AGENTS.md). They bind you:\n\n" + (ctx.root / "AGENTS.md").read_text(encoding="utf-8", errors="replace") + "\n\n"


def unanswered_questions(root: Path, sid: str) -> Path | None:
    q = root / "tracker" / "handoff" / f"{sid}-questions.md"
    if q.is_file() and UNANSWERED.search(q.read_text(encoding="utf-8", errors="replace")):
        return q
    return None


def author_prompt(ctx: B.Ctx, states: dict, args, sid: str, rework: bool) -> str:
    s, info = ctx.by_id[sid], states[sid]
    p1 = B.render_prompt(ctx, "P1", B.story_mapping(ctx, s, info), f"{sid}-P1", s.get("addendum") or None)
    p6 = B.render_prompt(ctx, "P6", {"STORY": sid}, f"{sid}-P6")
    text = rules_text(ctx, args) + p1.read_text(encoding="utf-8") + "\n\n" + p6.read_text(encoding="utf-8")
    if rework:
        text += (f"\nREWORK. The verifier did not accept the previous attempt. Read tracker/handoff/{sid}-verify.md. Fix exactly its numbered findings and "
                 f"nothing else, update your handoff (Commands run, Not done), commit, and reply DONE {sid}.\n")
    q = ctx.root / "tracker" / "handoff" / f"{sid}-questions.md"
    if q.is_file():
        text += f"\nThe owner answered your earlier questions in tracker/handoff/{sid}-questions.md. Follow those answers.\n"
    return text


def verifier_model(args, author_family: str) -> str:
    for m in (args.verifier_model, args.author_model):
        if B.family(m) != author_family:
            return m
    raise Stop(1, f"both models are the same family as the author ({author_family}); a verifier of another family is needed")


def do_author(ctx, states, args, agy, canary, log, sid: str, rework: bool) -> bool:
    ctx, states = stand_on_branch(ctx, states, sid)
    q = unanswered_questions(ctx.root, sid)
    if q:
        raise Stop(0, f"waiting for your answers: fill in every 'Answer:' line of {q.relative_to(ctx.root).as_posix()}, then run the autopilot again")
    before = git(ctx.root, "rev-parse", "HEAD")[1].strip()
    prompt = author_prompt(ctx, states, args, sid, rework)
    say(f"{'REWORK' if rework else 'AUTHOR'} {sid} with {args.author_model}")
    call_agent(args, agy, ctx.root, args.author_model, prompt, canary, log, f"author {sid}")
    ctx, states = refresh(ctx.root, ctx.today)
    q = unanswered_questions(ctx.root, sid)
    if q:
        raise Stop(0, f"{sid}: the author has questions only you can answer: {q.relative_to(ctx.root).as_posix()} (fill in every 'Answer:' line, then run the autopilot again)")
    after = git(ctx.root, "rev-parse", "HEAD")[1].strip()
    state = states[sid]["state"]
    ok = (after != before) if rework else (state == "VERIFY")
    say(f"  {sid} is now {state}" + ("" if ok else " (no progress)"))
    return ok


def do_verify(ctx, states, args, agy, canary, log, sid: str) -> bool:
    ctx, states = stand_on_branch(ctx, states, sid)
    info = states[sid]
    if info["state"] not in ("VERIFY", "REWORK"):
        raise Stop(1, f"{sid} is {info['state']}; the handoff must be complete before a verifier runs")
    model = verifier_model(args, info["author"])
    s = ctx.by_id[sid]
    p2 = B.render_prompt(ctx, "P2", B.story_mapping(ctx, s, info), f"{sid}-P2")
    p7 = B.render_prompt(ctx, "P7", {"STORY": sid}, f"{sid}-P7")
    prompt = rules_text(ctx, args) + p2.read_text(encoding="utf-8") + "\n\n" + p7.read_text(encoding="utf-8")
    say(f"VERIFY {sid} with {model}")
    call_agent(args, agy, ctx.root, model, prompt, canary, log, f"verify {sid}")
    ctx, states = refresh(ctx.root, ctx.today)
    state = states[sid]["state"]
    ok = state in ("MERGE", "REWORK")
    say(f"  {sid} is now {state}" + ("" if ok else " (no valid verdict: " + "; ".join(states[sid]["notes"]) + ")"))
    return ok


def commit_verdict(root: Path, sid: str, log: Log) -> None:
    """The verifier leaves its verdict uncommitted, and an author's `git add -A` may already have swept an older verdict into a commit.
    Commit the final one on the story branch: it then travels with the merge, and `git switch` finds a clean tree."""
    vf = f"tracker/handoff/{sid}-verify.md"
    rc, out, err = git(root, "status", "--porcelain", "--untracked-files=all", "--", vf)
    if rc != 0 or not out.strip():
        return
    for cmd in (["add", "--", vf], ["commit", "-m", f"chore(tracker): verdict for {sid}", "--", vf]):
        rc, out, err = git(root, *cmd)
        log.add(step=f"git {cmd[0]} verdict {sid}", rc=rc, stdout=tail(out, 400), stderr=tail(err, 400))
        if rc != 0:
            raise Stop(1, f"{sid}: could not commit {vf} ({tail(err or out)})")


def do_merge(ctx, states, log, sid: str) -> None:
    ctx, states = stand_on_branch(ctx, states, sid)
    br, root = states[sid]["branch"], ctx.root
    if states[sid]["state"] != "MERGE":
        raise Stop(1, f"{sid} is {states[sid]['state']}, not MERGE")
    say(f"MERGE {sid}")
    commit_verdict(root, sid, log)
    rc, out, err = sh(tool(root, "guard/check.py", "--full"), root, timeout=600)
    log.add(step=f"guard {sid}", rc=rc, stdout=tail(out, 1500))
    if rc != 0:
        raise Stop(1, f"{sid}: the guard shows FAIL on {br}; nothing was merged:\n{tail(out, 900)}")
    steps = [("git switch", ["git", "switch", ctx.main]),
             ("git merge --ff-only", ["git", "merge", "--ff-only", br]),
             ("git branch -d", ["git", "branch", "-d", br]),
             ("verify.py", tool(root, "tracker/verify.py")),
             ("export_xlsx.py", tool(root, "tracker/export_xlsx.py")),
             ("git add tracker", ["git", "add", "tracker"])]
    regressions: list[str] = []
    for name, cmd in steps:
        rc, out, err = sh(cmd, root, timeout=1800)
        log.add(step=f"{name} {sid}", rc=rc, stdout=tail(out, 600), stderr=tail(err, 600))
        if rc != 0:
            raise Stop(1, f"{sid}: '{name}' failed ({tail(err or out)}); fix it by hand, then run  py -3 tools\\tracker\\backlog.py")
        if name == "verify.py":
            regressions = [ln.strip() for ln in out.splitlines() if ln.startswith("REGRESSION")]
    rc, out, err = git(root, "commit", "-m", f"chore(tracker): refresh after {sid}")
    log.add(step=f"git commit {sid}", rc=rc, stdout=tail(out, 400), stderr=tail(err, 400))
    if rc != 0 and "nothing to commit" not in (out + err):
        raise Stop(1, f"{sid}: the tracker commit failed ({tail(err or out)}); the story is merged, commit tracker/ by hand")
    say(f"  {sid} merged into {ctx.main}")
    if regressions:
        raise Stop(1, f"{sid} is merged, but a feature went DOWN: " + " | ".join(regressions[:4]) + " . Nothing further was started; decide what to do first.")


# --------------------------------------------------------------------------- the loop
def run(args) -> int:
    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[2]
    today = B.as_date(args.today) if args.today else date.today()
    log = Log(root / "tracker" / ".cache" / "autopilot.log")
    stop_file = root / "tracker" / ".cache" / "STOP"
    t0, steps = time.time(), 0
    attempts: dict[tuple[str, str], int] = {}
    rounds: dict[str, int] = {}
    try:
        ctx, states = refresh(root, today)
        agy = None if args.dry_run else resolve_agy(args.agy)
        canary = preflight(ctx, args, agy, log)
        say(f"autopilot starts: author {args.author_model}, verifier {args.verifier_model}, at most {args.max_steps} steps / {args.max_minutes} minutes."
            f" Stop it with:  New-Item {stop_file.relative_to(root)}")
        while True:
            if stop_file.exists():
                raise Stop(0, f"the STOP file exists ({stop_file.relative_to(root)}); delete it before the next run")
            if steps >= args.max_steps:
                raise Stop(0, f"the step budget is used ({args.max_steps}); run it again for more")
            if (time.time() - t0) / 60 >= args.max_minutes:
                raise Stop(0, f"the time budget is used ({args.max_minutes} minutes); run it again for more")
            ctx, states = refresh(root, today)
            kind, sid = decide(ctx, states)
            if kind != "start":
                ctx, states = stand_on_branch(ctx, states, sid)
                kind, sid = decide(ctx, states)
            if args.dry_run:
                raise Stop(0, f"DRY RUN: the next action would be {kind.upper()} {sid} ({ctx.by_id[sid].get('title', '')}). Nothing was changed and no agent was called.")
            if kind == "start":
                rc, out, err = sh([sys.executable, str(root / "tools" / "tracker" / "backlog.py"), "--start", sid, "--today", today.isoformat()], root)
                log.add(step=f"start {sid}", rc=rc, stdout=tail(out, 800))
                if rc != 0:
                    raise Stop(1, f"the board refused to start {sid}: {tail(out)}")
                say(f"START {sid}")
                ctx, states = refresh(root, today)
                kind = "author"
            key = (sid, kind)
            if kind == "rework":
                rounds[sid] = rounds.get(sid, 0) + 1
                if rounds[sid] > 2:
                    raise Stop(1, f"{sid}: the verifier did not accept it after 2 rounds of rework; read tracker/handoff/{sid}-verify.md and decide")
                steps += 1
                if not do_author(ctx, states, args, agy, canary, log, sid, rework=True):
                    raise Stop(1, f"{sid}: the author made no commit while fixing the findings")
                ctx, states = refresh(root, today)
                steps += 1
                ok = do_verify(ctx, states, args, agy, canary, log, sid)
            elif kind == "author":
                steps += 1
                ok = do_author(ctx, states, args, agy, canary, log, sid, rework=False)
            elif kind == "verify":
                steps += 1
                ok = do_verify(ctx, states, args, agy, canary, log, sid)
            else:
                steps += 1
                do_merge(ctx, states, log, sid)
                ok = True
            if ok:
                attempts.pop(key, None)
            else:
                attempts[key] = attempts.get(key, 0) + 1
                if attempts[key] >= 2:
                    raise Stop(1, f"{sid}: no progress after 2 attempts at '{kind}'. Read {log.path.relative_to(root).as_posix()} and the handoff, then decide")
    except Stop as e:
        label = {0: "AUTOPILOT STOPPED", 1: "AUTOPILOT STOPPED, SOMETHING UNEXPECTED", 2: "AUTOPILOT DID NOT START"}[e.code]
        print(f"\n{label}: {e.message}")
        try:
            log.add(step="stop", code=e.code, message=e.message)
        except OSError:
            pass
        if e.code != 2:
            print("What to do next:  py -3 tools\\tracker\\backlog.py")
        return e.code
    except B.Fail as e:
        print(f"\nAUTOPILOT DID NOT START: {e}")
        return 2


def main(argv: list[str] | None = None) -> int:
    B.C.utf8_stdio()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--author-model", required=True, help="model slug for the author (see: agy models)")
    ap.add_argument("--verifier-model", required=True, help="model slug for the verifier; a different family than the author")
    ap.add_argument("--agy", default="agy", help="the agy command (default: agy)")
    ap.add_argument("--agy-args", default="", help="extra arguments passed to every agy -p call, e.g. --sandbox")
    ap.add_argument("--max-steps", type=int, default=6, help="agent calls plus merges per run (default 6)")
    ap.add_argument("--max-minutes", type=int, default=180, help="wall-clock budget per run (default 180)")
    ap.add_argument("--agent-minutes", type=int, default=45, help="longest one agent session may take (default 45)")
    ap.add_argument("--smoke-seconds", type=int, default=180, help="longest the one-line smoke question to each model may take (default 180); 0 skips it")
    ap.add_argument("--dry-run", action="store_true", help="print the next action; change nothing, call no agent")
    ap.add_argument("--inline-rules", action="store_true", help="paste AGENTS.md into every prompt (use when the canary check fails)")
    ap.add_argument("--skip-model-check", action="store_true", help="do not check the slugs against `agy models`")
    ap.add_argument("--pass-env", action="append", default=[], metavar="NAME", help="an environment variable that looks like a secret but agy needs")
    ap.add_argument("--root")
    ap.add_argument("--today", help="pretend it is this day (tests)")
    return run(ap.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
