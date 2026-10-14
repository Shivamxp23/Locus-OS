#!/usr/bin/env python3
"""Compute every feature's status from evidence. Nobody types a status.

    python tools/tracker/verify.py                    # runs the guard + every declared test command
    python tools/tracker/verify.py --static           # files / symbols / guard only (no test commands)
    python tools/tracker/verify.py --only F-0007,F-0061
    python tools/tracker/verify.py --fail-on-regression --fail-on-guard     # CI

Writes tracker/status.json, tracker/STATUS.md and appends to tracker/history.jsonl.

THE LADDER (strict; a level needs every level below it)
  L0 NO_EVIDENCE    0%   nothing declared, or declared files are missing
  L1 FILES_PRESENT  15%  every declared file exists and is non-empty
  L2 IMPLEMENTED    40%  declared symbols exist (outside comments), are not stubs, no `STUB(F-xxxx)` markers
  L3 UNIT_VERIFIED  65%  declared unit commands / guard checks pass, and the tests are real:
                         a recognised runner, an existing test file that mentions what the feature
                         implements, at least one real assertion, at least one test that actually PASSED
  L4 INTEGRATED     85%  declared integration commands pass under the same rules, and differ from the unit ones
  L5 PROVEN        100%  a proof recorded by record_proof.py is current AND the human's signoff names that proof
  INHERITED_OK     100%  KEEP-PI feature: every evidence file is under packages/, exists, and packages/ matches the pinned upstream

What this cannot catch: an agent that deliberately writes tests which call the code and assert nothing true,
or edits this script. That is what the human-review gate (tools/ is human-owned), CI and your diff review are for.
"""
from __future__ import annotations

import argparse
import ast
import io
import json
import os
import re
import subprocess
import sys
import time
import tokenize
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import locus_common as C  # noqa: E402

LEVELS = {0: ("NO_EVIDENCE", 0), 1: ("FILES_PRESENT", 15), 2: ("IMPLEMENTED", 40), 3: ("UNIT_VERIFIED", 65),
          4: ("INTEGRATED", 85), 5: ("PROVEN", 100)}
INH = ("INHERITED_OK", 100)
OVERCLAIM_GAP = 25
GENERIC_STEMS = {"index", "main", "init", "__init__", "utils", "util", "helpers", "types", "common", "base", "app", "server", "cli", "config"}


# ------------------------------------------------------------- comment stripping
def _strip_js(text: str) -> str:
    out: list[str] = []
    i, n, q = 0, len(text), ""
    while i < n:
        c = text[i]
        if q:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if c == q or (c == "\n" and q in "'\""):  # '/" strings end at the line end (a stray apostrophe must not eat the file)
                q = ""
            i += 1
            continue
        if c in "'\"`":
            q = c
            out.append(c)
            i += 1
            continue
        if c == "/" and text.startswith("//", i):
            j = text.find("\n", i)
            if j == -1:
                break
            i = j
            continue
        if c == "/" and text.startswith("/*", i):
            j = text.find("*/", i + 2)
            if j == -1:
                break
            out.append("\n" * text.count("\n", i, j))
            i = j + 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


def _strip_py(text: str) -> str:
    try:
        comments = [t for t in tokenize.generate_tokens(io.StringIO(text).readline) if t.type == tokenize.COMMENT]
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return text
    lines = text.splitlines(keepends=True)
    for t in reversed(comments):
        row, col = t.start
        ln = lines[row - 1]
        lines[row - 1] = ln[:col].rstrip() + ("\n" if ln.endswith("\n") else "")
    return "".join(lines)


def strip_comments(text: str, suffix: str) -> str:
    """A comment must never satisfy a `contains` / symbol check."""
    suffix = suffix.lower()
    if suffix == ".py":
        return _strip_py(text)
    if suffix in {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}:
        return _strip_js(text)
    if suffix in {".yml", ".yaml", ".toml", ".sh", ".ps1", ".ini", ".cfg", ".env"}:
        return "\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith("#"))
    return text


