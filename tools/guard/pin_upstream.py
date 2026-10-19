#!/usr/bin/env python3
"""Pin the last clean upstream Pi commit, so any edit to packages/ is detectable forever.

    python tools/guard/pin_upstream.py                 # auto-detect baseline from git history
    python tools/guard/pin_upstream.py --baseline SHA  # you name the last clean Pi commit
    python tools/guard/pin_upstream.py --compare-dir ../pi-fresh   # no history? diff against a fresh upstream checkout

Auto-detect rule: the baseline is the PARENT of the first commit that added any Locus-owned
folder (sidecar/, locus-extension/, locus_cli/). Everything before that commit is Pi.
After pinning, the guard fails whenever packages/ differs from that baseline.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import locus_common as C  # noqa: E402

LOCUS_OWNED = ["sidecar", "locus-extension", "locus_cli"]
SKIP = {"node_modules", "dist", "build", ".turbo", "coverage", ".git", "__pycache__"}


def detect_baseline(root: Path) -> tuple[str | None, str]:
    rc, out = C.git(root, "log", "--diff-filter=A", "--reverse", "--format=%H", "--", *LOCUS_OWNED)
    commits = out.split() if rc == 0 else []
    if not commits:
        return None, "No commit adds sidecar/, locus-extension/ or locus_cli/ yet."
    first = commits[0]
    rc, parent = C.git(root, "rev-parse", f"{first}^")
    if rc != 0:
        return first, ("ROOT: the very first commit already contains Locus folders. Pi's pristine state is not in history, "
                       "so 'clean' cannot be proven from git alone. Use --compare-dir with a fresh upstream checkout.")
    return parent.strip(), ""


def compare_dir(root: Path, ref: Path, paths: list[str]) -> int:
    diffs = []
    for pth in paths:
        a, b = root / pth, ref / pth
        if not b.is_dir():
            print(f"Reference has no {pth}/ folder: {b}")
            return 2
        files_a = {C.rel(a, p): p for p in C.iter_files(a, SKIP)}
        files_b = {C.rel(b, p): p for p in C.iter_files(b, SKIP)}
        for r in sorted(set(files_a) | set(files_b)):
            if r not in files_a:
                diffs.append(f"MISSING in yours:   {pth}/{r}")
            elif r not in files_b:
                diffs.append(f"EXTRA in yours:     {pth}/{r}")
            elif C.sha256_file(files_a[r]) != C.sha256_file(files_b[r]):
                diffs.append(f"MODIFIED:           {pth}/{r}")
    for d in diffs[:200]:
        print(d)
    print(f"\n{len(diffs)} difference(s) against the reference checkout.")
    print("Reference must be the SAME upstream version you started from; if every file differs, you picked the wrong version.")
    return 1 if diffs else 0


def main() -> int:
    C.utf8_stdio()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--baseline", help="commit sha of the last clean upstream state")
    ap.add_argument("--paths", nargs="*", default=["packages"])
    ap.add_argument("--compare-dir", help="fresh upstream checkout to diff against (no git needed)")
    ap.add_argument("--root", help="repo root")
    args = ap.parse_args()
    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[2]

    if args.compare_dir:
        return compare_dir(root, Path(args.compare_dir).resolve(), args.paths)

    if not (root / ".git").exists():
        print("Not a git repo.")
        return 2
    base, warn = (args.baseline, "") if args.baseline else detect_baseline(root)
    if not base:
        print(warn)
        return 2
    rc, _ = C.git(root, "cat-file", "-e", f"{base}^{{commit}}")
    if rc != 0:
        print(f"{base} is not a commit in this repo.")
        return 2
    base = C.git(root, "rev-parse", base)[1].strip()
    rc, subj = C.git(root, "log", "-1", "--format=%h %ad %s", "--date=short", base)
    print(f"Baseline commit : {subj.strip()}")
    if warn:
        print(f"WARNING         : {warn}")

    rc, diff = C.git(root, "diff", "--name-only", base, "--", *args.paths)
    rc2, unt = C.git(root, "ls-files", "--others", "--exclude-standard", "--", *args.paths)
    changed = [x for x in (diff.splitlines() + unt.splitlines()) if x.strip()]
    print(f"Files in {args.paths} that ALREADY differ from the baseline: {len(changed)}")
    for c in changed[:40]:
        print("   ", c)
    if changed:
        print("These are upstream edits. Revert them (git checkout <baseline> -- <file>) unless you can justify each one;")
        print("justified ones go into [upstream].allow_modified in guard.toml (human decision).")

    lock = {"baseline_commit": base, "paths": args.paths, "pinned_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "pinned_on_head": C.git_head(root), "warning": warn or None}
    out = root / "tools" / "guard" / "upstream.lock.json"
    C.json_dump(lock, out)
    print(f"\nWrote {C.rel(root, out)}. Commit it (needs LOCUS_ALLOW_GUARD_EDIT=1).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
