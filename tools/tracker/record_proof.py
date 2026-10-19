#!/usr/bin/env python3
"""Record end-to-end proof for a feature (the only way to reach L5, together with a human signoff).

    python tools/tracker/record_proof.py F-0061 -- python scripts/e2e_cron.py        # automated proof
    python tools/tracker/record_proof.py F-0061 --note "watched the 09:00 briefing arrive in Telegram" --artifact evidence/f0061-telegram.png

The proof stores the command, exit code, output hash, commit, and a hash of every evidence file.
If any evidence file changes afterwards the proof becomes STALE and the feature drops back to L4.
A proof alone is not enough: the human must add the feature to tracker/signoff.yaml.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import locus_common as C  # noqa: E402


def main() -> int:
    C.utf8_stdio()
    argv = sys.argv[1:]
    cmd: list[str] = []
    if "--" in argv:
        i = argv.index("--")
        argv, cmd = argv[:i], argv[i + 1:]
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("fid")
    ap.add_argument("--note")
    ap.add_argument("--artifact", help="repo-relative path of a screenshot/log that shows the result")
    ap.add_argument("--root")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[2]
    feats = C.load_yaml(root / "tracker" / "features.yaml")["features"]
    f = next((x for x in feats if x["id"] == args.fid), None)
    if not f:
        print(f"No feature {args.fid}")
        return 2
    files = [str(x) for x in (f.get("evidence") or {}).get("files") or []]
    if not files:
        print("Feature declares no evidence files; nothing to bind the proof to.")
        return 2
    proof = {"id": args.fid, "commit": C.git_head(root), "dirty": C.git_dirty(root), "ran_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
             "files_sha256": C.sha256_paths(root, files)}
    if cmd:
        t0 = time.time()
        p = subprocess.run(cmd, cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace")
        out = (p.stdout or "") + (p.stderr or "")
        proof.update(cmd=" ".join(cmd), exit=p.returncode, seconds=round(time.time() - t0, 1), output_sha256=C.sha256_text(out), output_tail=out[-3000:])
        print(out[-1500:])
    else:
        if not (args.note and args.artifact):
            print("Manual proof needs both --note and --artifact (a screenshot or log inside the repo).")
            return 2
        art = root / args.artifact
        if not art.is_file():
            print(f"Artifact not found: {args.artifact}")
            return 2
        proof.update(cmd=None, manual=True, exit=0, note=args.note, artifact=args.artifact, artifact_sha256=C.sha256_file(art))
    C.json_dump(proof, root / "tracker" / "proof" / f"{args.fid}.json")
    print(f"recorded tracker/proof/{args.fid}.json (exit={proof['exit']}).")
    if proof["exit"] == 0:
        pid = proof["files_sha256"][:12]
        print("\nTHE HUMAN (not an agent) now looks at the result and, if it is truly right, adds this line to tracker/signoff.yaml:")
        print(f'{args.fid}: {{by: Shivam, date: {time.strftime("%Y-%m-%d")}, proof: "{pid}", note: "what you personally saw"}}')
        print("The signoff only counts for THIS proof. If the evidence files change and the proof is re-recorded, you must sign again.")
    return 0 if proof["exit"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