# ----------------------------------------------------------------- evidence probes
def files_status(root: Path, files: list[str]) -> tuple[list[str], list[str]]:
    present, missing = [], []
    for f in files:
        f = str(f)
        if any(ch in f for ch in "*?["):
            ok = bool(list(root.glob(f)))
        elif f.endswith("/") or (root / f).is_dir():
            d = root / f.rstrip("/")
            ok = d.is_dir() and any(p.is_file() and not p.name.startswith(".") and "__pycache__" not in p.parts for p in d.rglob("*"))
        else:
            p = root / f
            ok = p.is_file() and p.stat().st_size > 0
        (present if ok else missing).append(f)
    return present, missing


def _is_stub_body(body: list[ast.stmt]) -> bool:
    stmts = list(body)
    if stmts and isinstance(stmts[0], ast.Expr) and isinstance(getattr(stmts[0], "value", None), ast.Constant) and isinstance(stmts[0].value.value, str):
        stmts = stmts[1:]
    if not stmts:
        return True
    for s in stmts:
        if isinstance(s, ast.Pass):
            continue
        if isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant) and s.value.value is Ellipsis:
            continue
        if isinstance(s, ast.Raise):
            exc = s.exc
            name = ""
            if isinstance(exc, ast.Call) and isinstance(exc.func, ast.Name):
                name = exc.func.id
            elif isinstance(exc, ast.Name):
                name = exc.id
            if name == "NotImplementedError":
                continue
        return False
    return True


def py_symbol(text: str, name: str) -> tuple[bool, bool]:
    """(found, is_stub)"""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return False, False
    found, stub = False, False
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            found = True
            stub = stub or _is_stub_body(node.body)
        elif isinstance(node, ast.ClassDef) and node.name == name:
            found = True
            methods = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            stub = stub or (bool(methods) and all(_is_stub_body(m.body) for m in methods))
    return found, stub


def ts_symbol(text: str, name: str) -> tuple[bool, bool]:
    n = re.escape(name)
    rx = re.compile(rf"(?:function\*?|class|interface|type|enum|const|let|var)\s+{n}\b|(?:^|\s){n}\s*[:=]\s*(?:async\s*)?(?:\(|function)|^\s*(?:public\s+|private\s+|async\s+|static\s+)*{n}\s*\([^)]*\)\s*(?::[^{{]+)?\{{", re.M)
    m = rx.search(text)
    if not m:
        return False, False
    window = text[m.end(): m.end() + 400]
    stub = bool(re.match(r"[^}]{0,200}(throw new Error\(['\"`][^'\"`]*not implemented|TODO|FIXME)", window, re.I | re.S))
    return True, stub


def symbols_status(root: Path, fid: str, symbols: list, files: list[str]) -> tuple[bool, list[str]]:
    problems: list[str] = []
    for spec in symbols:
        if not isinstance(spec, dict) or "file" not in spec:
            problems.append(f"malformed symbol entry: {spec!r}")
            continue
        p = root / spec["file"]
        raw = C.read_text(p) if p.is_file() else None
        if raw is None:
            problems.append(f"{spec['file']}: file missing/unreadable")
            continue
        text = strip_comments(raw, p.suffix)
        for sub in spec.get("contains", []) or []:
            if sub not in text:
                problems.append(f"{spec['file']}: does not contain `{sub}` (comments do not count)")
        if spec.get("pattern") and not re.search(spec["pattern"], text, re.M):
            problems.append(f"{spec['file']}: pattern /{spec['pattern']}/ not found (comments do not count)")
        if spec.get("name"):
            nm = spec["name"]
            fn = py_symbol if p.suffix == ".py" else ts_symbol
            found, stub = fn(text, nm)
            if not found:
                problems.append(f"{spec['file']}: `{nm}` is not defined")
            elif stub:
                problems.append(f"{spec['file']}: `{nm}` is a stub (empty / pass / not implemented)")
    for f in files:
        p = root / f
        if p.is_file() and p.suffix.lower() in C.TEXT_EXTS:
            t = C.read_text(p)
            if t and f"STUB({fid})" in t:
                problems.append(f"{f}: contains declared stub marker STUB({fid})")
    return (not problems), problems


