#!/usr/bin/env python3
"""The Locus board: Agile on top of the evidence tracker. Nobody types a story's status; it is derived.

Run with no arguments at the start of every slot. It prints the board and NEXT ACTION (the one thing to do now).

    python tools/tracker/backlog.py                      board + NEXT ACTION
    python tools/tracker/backlog.py --calendar           the sprints, slot by slot
    python tools/tracker/backlog.py --refine             what to fix so the top of the backlog is Ready (writes the prompts to paste)
    python tools/tracker/backlog.py --plan [--write]     propose the next sprint; --write records it (owner only)
    python tools/tracker/backlog.py --start US-03        branch + author prompt for one planned story
    python tools/tracker/backlog.py --prompt P2 US-03    verifier prompt (P1 and P2 need a story; P3 and P5 do not)
    python tools/tracker/backlog.py --accept US-03 --note "what I watched"      (owner only)
    python tools/tracker/backlog.py --retro                                      (owner only)
    python tools/tracker/backlog.py --close-sprint                               (owner only)
    python tools/tracker/backlog.py --check              validate backlog.yaml and the sprint log (CI)

Options: --json (machine-readable board), --today YYYY-MM-DD (pretend it is that day), --root PATH.
Files: tracker/backlog.yaml (the Product Backlog, owner-edited) and tracker/sprints.jsonl (append-only: planned, accepted, closed).
A story's state comes from git and files only: branch, tracker/handoff/<story>.md, tracker/handoff/<story>-verify.md,
tracker/status.json (levels computed by verify.py) and the accepted events. See docs/agent/11-agile-workflow.md.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import locus_common as C  # noqa: E402

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
DEFAULTS = {"main_branch": "main", "sprint_days": 14, "slot_days": ["Mon", "Tue", "Fri"], "slot_time": "19:30",
            "capacity_points": 4, "max_story_points": 3, "wip_limit": 1, "refine_top": 5}
HANDOFF_HEADINGS = ["Plan", "Files changed", "Spec sentences", "Config keys", "Commands run", "Open questions",
                    "Discard table", "Security", "Not done"]
RETRO_HEADINGS = ["Worked", "Did not work", "One change"]
IN_PROGRESS = ("DOING", "VERIFY", "REWORK", "MERGE")
VERDICT_RX = re.compile(r"^\s*VERDICT:\s*(ACCEPT-WITH-FIXES|ACCEPT|REJECT)\b", re.I)
BL = r"py -3 tools\tracker\backlog.py"
OWNER_ON = '$env:LOCUS_ALLOW_GUARD_EDIT = "1"'
OWNER_OFF = "Remove-Item Env:LOCUS_ALLOW_GUARD_EDIT"
CLIP = r"Get-Content -Raw -Encoding UTF8 tracker\.cache\prompt-{name}.md | Set-Clipboard"


class Fail(Exception):
    """A refusal that carries the message for the human (exit code 2)."""


# --------------------------------------------------------------------------- small helpers
def as_date(v) -> date:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return date.fromisoformat(str(v))


def fmt(d: date) -> str:
    return f"{DAYS[d.weekday()]} {d.isoformat()}"


def family(text: str) -> str:
    m = re.match(r"\s*([A-Za-z]+)", text or "")
    return m.group(1).lower() if m else ""


def slot_dates(start: date, days: int, slot_days: list) -> list[date]:
    want = {DAYS.index(d) for d in slot_days if d in DAYS}
    return [start + timedelta(days=i) for i in range(days) if (start + timedelta(days=i)).weekday() in want]


def next_slot_day(d: date, slot_days: list) -> date:
    for _ in range(8):
        if DAYS[d.weekday()] in slot_days:
            return d
        d += timedelta(days=1)
    return d


def ceremonies(i: int, n: int) -> list[str]:
    tags = []
    if i == 0:
        tags.append("PLANNING")
    if n >= 4 and i == n - 2:
        tags.append("REFINEMENT")
    if i == n - 1:
        tags.append("REVIEW+RETRO")
    return tags


def pts(story: dict) -> int:
    v = story.get("points")
    return v if isinstance(v, int) and not isinstance(v, bool) else 0


def need_owner(what: str) -> None:
    if os.environ.get("LOCUS_ALLOW_GUARD_EDIT") != "1":
        raise Fail(f"{what} writes a human-owned file (AGENTS.md law 11). Only the owner runs it, after:  {OWNER_ON}")


# --------------------------------------------------------------------------- files: log, errata, handoff, verdict
def read_log(root: Path) -> tuple[list[dict], list[str]]:
    p = root / "tracker" / "sprints.jsonl"
    events, bad = [], []
    if p.is_file():
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                e = json.loads(line)
                if not isinstance(e, dict):
                    raise ValueError("not an object")
                events.append(e)
            except ValueError:
                bad.append(f"tracker/sprints.jsonl line {n} is not a JSON object")
    return events, bad


def append_log(root: Path, event: dict) -> None:
    p = root / "tracker" / "sprints.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")


def errata_status(root: Path) -> dict[str, str]:
    p = root / "docs" / "agent" / "09-spec-errata.md"
    out: dict[str, str] = {}
    if p.is_file():
        for line in p.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^\|\s*(D-\d+)\s*\|\s*([A-Za-z]+)", line)
            if m:
                out.setdefault(m.group(1), m.group(2).upper())
    return out


def _sections(text: str) -> list[tuple[str, list[str]]]:
    lines = text.splitlines()
    heads = [i for i, ln in enumerate(lines) if ln.startswith("## ")]
    out = []
    for k, i in enumerate(heads):
        end = heads[k + 1] if k + 1 < len(heads) else len(lines)
        body = [ln for ln in lines[i + 1:end] if ln.strip() and not re.fullmatch(r"\s*<!--.*-->\s*", ln)]
        out.append((lines[i][3:].strip().lower(), body))
    return out


def parse_handoff(text: str | None) -> tuple[list[str], str]:
    """-> (missing or empty headings, author model family from the first line)."""
    if text is None:
        return list(HANDOFF_HEADINGS), ""
    secs = _sections(text)
    missing = []
    for name in HANDOFF_HEADINGS:
        hit = next((body for title, body in secs if title.startswith(name.lower())), None)
        if not hit:
            missing.append(name)
    m = re.search(r"^#\s*\S+\s+handoff\s*[-\u2013\u2014]\s*([^,\n]+)", text, re.M | re.I)
    return missing, family(m.group(1)) if m else ""


def parse_verify(text: str | None) -> tuple[str | None, str]:
    """-> (verdict from the FIRST line, verifier model family from a `Verifier:` line)."""
    if not text:
        return None, ""
    first = next((ln for ln in text.splitlines() if ln.strip()), "")
    m = VERDICT_RX.match(first)
    v = re.search(r"^\s*Verifier:\s*(.+)$", text, re.M | re.I)
    return (m.group(1).upper() if m else None), (family(v.group(1)) if v else "")


def retro_problems(path: Path) -> list[str]:
    if not path.is_file():
        return [f"tracker/retro/{path.name} does not exist (run --retro)"]
    text = path.read_text(encoding="utf-8")
    secs = _sections(text)
    probs = []
    for name in RETRO_HEADINGS:
        body = next((b for t, b in secs if t.startswith(name.lower())), None)
        if not body:
            probs.append(f"section '{name}' is missing or empty")
            continue
        if any("<fill>" in ln for ln in body):
            probs.append(f"section '{name}' still contains <fill>")
        if name == "One change" and len(body) != 1:
            probs.append(f"'One change' must be exactly ONE line (it has {len(body)})")
    return probs


# --------------------------------------------------------------------------- the context
class Ctx:
    def __init__(self, root: Path, today: date):
        self.root, self.today = root, today
        p = root / "tracker" / "backlog.yaml"
        if not p.is_file():
            raise Fail("tracker/backlog.yaml does not exist. It is the Product Backlog; the owner commits it (docs/agent/11-agile-workflow.md).")
        raw = C.load_yaml(p) or {}
        if not isinstance(raw, dict):
            raise Fail("tracker/backlog.yaml must be a YAML mapping")
        self.raw = raw
        self.cfg = {**DEFAULTS, **(raw.get("config") or {})}
        self.epics = {e["id"]: e for e in (raw.get("epics") or []) if isinstance(e, dict) and "id" in e}
        self.stories = [s for s in (raw.get("stories") or []) if isinstance(s, dict) and isinstance(s.get("id"), str)]
        self.by_id = {s["id"]: s for s in self.stories}
        gcfg = C.load_toml(root / "tools" / "guard" / "guard.toml") if (root / "tools" / "guard" / "guard.toml").is_file() else {}
        self.xlsx = (gcfg.get("repo") or {}).get("tracker_xlsx", "")
        fp = root / "tracker" / "features.yaml"
        self.feats = {f["id"]: f for f in (C.load_yaml(fp) or {}).get("features", [])} if fp.is_file() else {}
        sp = root / "tracker" / "status.json"
        self.status = json.loads(sp.read_text(encoding="utf-8")) if sp.is_file() else None
        self.log, self.bad_log = read_log(root)
        self.errata = errata_status(root)
        self.main = str(self.cfg["main_branch"])
        self.main_ok = C.git(root, "rev-parse", "--verify", "-q", f"refs/heads/{self.main}")[0] == 0
        rc, out = C.git(root, "branch", "--show-current")
        self.cur = out.strip() if rc == 0 else ""
        self.sprints: list[dict] = []
        self.accepted: dict[str, dict] = {}
        for e in self.log:
            ev = e.get("event")
            if ev == "planned":
                self.sprints.append({**e, "closed": None})
            elif ev == "closed":
                for s in reversed(self.sprints):
                    if s.get("sprint") == e.get("sprint") and not s["closed"]:
                        s["closed"] = e
                        break
            elif ev == "accepted" and isinstance(e.get("story"), str):
                self.accepted.setdefault(e["story"], e)

    @property
    def active(self) -> dict | None:
        return self.sprints[-1] if self.sprints and not self.sprints[-1]["closed"] else None

    def expected_start(self) -> date:
        if self.sprints:
            return as_date(self.sprints[-1]["end"]) + timedelta(days=1)
        return as_date(self.cfg.get("first_sprint_start"))

    # ---- reading story files from the right place
    def read_work(self, rel: str) -> str | None:
        p = self.root / rel
        return p.read_text(encoding="utf-8", errors="replace") if p.is_file() else None

    def read_main(self, rel: str) -> str | None:
        if not self.main_ok:
            return self.read_work(rel)
        rc, out = C.git(self.root, "show", f"{self.main}:{rel}")
        return out if rc == 0 else None

    def read_branch(self, br: str, rel: str) -> str | None:
        if br == self.cur:
            return self.read_work(rel)
        rc, out = C.git(self.root, "show", f"{br}:{rel}")
        return out if rc == 0 else None

    def find_branch(self, sid: str) -> str | None:
        rc, out = C.git(self.root, "for-each-ref", "--format=%(refname:short)", f"refs/heads/task/{sid}-*")
        names = sorted(ln.strip() for ln in out.splitlines() if ln.strip()) if rc == 0 else []
        return names[0] if names else None

    def dirty(self) -> list[str]:
        rc, out = C.git(self.root, "status", "--porcelain=v1", "-z")
        if rc != 0:
            return []
        parts, files, i = out.split("\0"), [], 0
        while i < len(parts):
            e = parts[i]
            i += 1
            if len(e) < 4:
                continue
            if "R" in e[:2] or "C" in e[:2]:
                i += 1
            files.append(e[3:])
        xlsx = self.xlsx.replace("\\", "/")
        return [f for f in files if f != xlsx and not f.startswith("tracker/.cache/")]

    def hooks_on(self) -> bool:
        return C.git(self.root, "config", "core.hooksPath")[1].strip() == ".githooks"


# --------------------------------------------------------------------------- derived story state
def derive(ctx: Ctx) -> dict[str, dict]:
    """State of every story, from git and files only. TODO DOING VERIFY REWORK MERGE REVIEW DONE (and ANOMALY)."""
    out: dict[str, dict] = {}
    for s in ctx.stories:
        sid = s["id"]
        rh, rv = f"tracker/handoff/{sid}.md", f"tracker/handoff/{sid}-verify.md"
        br = ctx.find_branch(sid)
        notes: list[str] = []
        mh, mv = ctx.read_main(rh), ctx.read_main(rv)
        miss, afam = parse_handoff(mh)
        verdict, vfam = parse_verify(mv)
        author, verifier = afam, vfam
        if mh is not None and not miss and verdict == "ACCEPT" and afam and vfam and afam != vfam:
            base = "REVIEW"
        elif br:
            bh, bv = ctx.read_branch(br, rh), ctx.read_branch(br, rv)
            miss, author = parse_handoff(bh)
            verdict, verifier = parse_verify(bv)
            if bh is None:
                base = "DOING"
                notes.append(f"tracker/handoff/{sid}.md does not exist yet")
            elif miss:
                base = "DOING"
                notes.append("handoff sections missing or empty: " + ", ".join(miss))
            elif not author:
                base = "DOING"
                notes.append(f"first line of the handoff must be '# {sid} handoff - <model>, <date>'")
            elif verdict is None or not verifier:
                base = "VERIFY"
                if bv is not None:
                    notes.append("verify file needs 'VERDICT: ...' on its first line and a 'Verifier: <model>' line")
            elif verifier == author:
                base = "VERIFY"
                notes.append(f"the verifier ({verifier}) is the same model family as the author: use the other model")
            elif verdict == "ACCEPT":
                base = "MERGE"
            else:
                base = "REWORK"
                notes.append(f"verdict {verdict}")
        elif mh is not None or mv is not None:
            base = "ANOMALY"
            notes.append("merged to " + ctx.main + " without a complete handoff and an ACCEPT verdict from a different model")
        else:
            base = "TODO"
        acc = ctx.accepted.get(sid)
        fid = s.get("feature")
        lvl = None
        if ctx.status and isinstance(ctx.status.get("features"), dict) and fid in ctx.status["features"]:
            lvl = ctx.status["features"][fid].get("level")
        try:
            target = int(s.get("target_level", 3))
        except (TypeError, ValueError):
            target = 3
        out[sid] = {"base": base, "state": "DONE" if (acc and base == "REVIEW") else base, "branch": br, "notes": notes,
                    "accepted": acc, "level": lvl, "target": target, "level_ok": lvl is not None and lvl >= target,
                    "author": author, "verifier": verifier, "verdict": verdict}
    return out


def readiness(ctx: Ctx, s: dict, states: dict) -> list[tuple[str, str]]:
    """Definition of Ready. -> [(kind, text)] with kind decision | dependency | content. Empty list = Ready."""
    p: list[tuple[str, str]] = []
    mx = int(ctx.cfg["max_story_points"])
    v = s.get("points")
    if not (isinstance(v, int) and not isinstance(v, bool) and 1 <= v <= mx):
        p.append(("content", f"points must be a whole number from 1 to {mx} (split a bigger story)"))
    if s.get("feature") not in ctx.feats:
        p.append(("content", f"feature {s.get('feature')} is not in tracker/features.yaml"))
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,40}", str(s.get("slug", ""))):
        p.append(("content", "slug must be 2-41 lowercase letters, digits or hyphens"))
    acc = s.get("accept")
    if not (isinstance(acc, list) and acc and all(isinstance(x, str) and x.strip() for x in acc)):
        p.append(("content", "accept: needs at least one observable acceptance criterion"))
    if not (isinstance(s.get("demo"), str) and s["demo"].strip()):
        p.append(("content", "demo: the owner's exact live check is missing"))
    if s.get("target_level") not in (2, 3, 4):
        p.append(("content", "target_level must be 2, 3 or 4"))
    for d in s.get("requires_decisions") or []:
        st = ctx.errata.get(d)
        if st is None:
            p.append(("content", f"{d} is not a row in docs/agent/09-spec-errata.md"))
        elif st == "OPEN":
            p.append(("decision", f"{d} is OPEN: decide it first (prompt P3)"))
    for dep in s.get("depends_on") or []:
        ds = states.get(dep, {}).get("state")
        if ds not in ("REVIEW", "DONE"):
            p.append(("dependency", f"waits for {dep} (now {ds or 'unknown'})"))
    return p


# --------------------------------------------------------------------------- --check
def validate(ctx: Ctx, states: dict) -> tuple[list[str], list[str]]:
    errs: list[str] = list(ctx.bad_log)
    warns: list[str] = []
    cfg = ctx.cfg
    for k in ("sprint_days", "capacity_points", "max_story_points", "wip_limit", "refine_top"):
        if not (isinstance(cfg.get(k), int) and not isinstance(cfg.get(k), bool) and cfg[k] >= 1):
            errs.append(f"config.{k} must be a whole number >= 1")
    sd = cfg.get("slot_days")
    if not (isinstance(sd, list) and sd and all(d in DAYS for d in sd)):
        errs.append("config.slot_days must be a list of " + ", ".join(DAYS))
    else:
        try:
            start = as_date(cfg.get("first_sprint_start"))
        except (TypeError, ValueError):
            errs.append("config.first_sprint_start must be a date YYYY-MM-DD")
        else:
            if DAYS[start.weekday()] not in sd:
                errs.append(f"config.first_sprint_start {start} is a {DAYS[start.weekday()]}; it must fall on a slot day")
            if isinstance(cfg.get("sprint_days"), int) and len(slot_dates(start, cfg["sprint_days"], sd)) < 4:
                errs.append("a sprint needs at least 4 slots (planning, refinement, review and at least one work slot)")
    if not re.fullmatch(r"\d\d:\d\d", str(cfg.get("slot_time"))):
        errs.append("config.slot_time must look like 19:30")
    seen: dict[str, int] = {}
    slugs: set[str] = set()
    for i, s in enumerate(ctx.raw.get("stories") or []):
        if not isinstance(s, dict) or not isinstance(s.get("id"), str) or not re.fullmatch(r"US-\d{2,3}", s["id"]):
            errs.append(f"story #{i + 1}: id must look like US-01")
            continue
        sid = s["id"]
        if sid in seen:
            errs.append(f"{sid}: duplicate id")
            continue
        seen[sid] = i
        if s.get("epic") not in ctx.epics:
            errs.append(f"{sid}: unknown epic {s.get('epic')}")
        if not (isinstance(s.get("title"), str) and s["title"].strip()):
            errs.append(f"{sid}: title is missing")
        if s.get("feature") not in ctx.feats:
            errs.append(f"{sid}: feature {s.get('feature')} is not in tracker/features.yaml")
        v = s.get("points")
        if not (isinstance(v, int) and not isinstance(v, bool) and 1 <= v <= int(cfg["max_story_points"])):
            errs.append(f"{sid}: points must be 1 to {cfg['max_story_points']}; a bigger story must be split")
        if s.get("target_level") not in (2, 3, 4):
            errs.append(f"{sid}: target_level must be 2, 3 or 4")
        slug = str(s.get("slug", ""))
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,40}", slug):
            errs.append(f"{sid}: slug must be 2-41 lowercase letters, digits or hyphens")
        elif slug in slugs:
            errs.append(f"{sid}: slug {slug} is used by another story")
        slugs.add(slug)
        if "completes_feature" in s and not isinstance(s["completes_feature"], bool):
            errs.append(f"{sid}: completes_feature must be true or false")
        if "autopilot" in s and not isinstance(s["autopilot"], bool):
            errs.append(f"{sid}: autopilot must be true or false")
        for d in s.get("requires_decisions") or []:
            if d not in ctx.errata:
                errs.append(f"{sid}: {d} is not a row in docs/agent/09-spec-errata.md")
        for dep in s.get("depends_on") or []:
            if dep not in ctx.by_id:
                errs.append(f"{sid}: depends_on {dep} does not exist")
            elif seen.get(dep, 10**6) >= i:
                errs.append(f"{sid}: depends_on {dep}, which is not ABOVE it in the backlog (priority order must respect dependencies)")
    wip = [sid for sid, st in states.items() if st["state"] in IN_PROGRESS]
    if len(wip) > int(cfg["wip_limit"]):
        errs.append(f"WIP limit {cfg['wip_limit']} exceeded: {', '.join(wip)} are all in progress")
    open_sprints = [s for s in ctx.sprints if not s["closed"]]
    if len(open_sprints) > 1:
        errs.append("more than one sprint is open in tracker/sprints.jsonl")
    for e in ctx.log:
        ev = e.get("event")
        if ev not in ("planned", "accepted", "closed"):
            errs.append(f"tracker/sprints.jsonl: unknown event {ev!r}")
        elif ev == "planned":
            for sid in e.get("stories") or []:
                if sid not in ctx.by_id:
                    errs.append(f"sprint {e.get('sprint')} plans {sid}, which is not in the backlog")
        elif ev == "accepted":
            sid = e.get("story")
            if sid not in states:
                errs.append(f"accepted event for unknown story {sid}")
            elif states[sid]["base"] != "REVIEW":
                errs.append(f"{sid} is recorded as accepted but is {states[sid]['base']}: no complete handoff + ACCEPT verdict from a different model on {ctx.main}")
        elif ev == "closed" and not any(s.get("sprint") == e.get("sprint") for s in ctx.sprints):
            errs.append(f"sprint {e.get('sprint')} is closed but was never planned")
    for sid, st in states.items():
        if st["state"] == "ANOMALY":
            warns.append(f"{sid}: {'; '.join(st['notes'])}")
    todo = [s for s in ctx.stories if states[s["id"]]["state"] == "TODO"][: int(cfg["refine_top"]) if isinstance(cfg.get("refine_top"), int) else 5]
    for s in todo:
        probs = readiness(ctx, s, states)
        if probs:
            warns.append(f"top of backlog: {s['id']} is not Ready ({'; '.join(t for _, t in probs)})")
    return errs, warns


# --------------------------------------------------------------------------- capacity, prompts
def capacity_next(ctx: Ctx) -> tuple[int, str]:
    vel = [e["velocity"] for e in ctx.log if e.get("event") == "closed" and isinstance(e.get("velocity"), int)]
    if len(vel) >= 3:
        cap = max(2, min(8, math.floor(sum(vel[-3:]) / 3)))
        return cap, f"average velocity of the last 3 sprints ({vel[-3:]}) rounded down, between 2 and 8"
    return int(ctx.cfg["capacity_points"]), f"config capacity_points (a velocity average is used after 3 closed sprints; {len(vel)} so far)"


def render_prompt(ctx: Ctx, which: str, mapping: dict, name: str, addendum: list | None = None) -> Path:
    pdir = ctx.root / "docs" / "agent" / "prompts"
    f = next(iter(sorted(pdir.glob(f"{which}-*.md"))), None)
    if f is None:
        raise Fail(f"no prompt file docs/agent/prompts/{which}-*.md")

    def body(path: Path) -> str:
        t = path.read_text(encoding="utf-8")
        parts = re.split(r"^---\s*$", t, maxsplit=1, flags=re.M)
        return (parts[1] if len(parts) == 2 else t).strip("\n")

    text = body(f)
    for extra in addendum or []:
        g = next(iter(sorted(pdir.glob(f"{extra}-*.md"))), None)
        if g is None:
            raise Fail(f"story asks for addendum {extra} but docs/agent/prompts/{extra}-*.md does not exist")
        text += "\n\n" + body(g)
    for k, v in mapping.items():
        text = text.replace("{{" + k + "}}", str(v))
    left = sorted(set(re.findall(r"\{\{([A-Z_]+)\}\}", text)))
    if left:
        raise Fail(f"prompt {which} has unfilled placeholders: {', '.join(left)}")
    out = ctx.root / "tracker" / ".cache" / f"prompt-{name}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text + "\n", encoding="utf-8", newline="\n")
    return out


def story_mapping(ctx: Ctx, s: dict, info: dict) -> dict:
    return {"STORY": s["id"], "FEATURE": s.get("feature", ""), "TITLE": s.get("title", ""), "POINTS": s.get("points", ""),
            "TARGET": s.get("target_level", ""), "SLUG": s.get("slug", ""),
            "BRANCH": info.get("branch") or f"task/{s['id']}-{s.get('slug', '')}",
            "ACCEPT": "\n".join(f"- {a}" for a in (s.get("accept") or [])),
            "DEMO": s.get("demo", ""), "DECISIONS": ", ".join(s.get("requires_decisions") or []) or "none",
            "AUTHOR": info.get("author") or "the author"}


# --------------------------------------------------------------------------- instructions for a story
OTHER = {"claude": "Gemini", "gemini": "Claude"}


def story_steps(ctx: Ctx, s: dict, info: dict) -> list[str]:
    sid, fid, br, st = s["id"], s["feature"], info["branch"], info["state"]
    notes = [f"  note: {n}" for n in info["notes"]]
    if st == "TODO":
        return [f"START {sid} ({fid}, {pts(s)} pts): {s.get('title', '')}",
                f"  1. {BL} --start {sid}",
                "  2. New Claude session on the folder locus-os. First message: what is the Locus canary?  It must answer blue-heron-47 (if not, close it and reopen the folder).",
                f"  3. Second message = the prompt. Copy it first:  {CLIP.format(name=sid + '-P1')}",
                "  4. Answer its questions one at a time. It must ask before it writes code. If it stops on an OPEN decision row, end the slot; that row goes to the next refinement.",
                f"  5. When it says it is finished:  py -3 tools\\guard\\check.py --full   then   {BL}"]
    if st == "DOING":
        return [f"CONTINUE {sid}: the author has not finished (branch {br}).", *notes,
                "  1. If the author session is still open, let it finish.",
                f"  2. If you closed it: new Claude session on locus-os, canary question, then  {BL} --prompt P1 {sid}  and  {CLIP.format(name=sid + '-P1')}",
                f"  3. When it says it is finished:  py -3 tools\\guard\\check.py --full   then   {BL}"]
    if st == "VERIFY":
        other = OTHER.get(info["author"], "a different model than " + (info["author"] or "the author"))
        return [f"VERIFY {sid}: handoff complete (author: {info['author']}). Nobody has accepted it yet.", *notes,
                f"  1. {BL} --prompt P2 {sid}",
                f"  2. New {other} session on the SAME branch ({br}). Canary question first.",
                f"  3. Paste the prompt. Copy it first:  {CLIP.format(name=sid + '-P2')}",
                f"  4. It writes tracker\\handoff\\{sid}-verify.md and stops. Then run  {BL}"]
    if st == "REWORK":
        return [f"REWORK {sid}: the verifier did not accept it. Read tracker\\handoff\\{sid}-verify.md.", *notes,
                f"  1. New {info['author'].capitalize() or 'Claude'} session on branch {br}. Canary question first.",
                f"  2. {BL} --prompt P1 {sid}   then   {CLIP.format(name=sid + '-P1')}   and paste it.",
                f"  3. Second message: Fix exactly the numbered findings in tracker\\handoff\\{sid}-verify.md and nothing else.",
                f"  4. Then verify again with a NEW session of the other model: {BL} --prompt P2 {sid}"]
    if st == "MERGE":
        vf = f"tracker/handoff/{sid}-verify.md"
        verdict_open = bool(C.git(ctx.root, "status", "--porcelain", "--untracked-files=all", "--", vf)[1].strip())
        commit_verdict = ([f"  git add tracker\\handoff\\{sid}-verify.md",
                           f'  git commit -m "chore(tracker): verdict for {sid}"'] if verdict_open else [])
        return [f"MERGE {sid}: a different model accepted it. Do exactly this now:",
                *commit_verdict,
                "  git switch " + ctx.main,
                f"  git merge --ff-only {br}",
                f"  git branch -d {br}",
                "  py -3 tools\\tracker\\verify.py",
                "  py -3 tools\\tracker\\export_xlsx.py",
                "  git add tracker",
                f'  git commit -m "chore(tracker): refresh after {sid}"',
                f"  then run  {BL}"]
    if st == "REVIEW":
        return [f"{sid} is merged and waits for the Review slot. Nothing to do now."]
    if st == "ANOMALY":
        return [f"{sid}: {'; '.join(info['notes'])}",
                f"  Fix: {BL} --prompt P2 {sid}, run it in the OTHER model on branch {ctx.main}; it writes tracker\\handoff\\{sid}-verify.md; commit that file."]
    return []


def sprint_view(ctx: Ctx) -> dict | None:
    a = ctx.active
    if not a:
        return None
    st, en = as_date(a["start"]), as_date(a["end"])
    slots = slot_dates(st, int(ctx.cfg["sprint_days"]), ctx.cfg["slot_days"])
    return {"id": a["sprint"], "start": st, "end": en, "slots": slots, "stories": list(a.get("stories") or []),
            "goal": a.get("goal", ""), "capacity": a.get("capacity")}


def next_actions(ctx: Ctx, states: dict) -> list[str]:
    cfg, today = ctx.cfg, ctx.today
    time_ = cfg["slot_time"]
    sv = sprint_view(ctx)
    if sv is None:
        exp = ctx.expected_start()
        if today < exp:
            return [f"No sprint is active. Sprint {len(ctx.sprints) + 1} planning day: {fmt(exp)} {time_}.",
                    "Until then do only what the RUNBOOK lists for Sprint 0. Do not build anything."]
        if DAYS[today.weekday()] in cfg["slot_days"]:
            return [f"PLANNING (30 minutes) for Sprint {len(ctx.sprints) + 1}. Do exactly this:",
                    f"  1. {BL} --plan                (read it; a story listed as not Ready is skipped on purpose)",
                    f"  2. {OWNER_ON}",
                    f"  3. {BL} --plan --write",
                    '  4. git add tracker/sprints.jsonl',
                    '  5. git commit -m "chore(agile): plan sprint"',
                    f"  6. {OWNER_OFF}",
                    f"  7. {BL}                (the board then names the first story to start)"]
        nxt = next_slot_day(today, cfg["slot_days"])
        return [f"No sprint is active and today is not a slot day. Next slot: {fmt(nxt)} {time_} (PLANNING)."]
    slots = sv["slots"]
    n = len(slots)
    if today not in slots:
        future = [d for d in slots if d > today]
        if not future:
            return [f"Sprint {sv['id']} has no slot left. Close it at its review slot ({fmt(slots[-1])}) if you have not:",
                    f"  {OWNER_ON}  then  {BL} --retro  then  {BL} --close-sprint"]
        j = slots.index(future[0])
        tags = " + ".join(ceremonies(j, n)) or "work"
        return [f"Not a slot day. Next slot: {fmt(future[0])} {time_} ({tags}). Nothing to do before then."]
    idx = slots.index(today)
    tags = ceremonies(idx, n)
    out: list[str] = []
    if "REVIEW+RETRO" in tags:
        out += review_steps(ctx, states, sv)
        return out
    if "REFINEMENT" in tags:
        out += [f"REFINEMENT (30 minutes, FIRST in this slot): {BL} --refine  and do exactly what it prints.", ""]
    in_prog = [s for s in ctx.stories if states[s["id"]]["state"] in IN_PROGRESS]
    if in_prog:
        s = in_prog[0]
        return out + story_steps(ctx, s, states[s["id"]])
    for sid in sv["stories"]:
        s = ctx.by_id.get(sid)
        if s and states[sid]["state"] == "TODO" and not readiness(ctx, s, states):
            return out + story_steps(ctx, s, states[sid])
    return out + [f"Nothing is left to start in Sprint {sv['id']}. Run  {BL} --refine  and stop for today."]


def review_steps(ctx: Ctx, states: dict, sv: dict) -> list[str]:
    revs = [s for s in ctx.stories if states[s["id"]]["state"] == "REVIEW"]
    out = [f"REVIEW + RETRO for sprint {sv['id']} (about 45 minutes). Do exactly this, in this order:",
           f"  0. {OWNER_ON}"]
    if revs:
        out.append("  1. DEMO each story below, one at a time. Accept it only if the result matches exactly:")
        for s in revs:
            inf = states[s["id"]]
            lv = "level not computed: run py -3 tools\\tracker\\verify.py first" if inf["level"] is None else f"computed level L{inf['level']}, target L{inf['target']}"
            out += [f"     {s['id']} ({s['feature']}, {pts(s)} pts) {s.get('title', '')}  [{lv}]",
                    f"       demo: {s.get('demo', '')}",
                    f'       worked -> {BL} --accept {s["id"]} --note "what I saw"',
                    "       did not work -> do nothing; it stays in REVIEW and refinement adds a fix story"]
    else:
        out.append("  1. Nothing is waiting for a demo.")
    out += [f"  2. {BL} --retro               (creates tracker\\retro\\{sv['id']}.md). Fill the three sections in Notepad; exactly ONE line under 'One change'.",
            f"  3. {BL} --close-sprint",
            "  4. git add tracker",
            f'  5. git commit -m "chore(agile): close sprint {sv["id"]}"',
            f"  6. {OWNER_OFF}"]
    nxt = next_slot_day(sv["end"] + timedelta(days=1), ctx.cfg["slot_days"])
    out.append(f"  Next planning: {fmt(nxt)} {ctx.cfg['slot_time']}.")
    return out


# --------------------------------------------------------------------------- commands
def board_lines(ctx: Ctx, states: dict) -> list[str]:
    hooks = "ON" if ctx.hooks_on() else "OFF (turn on once the guard shows 0 FAIL: git config core.hooksPath .githooks)"
    out = [f"LOCUS BOARD  {fmt(ctx.today)}   hooks: {hooks}"]
    sv = sprint_view(ctx)
    if ctx.status is None:
        out.append("Levels unknown: tracker/status.json does not exist. Run: py -3 tools\\tracker\\verify.py")
    if sv:
        idx = sv["slots"].index(ctx.today) if ctx.today in sv["slots"] else None
        days = int(ctx.cfg["sprint_days"])
        where = f"slot {idx + 1} of {len(sv['slots'])} ({' + '.join(ceremonies(idx, len(sv['slots']))) or 'work'})" if idx is not None else "no slot today"
        out.append(f"Sprint {sv['id']}  {sv['start']} .. {sv['end']}  day {(ctx.today - sv['start']).days + 1} of {days}  {where}")
        out.append(f"Goal: {sv['goal']}")
        mine = [ctx.by_id[x] for x in sv["stories"] if x in ctx.by_id]
        tot = sum(pts(s) for s in mine)
        done = sum(pts(s) for s in mine if states[s["id"]]["state"] == "DONE")
        rev = sum(pts(s) for s in mine if states[s["id"]]["state"] == "REVIEW")
        prog = sum(pts(s) for s in mine if states[s["id"]]["state"] in IN_PROGRESS)
        out.append(f"Points: capacity {sv['capacity']} | planned {tot} | accepted {done} | waiting for demo {rev} | in progress {prog} | not started {tot - done - rev - prog}")
        rows = mine
    else:
        out.append("No active sprint.")
        rows = []
    wip = [s["id"] for s in ctx.stories if states[s["id"]]["state"] in IN_PROGRESS]
    out.append(f"WIP {len(wip)}/{ctx.cfg['wip_limit']}" + (": " + ", ".join(wip) if wip else ""))

    def table(items: list[dict]) -> list[str]:
        t = [f"  {'ID':<6} {'Pts':>3}  {'Feature':<8} {'State':<8} {'Level':<7} Title"]
        for s in items:
            i = states[s["id"]]
            lv = "L" + ("?" if i["level"] is None else str(i["level"])) + f"/L{i['target']}"
            t.append(f"  {s['id']:<6} {pts(s):>3}  {str(s.get('feature')):<8} {i['state']:<8} {lv:<7} {str(s.get('title', ''))[:70]}")
        return t

    if rows:
        out += ["", "SPRINT BACKLOG"] + table(rows)
    inside = {s["id"] for s in rows}
    nxt = [s for s in ctx.stories if states[s["id"]]["state"] == "TODO" and s["id"] not in inside][: int(ctx.cfg["refine_top"])]
    if nxt:
        out += ["", "NEXT IN THE PRODUCT BACKLOG (order = priority)"] + table(nxt)
        for s in nxt:
            probs = readiness(ctx, s, states)
            if probs:
                out.append(f"    {s['id']} not Ready: " + "; ".join(t for _, t in probs))
    waiting = [s for s in ctx.stories if states[s["id"]]["state"] == "REVIEW"]
    if waiting:
        out.append("")
        out.append("Merged, waiting for the owner's demo: " + ", ".join(s["id"] for s in waiting))
    return out


def guard_clean(ctx: Ctx) -> bool | None:
    """True when the last FULL guard run (tracker/.cache/guard_report.json) had 0 FAIL; None when there is no such report."""
    try:
        rep = json.loads((ctx.root / "tracker" / ".cache" / "guard_report.json").read_text(encoding="utf-8"))
        if rep.get("mode") != "full" or rep.get("only"):
            return None  # a fast or --only run says nothing about the whole guard
        return int(rep["counts"]["FAIL"]) == 0
    except (OSError, ValueError, KeyError, TypeError):
        return None


def cmd_board(ctx: Ctx, states: dict, as_json: bool) -> int:
    na = next_actions(ctx, states)
    if not ctx.hooks_on() and guard_clean(ctx) is True:
        na = ["TURN THE HOOKS ON NOW (the last guard run had 0 FAIL):  git config core.hooksPath .githooks", ""] + na
    if as_json:
        sv = sprint_view(ctx)
        print(json.dumps({"today": ctx.today.isoformat(), "hooks_on": ctx.hooks_on(), "levels_known": ctx.status is not None,
                          "sprint": None if not sv else {"id": sv["id"], "start": sv["start"].isoformat(), "end": sv["end"].isoformat(),
                                                         "stories": sv["stories"], "goal": sv["goal"], "capacity": sv["capacity"]},
                          "wip": [s["id"] for s in ctx.stories if states[s["id"]]["state"] in IN_PROGRESS],
                          "states": {k: {kk: vv for kk, vv in v.items() if kk != "accepted"} | {"accepted": bool(v["accepted"])} for k, v in states.items()},
                          "next": na}, indent=1, default=str))
        return 0
    print("\n".join(board_lines(ctx, states)))
    print("\nNEXT ACTION (do exactly this, nothing else):")
    print("\n".join("  " + ln if ln and not ln.startswith(" ") else ln for ln in na))
    return 0


def cmd_calendar(ctx: Ctx) -> int:
    cfg = ctx.cfg
    days = int(cfg["sprint_days"])

    def show(label: str, start: date) -> date:
        end = start + timedelta(days=days - 1)
        sl = slot_dates(start, days, cfg["slot_days"])
        print(f"{label}  {fmt(start)} .. {fmt(end)}")
        for j, d in enumerate(sl):
            print(f"  {fmt(d)} {cfg['slot_time']}  {' + '.join(ceremonies(j, len(sl))) or 'work'}")
        return end + timedelta(days=1)

    a = ctx.active
    if a:
        show(f"{a['sprint']} (ACTIVE)", as_date(a["start"]))
    k = len(ctx.sprints) + 1
    start = ctx.expected_start()
    for i in range(6):
        start = show(f"S{k + i}", start)
    print("A slot is one evening session. Ceremonies come first in the slot; story work uses the rest.")
    return 0


def cmd_check(ctx: Ctx, states: dict) -> int:
    errs, warns = validate(ctx, states)
    for w in warns:
        print("WARN ", w)
    for e in errs:
        print("ERROR", e)
    print(f"backlog check: {len(ctx.stories)} stories, {len(ctx.sprints)} sprints, {len(errs)} ERROR, {len(warns)} WARN")
    return 1 if errs else 0


def cmd_refine(ctx: Ctx, states: dict) -> int:
    top = [s for s in ctx.stories if states[s["id"]]["state"] == "TODO"][: int(ctx.cfg["refine_top"])]
    if not top:
        print("The backlog has no unstarted stories. The owner adds stories with prompt P5 (docs/agent/prompts/P5-backlog-refinement.md).")
        return 0
    ready, waiting, problems, rows = [], [], [], []
    for s in top:
        probs = readiness(ctx, s, states)
        if not probs:
            ready.append(s["id"])
        for kind, text in probs:
            if kind == "decision":
                m = re.match(r"(D-\d+)", text)
                if m and m.group(1) not in rows:
                    rows.append(m.group(1))
            elif kind == "dependency":
                waiting.append(f"{s['id']} {text}")
            else:
                problems.append(f"{s['id']}: {text}")
    print(f"REFINEMENT of the top {len(top)} stories: Ready = {', '.join(ready) or 'none'}")
    for w in waiting:
        print(f"  waiting: {w} (nothing to do; it becomes Ready when that story is merged)")
    if not rows and not problems:
        print("Nothing to refine: every story that can be Ready is Ready. Stop here.")
        return 0
    step = 1
    if rows:
        path = render_prompt(ctx, "P3", {"ROWS": ", ".join(rows)}, "P3")
        print(f"\n{step}. DECISIONS needed by the top stories, in this order: {', '.join(rows)}")
        print(f"   New Claude session on locus-os, canary first, then paste:  {CLIP.format(name='P3')}")
        print(f"   (prompt written to {path.relative_to(ctx.root).as_posix()})")
        step += 1
    if problems:
        text = "\n".join(f"- {p}" for p in problems)
        path = render_prompt(ctx, "P5", {"PROBLEMS": text, "TOP": ", ".join(s["id"] for s in top)}, "P5")
        print(f"\n{step}. STORIES to complete:\n" + "\n".join(f"   {p}" for p in problems))
        print(f"   New Claude session on locus-os, canary first, then paste:  {CLIP.format(name='P5')}")
        print(f"   (prompt written to {path.relative_to(ctx.root).as_posix()})")
        step += 1
    print(f"\n{step}. {BL} --check   (must print 0 ERROR)")
    print(f"{step + 1}. {OWNER_ON}")
    print(f'{step + 2}. git add tracker docs/agent/09-spec-errata.md ; git commit -m "docs(agile): refine backlog"')
    print(f"{step + 3}. {OWNER_OFF}")
    return 0


def cmd_plan(ctx: Ctx, states: dict, write: bool, goal: str | None) -> int:
    if ctx.active:
        raise Fail(f"sprint {ctx.active['sprint']} is still open. Close it at its review slot first ({BL} --close-sprint).")
    cfg = ctx.cfg
    exp = ctx.expected_start()
    start = max(ctx.today, exp)
    sid = f"S{len(ctx.sprints) + 1}"
    end = start + timedelta(days=int(cfg["sprint_days"]) - 1)
    cap, why = capacity_next(ctx)
    carried = [s for s in ctx.stories if states[s["id"]]["state"] in IN_PROGRESS]
    chosen, used = list(carried), sum(pts(s) for s in carried)
    skipped, stopped = [], None
    for s in ctx.stories:
        if states[s["id"]]["state"] != "TODO":
            continue
        probs = readiness(ctx, s, states)
        if probs:
            skipped.append((s["id"], "; ".join(t for _, t in probs)))
            continue
        if used + pts(s) > cap:
            stopped = s
            break
        chosen.append(s)
        used += pts(s)
    print(f"PLAN for sprint {sid}: {fmt(start)} .. {fmt(end)}   capacity {cap} points ({why})")
    for s in carried:
        print(f"  carry   {s['id']}  {pts(s)} pts  {s['feature']}  {s.get('title', '')}   (unfinished: {states[s['id']]['state']})")
    run = sum(pts(s) for s in carried)
    for s in chosen[len(carried):]:
        run += pts(s)
        print(f"  take    {s['id']}  {pts(s)} pts  {s['feature']}  {s.get('title', '')}   total {run}/{cap}")
    if stopped:
        print(f"  stop    {stopped['id']} ({pts(stopped)} pts) does not fit: {used} + {pts(stopped)} > {cap}. Stories are taken strictly in priority order.")
    for sk, why_ in skipped:
        print(f"  skipped {sk}: not Ready ({why_})")
    waiting = [s["id"] for s in ctx.stories if states[s["id"]]["state"] == "REVIEW"]
    if waiting:
        print("  still waiting for the owner's demo (they are not planned again): " + ", ".join(waiting))
    if not chosen:
        print("Nothing is Ready, so there is nothing to plan. Run:  " + BL + " --refine")
        return 1
    g = goal or str((ctx.epics.get(chosen[0].get("epic")) or {}).get("goal") or chosen[0].get("title", ""))
    print(f"Goal: {g}")
    if not write:
        print(f"\nThis was a dry run. To record it (on a slot day, owner only):  {OWNER_ON}  then  {BL} --plan --write")
        return 0
    need_owner("--plan --write")
    if ctx.today < exp:
        raise Fail(f"sprint {sid} may be planned from {fmt(exp)}, not {fmt(ctx.today)}")
    if DAYS[ctx.today.weekday()] not in cfg["slot_days"]:
        raise Fail(f"planning happens in a slot; {fmt(ctx.today)} is not one (slot days: {', '.join(cfg['slot_days'])})")
    append_log(ctx.root, {"event": "planned", "sprint": sid, "start": start.isoformat(), "end": end.isoformat(), "goal": g,
                          "capacity": cap, "points": used, "stories": [s["id"] for s in chosen], "date": ctx.today.isoformat()})
    print(f"\nRecorded sprint {sid} in tracker/sprints.jsonl. Next:  git add tracker/sprints.jsonl ; git commit ; {OWNER_OFF}")
    return 0


def cmd_start(ctx: Ctx, states: dict, sid: str) -> int:
    s = ctx.by_id.get(sid)
    if not s:
        raise Fail(f"{sid} is not in the backlog")
    a = ctx.active
    if not a or sid not in (a.get("stories") or []):
        raise Fail(f"{sid} is not in the active sprint. Only planned stories are started.")
    if states[sid]["state"] != "TODO":
        raise Fail(f"{sid} is {states[sid]['state']}, not TODO")
    probs = readiness(ctx, s, states)
    if probs:
        raise Fail(f"{sid} is not Ready: " + "; ".join(t for _, t in probs))
    wip = [x["id"] for x in ctx.stories if states[x["id"]]["state"] in IN_PROGRESS]
    if len(wip) >= int(ctx.cfg["wip_limit"]):
        raise Fail(f"WIP limit {ctx.cfg['wip_limit']}: finish {', '.join(wip)} first")
    if ctx.cur != ctx.main:
        raise Fail(f"start from {ctx.main} (you are on '{ctx.cur}'): git switch {ctx.main}")
    d = ctx.dirty()
    if d:
        raise Fail("the working tree is not clean (" + ", ".join(d[:5]) + "). Commit or discard first; one story starts from a clean tree.")
    br = f"task/{sid}-{s['slug']}"
    rc, out = C.git(ctx.root, "switch", "-c", br)
    if rc != 0:
        raise Fail(f"git switch -c {br} failed: {out.strip()}")
    info = {**states[sid], "branch": br}
    path = render_prompt(ctx, "P1", story_mapping(ctx, s, info), f"{sid}-P1", s.get("addendum") or None)
    print(f"Started {sid}: you are now on branch {br}.")
    print(f"Author prompt written to {path.relative_to(ctx.root).as_posix()}\n")
    print("\n".join(story_steps(ctx, s, {**info, "state": "TODO"})[2:]))
    return 0


def cmd_prompt(ctx: Ctx, states: dict, which: list[str]) -> int:
    p = which[0].upper()
    if p == "P0":
        path = render_prompt(ctx, "P0", {}, "P0")
    elif p in ("P1", "P2"):
        if len(which) != 2 or which[1] not in ctx.by_id:
            raise Fail(f"usage: --prompt {p} US-03")
        s = ctx.by_id[which[1]]
        info = states[s["id"]]
        if p == "P2" and not info["branch"] and info["state"] != "ANOMALY":
            raise Fail(f"{s['id']} has no branch task/{s['id']}-*; the verifier works on the author's branch")
        path = render_prompt(ctx, p, story_mapping(ctx, s, info), f"{s['id']}-{p}", (s.get("addendum") or None) if p == "P1" else None)
    elif p == "P3":
        rows = []
        for s in ctx.stories:
            for d in s.get("requires_decisions") or []:
                if ctx.errata.get(d) == "OPEN" and d not in rows:
                    rows.append(d)
        path = render_prompt(ctx, "P3", {"ROWS": ", ".join(rows) or "every OPEN row"}, "P3")
    elif p == "P5":
        top = [s for s in ctx.stories if states[s["id"]]["state"] == "TODO"][: int(ctx.cfg["refine_top"])]
        probs = [f"- {s['id']}: {t}" for s in top for k, t in readiness(ctx, s, states) if k == "content"]
        path = render_prompt(ctx, "P5", {"PROBLEMS": "\n".join(probs) or "- none; add the next stories the owner asks for", "TOP": ", ".join(s["id"] for s in top)}, "P5")
    else:
        raise Fail("--prompt takes P0, P1, P2, P3 or P5")
    name = path.name[len("prompt-"):-len(".md")]
    print(f"Prompt written to {path.relative_to(ctx.root).as_posix()}")
    print("Copy it with:  " + CLIP.format(name=name))
    return 0


def cmd_accept(ctx: Ctx, states: dict, sid: str, note: str | None) -> int:
    need_owner("--accept")
    s = ctx.by_id.get(sid)
    if not s:
        raise Fail(f"{sid} is not in the backlog")
    inf = states[sid]
    if inf["accepted"]:
        raise Fail(f"{sid} is already accepted")
    if inf["base"] != "REVIEW":
        raise Fail(f"{sid} is {inf['state']}. Only a merged story with a complete handoff and an ACCEPT verdict from a different model can be accepted.")
    if inf["level"] is None:
        raise Fail("computed levels are unknown. Run py -3 tools\\tracker\\verify.py first.")
    if not inf["level_ok"]:
        raise Fail(f"{s['feature']} is computed at L{inf['level']}, below this story's target L{inf['target']}. Accepting would contradict the tracker; the story goes back for rework.")
    if not note or len(note.strip()) < 8:
        raise Fail('--note must say what you personally watched (at least 8 characters), e.g. --note "sent /pair from my phone; bot answered"')
    append_log(ctx.root, {"event": "accepted", "story": sid, "feature": s["feature"], "level": inf["level"], "note": note.strip(),
                          "date": ctx.today.isoformat(), "commit": C.git_head(ctx.root)[:12]})
    print(f"Accepted {sid} ({s['feature']} at L{inf['level']}). Recorded in tracker/sprints.jsonl; commit it with the other review files.")
    if s.get("completes_feature") is True:
        fid = s["feature"]
        print(f"\nThis story completes {fid}. Make it 100% (PROVEN) now:")
        print(f"  1. Save a screenshot or log of what you watched as tracker\\proof\\{fid}-evidence.png (or .txt)")
        print(f'  2. py -3 tools\\tracker\\record_proof.py {fid} --note "what I watched" --artifact tracker/proof/{fid}-evidence.png')
        print("  3. Paste the line it prints into tracker\\signoff.yaml")
    return 0


def cmd_retro(ctx: Ctx, states: dict) -> int:
    need_owner("--retro")
    a = ctx.active
    if not a:
        raise Fail("no active sprint")
    path = ctx.root / "tracker" / "retro" / f"{a['sprint']}.md"
    if path.is_file():
        print(f"{path.relative_to(ctx.root).as_posix()} already exists. Edit it; then run --close-sprint.")
        return 0
    mine = [ctx.by_id[x] for x in a.get("stories") or [] if x in ctx.by_id]
    acc = [s["id"] for s in mine if states[s["id"]]["state"] == "DONE"]
    rest = [f"{s['id']} ({states[s['id']]['state']})" for s in mine if states[s["id"]]["state"] != "DONE"]
    text = (f"# Retrospective {a['sprint']} ({a['start']} .. {a['end']})\n"
            f"Facts (generated, do not edit): planned {a.get('points')} points. Accepted: {', '.join(acc) or 'none'}. Not accepted: {', '.join(rest) or 'none'}.\n\n"
            "## Worked\n- <fill> one to three lines: what saved you time\n\n"
            "## Did not work\n- <fill> one to three lines: what cost you time or caused rework\n\n"
            "## One change\n<fill> exactly ONE line: the single thing that will be different next sprint\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    print(f"Created {path.relative_to(ctx.root).as_posix()}. Replace every <fill>, keep exactly one line under 'One change', then run --close-sprint.")
    return 0


def cmd_close(ctx: Ctx, states: dict) -> int:
    need_owner("--close-sprint")
    a = ctx.active
    if not a:
        raise Fail("no active sprint")
    sv = sprint_view(ctx)
    review_day = sv["slots"][-1]
    if ctx.today < review_day:
        raise Fail(f"the review slot of sprint {a['sprint']} is {fmt(review_day)}; close it then")
    probs = retro_problems(ctx.root / "tracker" / "retro" / f"{a['sprint']}.md")
    if probs:
        raise Fail("retrospective is not finished: " + "; ".join(probs))
    counted: set[str] = set()
    for s in ctx.sprints:
        if s["closed"]:
            counted |= set(s["closed"].get("done") or [])
    done = [sid for sid in ctx.accepted if sid in ctx.by_id and sid not in counted]
    vel = sum(pts(ctx.by_id[sid]) for sid in done)
    not_done = {sid: states[sid]["state"] for sid in (a.get("stories") or []) if sid in states and sid not in done and states[sid]["state"] != "DONE"}
    append_log(ctx.root, {"event": "closed", "sprint": a["sprint"], "date": ctx.today.isoformat(), "planned_points": a.get("points"),
                          "velocity": vel, "done": done, "not_done": not_done})
    ctx2 = Ctx(ctx.root, ctx.today)
    cap, why = capacity_next(ctx2)
    print(f"Closed {a['sprint']}: velocity {vel} points (planned {a.get('points')}). Accepted: {', '.join(done) or 'none'}. Not accepted: {json.dumps(not_done)}")
    print(f"Capacity for the next sprint: {cap} points ({why}).")
    chg = [ln for ln in (ctx.root / "tracker" / "retro" / f"{a['sprint']}.md").read_text(encoding="utf-8").split("## One change", 1)[1].splitlines() if ln.strip()]
    print(f"Retro change to apply next sprint: {chg[0].strip() if chg else ''}")
    return 0


def main(argv: list[str] | None = None) -> int:
    C.utf8_stdio()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root")
    ap.add_argument("--today")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--calendar", action="store_true")
    ap.add_argument("--refine", action="store_true")
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--goal")
    ap.add_argument("--start")
    ap.add_argument("--prompt", nargs="+", metavar="P")
    ap.add_argument("--accept")
    ap.add_argument("--note")
    ap.add_argument("--retro", action="store_true")
    ap.add_argument("--close-sprint", action="store_true")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[2]
    try:
        today = as_date(args.today) if args.today else date.today()
        ctx = Ctx(root, today)
        states = derive(ctx)
        if args.check:
            return cmd_check(ctx, states)
        if args.calendar:
            return cmd_calendar(ctx)
        if args.refine:
            return cmd_refine(ctx, states)
        if args.plan:
            return cmd_plan(ctx, states, args.write, args.goal)
        if args.start:
            return cmd_start(ctx, states, args.start)
        if args.prompt:
            return cmd_prompt(ctx, states, args.prompt)
        if args.accept:
            return cmd_accept(ctx, states, args.accept, args.note)
        if args.retro:
            return cmd_retro(ctx, states)
        if args.close_sprint:
            return cmd_close(ctx, states)
        return cmd_board(ctx, states, args.json)
    except Fail as e:
        print(f"REFUSED: {e}")
        return 2
    except ValueError as e:
        print(f"REFUSED: bad value in tracker/backlog.yaml or arguments: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
