"""Shared helpers for the Locus guard and tracker tools.

Stdlib + PyYAML (+ openpyxl in export/import). Python 3.11+ (tomllib).
Nothing here talks to an LLM. Everything is deterministic.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

try:
    import yaml  # PyYAML
except ImportError:  # pragma: no cover
    sys.stderr.write("PyYAML missing. Run: python -m pip install pyyaml openpyxl pytest\n")
    raise

import tomllib


# --------------------------------------------------------------------------- io
def utf8_stdio() -> None:
    """Windows consoles choke on emoji / box characters; force UTF-8."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass


def load_toml(path: Path) -> dict:
    with open(path, "rb") as fh:
        return tomllib.load(fh)


def load_yaml(path: Path):
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def dump_yaml(obj, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        yaml.safe_dump(obj, fh, sort_keys=False, allow_unicode=True, width=110)


def read_text(path: Path, limit: int = 2_000_000) -> str | None:
    try:
        if path.stat().st_size > limit:
            return None
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_paths(root: Path, rel_paths: list[str]) -> str:
    """Stable hash over the content of files (and every file inside listed dirs)."""
    h = hashlib.sha256()
    files: list[Path] = []
    for rel in sorted(rel_paths):
        p = root / rel
        if p.is_dir():
            for sub in sorted(p.rglob("*")):
                if sub.is_file() and "__pycache__" not in sub.parts:
                    files.append(sub)
        elif p.is_file():
            files.append(p)
    for f in files:
        h.update(f.relative_to(root).as_posix().encode())
        h.update(b"\0")
        h.update(sha256_file(f).encode())
        h.update(b"\0")
    return h.hexdigest()


# -------------------------------------------------------------------------- git
def git(root: Path, *args: str) -> tuple[int, str]:
    try:
        p = subprocess.run(
            ["git", *args], cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        return p.returncode, (p.stdout or "") + (p.stderr if p.returncode else "")
    except FileNotFoundError:
        return 127, "git not found"


def git_head(root: Path) -> str:
    rc, out = git(root, "rev-parse", "HEAD")
    return out.strip() if rc == 0 else "no-commit"


def git_dirty(root: Path) -> bool:
    rc, out = git(root, "status", "--porcelain")
    return rc == 0 and bool(out.strip())


# ------------------------------------------------------------------- file walk
DEFAULT_SKIP_DIRS = {
    ".git", "node_modules", ".venv", "venv", "__pycache__", ".mypy_cache", ".pytest_cache",
    ".ruff_cache", "dist", "build", ".next", ".turbo", "graphify-out", ".idea", ".vscode",
}

TEXT_EXTS = {
    ".py", ".ts", ".tsx", ".js", ".mjs", ".cjs", ".json", ".yml", ".yaml", ".toml", ".ini", ".cfg",
    ".md", ".txt", ".sh", ".ps1", ".bat", ".cmd", ".service", ".env", ".sql", ".html", ".css",
    ".rs", ".go", ".conf", ".example",
}


def iter_files(root: Path, skip_dirs: set[str] | None = None, skip_rel: list[str] | None = None):
    """Yield files under root, pruning skip dirs (by name at any depth) and skip_rel prefixes."""
    skip = set(DEFAULT_SKIP_DIRS) | (skip_dirs or set())
    skip_rel = [s.strip("/").replace("\\", "/") for s in (skip_rel or [])]
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = Path(dirpath).relative_to(root).as_posix()
        rel_dir = "" if rel_dir == "." else rel_dir
        keep = []
        for d in dirnames:
            rel = f"{rel_dir}/{d}" if rel_dir else d
            if d in skip or any(rel == s or rel.startswith(s + "/") for s in skip_rel):
                continue
            keep.append(d)
        dirnames[:] = keep
        for fn in filenames:
            yield Path(dirpath) / fn


def is_text_file(p: Path) -> bool:
    name = p.name
    if name in {"Dockerfile", "Makefile", ".gitignore", ".env", ".gitattributes"}:
        return True
    if name.startswith("Dockerfile") or name.startswith("docker-compose"):
        return True
    return p.suffix.lower() in TEXT_EXTS


def rel(root: Path, p: Path) -> str:
    return p.relative_to(root).as_posix()


# ------------------------------------------------------------------------ spec
SECT = "\u00a7"
_RANGE = re.compile(r"^(\d+)\.(\d+)[a-z]?\s*[-–]\s*(?:(\d+)\.)?(\d+)$")
_SINGLE = re.compile(r"^(\d+\.\d+)[a-z]?$")


def expand_ids(idpart: str) -> list[str]:
    """'3.7 + 11.5' -> ['3.7','11.5'];  '17.1-17.11' -> ['17.1', ..., '17.11']."""
    out: list[str] = []
    for part in re.split(r"\s*[+,]\s*", idpart.replace("§", "").strip()):
        part = part.strip()
        m = _RANGE.match(part)
        if m:
            maj, a, b = m.group(1), int(m.group(2)), int(m.group(4))
            out += [f"{maj}.{i}" for i in range(a, b + 1)]
            continue
        m2 = _SINGLE.match(part)
        if m2:
            out.append(m2.group(1))
    return out


def norm_key(text: str) -> str:
    text = text.replace("§", "").lower()
    text = re.sub(r"[^a-z0-9.+\- ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


_TARGET = re.compile(
    r"`((?:locus-os/|locus/|sidecar/|src/|locus-extension/|locus_cli/|vault/|\.pi/)[A-Za-z0-9_.\-/*{}]*)`"
)
_HEAD = re.compile(r"^## Feature (.+?)\s*$")
_ANY_HEAD = re.compile(r"^#{1,2} ")


def parse_spec(path: Path) -> dict:
    """Parse '## Feature §X: Title' sections. Returns headings with a content hash each."""
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    heads: list[dict] = []
    for i, line in enumerate(lines):
        m = _HEAD.match(line)
        if not m:
            continue
        body = m.group(1)
        if ":" in body:
            idpart, title = body.split(":", 1)
        else:
            idpart, title = body, ""
        idpart, title = idpart.strip(), title.strip()
        heads.append({"line": i + 1, "idpart": idpart, "title": title,
                      "ids": expand_ids(idpart), "key": norm_key(f"{idpart}: {title}")})
    # section extents + hashes
    for n, h in enumerate(heads):
        start = h["line"]  # 1-based line of the heading; body starts next line
        end = len(lines)
        for j in range(start, len(lines)):
            if _ANY_HEAD.match(lines[j]):
                end = j
                break
        section = "\n".join(lines[start - 1:end]).rstrip()
        h["end_line"] = end
        h["sha"] = sha256_text(section)[:16]
        verdict = re.search(r"\*\*Verdict\*\*:\s*([^\n·|*]+)", section)
        h["verdict"] = verdict.group(1).strip(" \t•") if verdict else None
        h["targets"] = sorted(set(_TARGET.findall(section)))[:12]
    return {"text": text, "lines": lines, "headings": heads}


def display_heading(h: dict) -> str:
    return f"§{h['idpart'].lstrip('§')}: {h['title']}".strip()


def translate_target(path: str, stale_rules: list[dict]) -> str:
    """Spec path -> canonical repo path (e.g. locus/core/x.ts -> locus-extension/src/x.ts)."""
    out = path
    for r in stale_rules:
        out = re.sub(r["pattern"], r["canonical"], out, count=1)
    if out.startswith("locus-os/"):
        out = out[len("locus-os/"):]
    return out


# --------------------------------------------------------------------- findings
# Every finding id check.py can emit besides the per-rule ids that live in guard.toml
# ([[forbidden_text]].id and [[stale_paths]].id). features.yaml may only cite ids from this set
# (a typo would otherwise "pass" because no finding of that id ever exists). A test keeps this list
# in sync with check.py.
GUARD_CHECK_IDS = {
    "forbidden-path", "reparse-point", "layout-required", "layout-baseline", "layout-top-level",
    "vault-layout", "vault-name", "upstream-clean", "must-define", "pi-bridge-flags", "python-syntax",
    "agents-md", "claude-md", "gemini-md", "segment-size", "secrets", "gitignore", "spec-lint",
    "tracker", "tracker-xlsx", "human-review", "git", "import-smoke", "ts-typecheck",
}


class Finding:
    __slots__ = ("severity", "check", "message", "where")

    def __init__(self, severity: str, check: str, message: str, where: str = ""):
        self.severity, self.check, self.message, self.where = severity, check, message, where

    def as_dict(self) -> dict:
        return {"severity": self.severity, "check": self.check, "message": self.message, "where": self.where}

    def __str__(self) -> str:
        loc = f"  ({self.where})" if self.where else ""
        return f"[{self.severity}] {self.check}: {self.message}{loc}"


def json_dump(obj, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False, sort_keys=False)
        fh.write("\n")


# ------------------------------------------------------------- workbook tamper
GRID_COLS = 16  # columns A..P of the "Feature Tracker" sheet are the hashed grid


def _norm_cell(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def grid_hash(ws) -> str:
    """Hash of the visible data grid (rows 2.., columns A..P). Written by export_xlsx, re-checked by the guard."""
    rows = []
    for r in ws.iter_rows(min_row=2, max_col=GRID_COLS, values_only=True):
        if all(v is None for v in r):
            continue
        rows.append([_norm_cell(v) for v in r])
    return sha256_text(json.dumps(rows, ensure_ascii=False, separators=(",", ":")))