# ------------------------------------------------------------------ test analysis
TEST_FILE_RX = re.compile(r"(?:^|/)(?:test_[^/]*\.py|[^/]*_test\.py|[^/]*\.(?:test|spec)\.(?:ts|tsx|js|jsx|mjs|cjs))$")
_JS_TEST = re.compile(r"(?<![\w.])(?:it|test)(?:\.each\([^)]*\))?\s*\(")
_JS_SKIP = re.compile(r"\b(?:it|test|describe)\.(?:skip|todo)\b|\bx(?:it|describe)\s*\(")
_JS_ASSERT = re.compile(r"\bexpect\s*\(|\bassert(?:\.\w+)?\s*\(|\bt\.(?:is|true|false|deepEqual|throws|equal|regex|truthy|falsy)\s*\(")
_LIT = r"(?:true|false|1|0|null|undefined|'[^']*'|\"[^\"]*\")"
_JS_TRIVIAL = re.compile(rf"expect\s*\(\s*{_LIT}\s*\)\s*\.\s*(?:toBe|toEqual|toStrictEqual)\s*\(\s*{_LIT}\s*\)|assert\s*\(\s*true\s*\)|assert\.ok\s*\(\s*true\s*\)")
PASS_RX = {"pytest": r"\b[1-9]\d* passed\b", "unittest": r"\bRan [1-9]\d* tests?\b", "vitest": r"\b[1-9]\d* passed\b",
           "jest": r"\b[1-9]\d* passed\b", "node-test": r"#\s*pass\s+[1-9]"}


