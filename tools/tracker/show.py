#!/usr/bin/env python3
"""Print ONE feature (instead of reading the 4000-line manifest or the 8000-line spec).

    python tools/tracker/show.py F-0061            # the feature block + its computed status
    python tools/tracker/show.py F-0061 --spec     # + the verbatim spec section(s) for it
    python tools/tracker/show.py --find livesync   # search titles / spec refs
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import locus_common as C  # noqa: E402


def main() -> int:
    C.utf8_stdio()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("fid", nargs="?")
    ap.add_argument("--spec", action="store_true", help="also print the verbatim spec section(s)")
    ap.add_argument("--find")
    ap.add_argument("--root")
    args = ap.parse_args()
    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[2]
    cfg = C.load_toml(root / "tools" / "guard" / "guard.toml")
    feats = C.load_yaml(root / "tracker" / "features.yaml")["features"]

    if args.find:
        q = args.find.lower()
        for f in feats:
            hay = (f["title"] + " " + " ".join(f.get("spec_refs") or [])).lower()
            if q in hay:
                print(f"{f['id']}  {f['title'][:60]}   {', '.join(f.get('spec_refs') or [])[:60]}")
        return 0
    if not args.fid:
        ap.print_help()
        return 2
    f = next((x for x in feats if x["id"] == args.fid), None)
    if not f:
        print(f"No feature {args.fid}")
        return 2
    print(C.yaml.safe_dump(f, sort_keys=False, allow_unicode=True, width=110))
    if f.get("spec_targets"):
        print("--- WHERE THE SPEC SAYS THE CODE LIVES -> WHERE IT MUST LIVE (canonical layout wins) ---")
        for t in f["spec_targets"]:
            print(f"  {t}  ->  {C.translate_target(t, cfg.get('stale_paths', []))}")
    sp = root / "tracker" / "status.json"
    if sp.is_file():
        st = json.loads(sp.read_text(encoding="utf-8"))["features"].get(args.fid)
        if st:
            print("--- COMPUTED STATUS (not an opinion) ---")
            print(f"level: {st['label']} ({st['pct']}%)   old claim: {st['claimed_pct']}%   flags: {st['flags']}")
            for r in st["reasons"]:
                print("  why not higher:", r)
            print("  next:", st["next"])
    if args.spec:
        spec_path = root / cfg["repo"]["spec_path"]
        spec = C.parse_spec(spec_path)
        want = {C.norm_key(r) for r in f.get("spec_refs") or []}
        for h in spec["headings"]:
            if h["key"] in want:
                print(f"\n=== SPEC {C.display_heading(h)} (lines {h['line']}-{h['end_line']}) ===")
                print("\n".join(spec["lines"][h["line"] - 1:h["end_line"]]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