def analyze_test_file(path: Path) -> tuple[int, int]:
    """(test functions, meaningful assertions) for a Python test file. Constant / self-comparing asserts do not count."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return 0, 0
    tests = meaningful = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
            tests += 1
            for sub in ast.walk(node):
                if isinstance(sub, ast.Assert):
                    t = sub.test
                    if isinstance(t, ast.Constant):
                        continue
                    if isinstance(t, ast.Compare) and len(t.comparators) == 1 and ast.dump(t.left) == ast.dump(t.comparators[0]):
                        continue
                    meaningful += 1
                elif isinstance(sub, ast.Call):
                    fn = sub.func
                    attr = fn.attr if isinstance(fn, ast.Attribute) else (fn.id if isinstance(fn, ast.Name) else "")
                    if attr.startswith("assert") or attr in {"raises", "fail"}:
                        meaningful += 1
    return tests, meaningful


def analyze_js_test_file(path: Path) -> tuple[int, int]:
    text = strip_comments(C.read_text(path) or "", path.suffix)
    tests = len(_JS_TEST.findall(text)) - len(_JS_SKIP.findall(text))
    meaningful = len(_JS_ASSERT.findall(text)) - len(_JS_TRIVIAL.findall(text))
    return max(tests, 0), max(meaningful, 0)


def detect_runner(cmd: str) -> str | None:
    lc = cmd.lower()
    if re.search(r"\bpytest\b|\bpy\.test\b", lc):
        return "pytest"
    if re.search(r"-m\s+unittest\b", lc):
        return "unittest"
    if re.search(r"\bvitest\b", lc):
        return "vitest"
    if re.search(r"\bjest\b", lc):
        return "jest"
    if re.search(r"\bnode\b[^|&;]*--test\b", lc):
        return "node-test"
    return None


def resolve_test_files(root: Path, cmd: str) -> list[Path]:
    """Test files named by the command (files directly, or found inside folders it names)."""
    found: dict[str, Path] = {}
    skip = {"node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".git"}
    for tok in re.findall(r"[\w./\\@\-]+", cmd):
        t = tok.replace("\\", "/")
        if t.startswith("./"):
            t = t[2:]
        if not t or t.startswith("-"):
            continue
        p = root / t
        if p.is_file():
            if TEST_FILE_RX.search(t):
                found[t] = p
        elif p.is_dir():
            for sub in sorted(p.rglob("*")):
                if sub.is_file() and not (set(sub.parts) & skip):
                    r = sub.relative_to(root).as_posix()
                    if TEST_FILE_RX.search(r):
                        found[r] = sub
    return list(found.values())


def relation_terms(f: dict) -> set[str]:
    """Words a real test of this feature must mention: its declared symbols and its file names."""
    ev = f.get("evidence") or {}
    terms: set[str] = set()
    for s in ev.get("symbols") or []:
        if isinstance(s, dict) and s.get("name"):
            terms.add(str(s["name"]))
    for p in ev.get("files") or []:
        stem = Path(str(p).rstrip("/")).stem
        if len(stem) >= 4 and stem not in GENERIC_STEMS and not any(ch in stem for ch in "*?["):
            terms.add(stem)
    return terms


def norm_cmd(c) -> dict:
    return {"cmd": c} if isinstance(c, str) else dict(c)


def judge_test_command(root: Path, c: dict, terms: set[str]) -> tuple[str | None, bool, str]:
    """-> (runner, vacuous, why). Static analysis only; nothing is executed here."""
    cmd = c.get("cmd", "")
    runner = detect_runner(cmd)
    if runner is None:
        if c.get("expect_regex"):
            return None, False, ""
        return None, True, "not a recognised test runner (pytest/unittest/vitest/jest/node --test) and no expect_regex to prove success"
    files = resolve_test_files(root, cmd)
    if not files:
        return runner, True, "the command names no existing test file or folder"
    rows = []
    for fp in files:
        a, b = analyze_test_file(fp) if fp.suffix == ".py" else analyze_js_test_file(fp)
        text = C.read_text(fp) or ""
        related = (not terms) or any(t in text for t in terms)
        rows.append((fp, a, b, related))
    rel = [r for r in rows if r[3]]
    if not rel:
        return runner, True, "no test file mentions what the feature implements (" + ", ".join(sorted(terms)[:3]) + ")"
    if sum(r[1] for r in rel) == 0:
        return runner, True, "the related test files contain no test functions"
    if sum(r[2] for r in rel) == 0:
        return runner, True, "the related tests contain no real assertions"
    return runner, False, ""


def run_commands(root: Path, cmds: list, run: bool, terms: set[str] | None = None) -> list[dict]:
    results = []
    for raw in cmds or []:
        c = norm_cmd(raw)
        runner, vacuous, why = judge_test_command(root, c, terms or set())
        res = {"cmd": c.get("cmd", ""), "runner": runner, "ran": False, "ok": None, "exit": None, "tail": "",
               "vacuous": vacuous, "why_vacuous": why, "seconds": 0.0}
        if run:
            t0 = time.time()
            try:
                p = subprocess.run(res["cmd"], shell=True, cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace",
                                   timeout=int(c.get("timeout", 600)), env={**os.environ, "PYTHONIOENCODING": "utf-8"})
                out = (p.stdout or "") + (p.stderr or "")
                res.update(ran=True, exit=p.returncode, tail=out[-600:])
                ok = p.returncode == 0
                if ok and runner and not re.search(PASS_RX[runner], out):
                    ok = False
                    res["tail"] = "(no test reported PASSED: skipped or empty runs do not count) " + res["tail"]
                if ok and c.get("expect_regex"):
                    ok = bool(re.search(c["expect_regex"], out))
                res["ok"] = ok
            except subprocess.TimeoutExpired:
                res.update(ran=True, ok=False, exit=-1, tail="timeout")
            res["seconds"] = round(time.time() - t0, 1)
        results.append(res)
    return results


def known_guard_ids(cfg: dict) -> set[str]:
    ids = set(C.GUARD_CHECK_IDS)
    ids |= {r["id"] for r in cfg.get("forbidden_text", [])}
    ids |= {r["id"] for r in cfg.get("stale_paths", [])}
    return ids


# --------------------------------------------------------------------- evaluation
def next_step(level: int, f: dict, missing: list[str], problems: list[str], ev: dict, manual: bool) -> str:
    if missing:
        return "Files claimed but absent: " + ", ".join(missing[:4]) + (" ..." if len(missing) > 4 else "") + ". Create them or correct the path."
    if level == 0:
        return "Name the files this feature lives in (evidence.files)."
    if level == 1:
        return problems[0] if problems else "Declare evidence.symbols that prove the implementation exists."
    if level == 2 and not manual:
        return "Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with real assertions) or evidence.guard checks."
    if level == 3 and not manual:
        return "Add evidence.integration: a DIFFERENT test that crosses a boundary (sidecar<->Pi, extension<->Pi, service<->service)."
    return "Run tools/tracker/record_proof.py, then the human adds the printed line to tracker/signoff.yaml."


def evaluate(root: Path, f: dict, run: bool, guard_report: dict | None, upstream_ok: bool | None,
             proofs_dir: Path, signoff: dict, overrides: dict, spec_sha: dict[str, str],
             guard_ids: set[str] | None = None) -> dict:
    fid = f["id"]
    ev = f.get("evidence") or {}
    files = [str(x) for x in (ev.get("files") or [])]
    manual = bool(f.get("manual"))
    inherited = bool(f.get("inherited"))
    reasons: list[str] = []
    flags: list[str] = []
    checks: dict = {}
    level = 0
    missing: list[str] = []
    problems: list[str] = []

    if inherited and not (files and all(x.startswith("packages/") for x in files)):
        inherited = False
        flags.append("INHERITED_INVALID")
        reasons.append("marked inherited, but not every evidence file is under packages/: treated as normal Locus code")

    if files:
        _, missing = files_status(root, files)
        if not missing:
            level = 1
        else:
            reasons.append("declared files missing: " + ", ".join(missing[:6]))
            flags.append("CLAIMED_FILES_MISSING")
    else:
        reasons.append("no evidence files declared")
        claimed = (f.get("claimed") or {}).get("pct")
        if isinstance(claimed, (int, float)) and claimed > 0:
            flags.append("NO_FILES_NAMED")

    label_override = None
    if level >= 1 and inherited:
        if upstream_ok:
            label_override = INH
        else:
            reasons.append("upstream pin missing or packages/ differs: cannot confirm it is inherited unmodified")
    elif level >= 1:
        symbols = ev.get("symbols") or []
        if not symbols:
            reasons.append("no symbols declared: file existence alone proves nothing")
        else:
            ok, problems = symbols_status(root, fid, symbols, files)
            checks["symbols"] = {"ok": ok, "problems": problems}
            if ok:
                level = 2
            else:
                reasons += problems[:4]
        if level >= 2 and not manual:
            terms = relation_terms(f)
            unit = run_commands(root, ev.get("unit") or [], run, terms)
            gnames = ev.get("guard") or []
            gres = []
            valid = guard_ids if guard_ids is not None else set(C.GUARD_CHECK_IDS)
            for g in gnames:
                if g not in valid:
                    gres.append({"check": g, "ok": False, "why": "unknown guard check id (typo? it would pass vacuously)"})
                elif guard_report is None:
                    gres.append({"check": g, "ok": False, "why": "no guard report"})
                else:
                    bad = [x for x in guard_report["findings"] if x["check"] == g and x["severity"] == "FAIL"]
                    gres.append({"check": g, "ok": not bad, "why": (bad[0]["message"][:100] if bad else "")})
            checks["unit"], checks["guard"] = unit, gres
            have_any = bool(unit or gres)
            if not have_any:
                reasons.append("no unit tests or guard checks declared")
            else:
                pending = [u for u in unit if u["ok"] is None]
                failed = [u for u in unit if u["ok"] is False] + [g for g in gres if not g["ok"]]
                vac = [u for u in unit if u["vacuous"]]
                if pending:
                    reasons.append(f"{len(pending)} unit command(s) declared but not run (--static)")
                elif vac:
                    reasons.append(f"unit test does not count ({vac[0]['why_vacuous']}): " + vac[0]["cmd"][:80])
                    flags.append("VACUOUS_TESTS")
                elif failed:
                    reasons.append("failing: " + "; ".join((x.get("cmd") or x.get("check")) + (" -> " + x["why"] if x.get("why") else "") for x in failed)[:200])
                else:
                    level = 3
        if level >= 3 and not manual:
            unit_cmds = {norm_cmd(x).get("cmd") for x in ev.get("unit") or []}
            integ_raw = ev.get("integration") or []
            dup = [norm_cmd(x).get("cmd") for x in integ_raw if norm_cmd(x).get("cmd") in unit_cmds]
            integ = run_commands(root, integ_raw, run, relation_terms(f))
            checks["integration"] = integ
            if not integ:
                reasons.append("no integration test declared")
            elif dup:
                reasons.append("integration command is identical to a unit command: " + dup[0][:80])
            else:
                pending = [u for u in integ if u["ok"] is None]
                failed = [u for u in integ if u["ok"] is False]
                vac = [u for u in integ if u["vacuous"]]
                if pending:
                    reasons.append(f"{len(pending)} integration command(s) declared but not run (--static)")
                elif vac:
                    reasons.append(f"integration test does not count ({vac[0]['why_vacuous']}): " + vac[0]["cmd"][:80])
                    flags.append("VACUOUS_TESTS")
                elif failed:
                    reasons.append("integration failing: " + "; ".join(x["cmd"] for x in failed)[:200])
                else:
                    level = 4
        gate = 4 if not manual else 2
        if level >= gate:
            pf = proofs_dir / f"{fid}.json"
            if pf.is_file():
                proof = json.loads(pf.read_text(encoding="utf-8"))
                cur = C.sha256_paths(root, files)
                entry = signoff.get(fid) if isinstance(signoff, dict) else None
                if proof.get("exit") != 0:
                    reasons.append("recorded proof run failed")
                elif proof.get("files_sha256") != cur:
                    reasons.append("proof is STALE: evidence files changed since it was recorded")
                    flags.append("PROOF_STALE")
                elif entry is None:
                    reasons.append("proof recorded; waiting for human signoff (tracker/signoff.yaml)")
                elif not (isinstance(entry, dict) and entry.get("by") and entry.get("date") and entry.get("proof")):
                    reasons.append("signoff entry must have by:, date: and proof: (the id printed by record_proof.py)")
                elif str(entry.get("proof"))[:12] != str(proof.get("files_sha256", ""))[:12]:
                    reasons.append("signoff names an older proof: the human must re-sign the newly recorded proof")
                    flags.append("SIGNOFF_STALE")
                else:
                    level = 5
            else:
                reasons.append("no recorded proof")

    cap = (overrides.get(fid) or {}).get("cap_level") if isinstance(overrides, dict) else None
    if cap is not None and level > int(cap):
        level = int(cap)
        flags.append("CAPPED_BY_HUMAN")
        label_override = None
    label, pct = label_override or LEVELS[level]

    claimed_pct = (f.get("claimed") or {}).get("pct")
    try:
        claimed_pct = float(claimed_pct) if claimed_pct is not None else None
    except (TypeError, ValueError):
        claimed_pct = None
    gap = None if claimed_pct is None else round(claimed_pct - pct, 1)
    if gap is not None and gap >= OVERCLAIM_GAP:
        flags.append("OVERCLAIM")
    if f.get("mapping") == "low-confidence":
        flags.append("LOW_CONFIDENCE_MAPPING")
    for ref, old in (f.get("spec_sha") or {}).items():
        cur = spec_sha.get(C.norm_key(ref))
        if cur is None:
            flags.append("SPEC_REF_DANGLING")
        elif cur != old:
            flags.append("SPEC_CHANGED")
    flags = sorted(set(flags))
    return {"id": fid, "title": f.get("title"), "verdict": f.get("verdict"), "level": level, "label": label, "pct": pct,
            "claimed_pct": claimed_pct, "gap": gap, "flags": flags, "reasons": reasons,
            "next": "" if label == "PROVEN" or (label == INH[0]) else next_step(level, f, missing, problems, ev, manual),
            "checks": checks}


# ------------------------------------------------------------------------- output
SHOWN_FLAGS = {"OVERCLAIM", "CLAIMED_FILES_MISSING", "NO_FILES_NAMED", "VACUOUS_TESTS", "PROOF_STALE", "SIGNOFF_STALE", "SPEC_CHANGED", "INHERITED_INVALID"}


def md_table(results: list[dict]) -> str:
    lines = ["| ID | Feature | Claimed | Verified | Level | Flags | Next step |", "|---|---|---:|---:|---|---|---|"]
    for r in results:
        cl = "-" if r["claimed_pct"] is None else f"{r['claimed_pct']:.0f}%"
        title = (r["title"] or "")[:44].replace("|", "/")
        flags = ",".join(x for x in r["flags"] if x in SHOWN_FLAGS)
        nxt = (r["next"] or "").replace("|", "/")[:90]
        lines.append(f"| {r['id']} | {title} | {cl} | {r['pct']}% | {r['label']} | {flags} | {nxt} |")
    return "\n".join(lines)


def main() -> int:
    C.utf8_stdio()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root")
    ap.add_argument("--static", action="store_true", help="do not execute test commands")
    ap.add_argument("--only", help="comma-separated feature ids")
    ap.add_argument("--no-guard", action="store_true", help="reuse the last guard report instead of re-running the guard")
    ap.add_argument("--fail-on-regression", action="store_true")
    ap.add_argument("--fail-on-guard", action="store_true")
    ap.add_argument("--no-write", action="store_true", help="print only")
    args = ap.parse_args()
    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[2]
    cfg = C.load_toml(root / "tools" / "guard" / "guard.toml")
    data = C.load_yaml(root / "tracker" / "features.yaml")
    feats = data["features"]
    only = set(args.only.split(",")) if args.only else None

    report_path = root / "tracker" / ".cache" / "guard_report.json"
    if not args.no_guard:
        subprocess.run([sys.executable, str(root / "tools" / "guard" / "check.py"), "--full", "--root", str(root), "--json", str(report_path)],
                       capture_output=True, text=True)
    guard_report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.is_file() else None
    if guard_report is not None and (guard_report.get("mode") != "full" or guard_report.get("only")):
        guard_report = None  # a fast or --only run did not look at everything; "no FAIL" there proves nothing
    upstream_ok = None
    if guard_report is not None:
        has_pin = (root / cfg.get("upstream", {}).get("lock_file", "tools/guard/upstream.lock.json")).is_file()
        upstream_ok = has_pin and not any(x["check"] == "upstream-clean" and x["severity"] == "FAIL" for x in guard_report["findings"])

    spec_sha: dict[str, str] = {}
    sp = root / cfg["repo"]["spec_path"]
    if sp.is_file():
        spec_sha = {h["key"]: h["sha"] for h in C.parse_spec(sp)["headings"]}
    signoff = (C.load_yaml(root / "tracker" / "signoff.yaml") if (root / "tracker" / "signoff.yaml").is_file() else {}) or {}
    overrides = (C.load_yaml(root / "tracker" / "overrides.yaml") if (root / "tracker" / "overrides.yaml").is_file() else {}) or {}
    gids = known_guard_ids(cfg)

    results = []
    for f in feats:
        if only and f["id"] not in only:
            continue
        results.append(evaluate(root, f, not args.static, guard_report, upstream_ok, root / "tracker" / "proof", signoff, overrides, spec_sha, gids))

    # ---- summary
    n = len(results)
    mean = lambda xs: round(sum(xs) / len(xs), 1) if xs else 0.0  # noqa: E731
    by_label: dict[str, int] = {}
    for r in results:
        by_label[r["label"]] = by_label.get(r["label"], 0) + 1
    claimed = [r["claimed_pct"] for r in results if r["claimed_pct"] is not None]
    summary = {
        "features": n, "verified_mean_pct": mean([r["pct"] for r in results]),
        "claimed_mean_pct": mean(claimed), "claimed_rows": len(claimed),
        "by_label": dict(sorted(by_label.items())),
        "integrated_or_better": sum(1 for r in results if r["level"] >= 4 or r["label"] == INH[0]),
        "proven": sum(1 for r in results if r["level"] == 5),
        "overclaims": sum(1 for r in results if "OVERCLAIM" in r["flags"]),
        "no_evidence": sum(1 for r in results if r["level"] == 0),
        "spec_sections_total": len(spec_sha),
        "spec_changed": sum(1 for r in results if "SPEC_CHANGED" in r["flags"]),
    }
    commit, dirty = C.git_head(root), C.git_dirty(root)
    guard_sum = None if guard_report is None else {"verdict": guard_report["verdict"], "counts": guard_report["counts"]}
    status = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "commit": commit, "dirty": dirty, "static": args.static,
              "guard": guard_sum, "summary": summary, "features": {r["id"]: r for r in results}}

    # ---- regressions vs the previous run of the SAME kind (a static run never executes tests, so it is not comparable with a full one)
    hist_path = root / "tracker" / "history.jsonl"
    regressions = []
    if hist_path.is_file() and not only:
        last = None
        for line in hist_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                entry = json.loads(line)
                if bool(entry.get("static")) == bool(args.static):
                    last = entry
        if last:
            for r in results:
                prev = last["levels"].get(r["id"])
                if prev is not None and r["pct"] < prev:
                    regressions.append(f"{r['id']} {r['title'][:40]}: {prev}% -> {r['pct']}%")
    status["regressions"] = regressions

    if not args.no_write and not only:
        C.json_dump(status, root / "tracker" / "status.json")
        order = sorted(results, key=lambda r: (-(r["gap"] or 0), r["id"]))[:20]
        md = ["# Tracker status (computed, not written)", "",
              f"- commit `{commit[:10]}`{' (dirty working tree)' if dirty else ''} - {status['generated_at']} - {'static' if args.static else 'with test runs'}",
              f"- guard: {guard_sum['verdict'] if guard_sum else 'not run'} {guard_sum['counts'] if guard_sum else ''}",
              f"- features: {n} | verified average **{summary['verified_mean_pct']}%** | old claimed average {summary['claimed_mean_pct']}% over {summary['claimed_rows']} rows",
              f"- integrated or better: {summary['integrated_or_better']} | proven: {summary['proven']} | overclaims (claimed >= verified + {OVERCLAIM_GAP}): {summary['overclaims']} | no evidence: {summary['no_evidence']}",
              f"- by level: {summary['by_label']}", ""]
        if regressions:
            md += ["## REGRESSIONS since last run", *[f"- {x}" for x in regressions], ""]
        md += ["## Biggest gaps between old claim and evidence", md_table(order), "", "## All features", md_table(results), ""]
        (root / "tracker" / "STATUS.md").write_text("\n".join(md), encoding="utf-8", newline="\n")
        with open(hist_path, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps({"ts": status["generated_at"], "commit": commit, "dirty": dirty, "static": bool(args.static),
                                 "mean": summary["verified_mean_pct"], "levels": {r["id"]: r["pct"] for r in results}},
                                separators=(",", ":")) + "\n")

    print(f"features {n} | verified avg {summary['verified_mean_pct']}% | old claimed avg {summary['claimed_mean_pct']}% | "
          f"integrated+ {summary['integrated_or_better']} | proven {summary['proven']} | overclaims {summary['overclaims']} | no-evidence {summary['no_evidence']}")
    print("by level:", summary["by_label"])
    if guard_sum:
        print("guard:", guard_sum["verdict"], guard_sum["counts"])
    for x in regressions:
        print("REGRESSION", x)
    if only:
        for r in results:
            print(json.dumps({k: r[k] for k in ("id", "label", "pct", "flags", "reasons", "next")}, ensure_ascii=False))
    rc = 0
    if args.fail_on_regression and regressions:
        rc = 1
    if args.fail_on_guard and guard_sum and guard_sum["verdict"] == "FAIL":
        rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
