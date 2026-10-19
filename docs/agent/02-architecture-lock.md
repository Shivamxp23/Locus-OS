# 02 - Architecture lock (one layout, one bridge, one name for everything)

## Processes
```
Pi (Node, packages/coding-agent)  <- loads ->  Locus extension (locus-extension/): tools, hooks, slash commands
   ^  tools call HTTP http://127.0.0.1:8420                  |
   |                                                         v
Sidecar (Python package sidecar/, FastAPI :8420) -- starts Pi turns through sidecar/pi_bridge.py (cron, Telegram, conductor)
   |-- neo4j :7687 (bolt)   postgres+pgvector :5432   couchdb :5984 (LiveSync)   redis :6379 (spec 30.9; errata D-7)
```
The sidecar is started by the Node side on boot (health ping `/health`, spawn after 30 s of silence), or by systemd/Docker on a VM.

## Folders (guard.toml enforces this)
| Folder | Owner | Rule |
|---|---|---|
| `packages/` | upstream Pi | byte-identical to the pinned baseline (`tools/guard/pin_upstream.py`). Never edit. |
| `locus-extension/` | Locus TS | all Pi-side features. Spec paths `locus/core/..`, `locus-os/src/core/..`, `locus/extensions/..`, `src/extensions/..` mean `locus-extension/src/..` |
| `sidecar/` | Locus Python | the ONLY Python package for runtime logic. `sidecar/__init__.py` holds `__version__` and nothing else |
| `locus_cli/` | Locus Python | CLI, setup wizard, doctor |
| `vault/` | content | 8 canonical folders (06-vault-memory-audit.md) |
| `tools/ tracker/ tests/guard/ docs/agent/ .githooks/` | human | guard + tracker + rules |
| `docker-compose.yml`, `install.*`, `locus.*` | Locus infra | allowed top-level files (adopted in guard.toml) |
Anything else at the top level fails the guard. Spec says `locus-os/sidecar/x.py`: the leading `locus-os/` is the repo root, so `sidecar/x.py`.

## Forbidden, with the reason it exists
- `core/` (any form). It was an NTFS junction onto `sidecar/`: edits through one path rewrote the other, and `pi_bridge.py` was
  overwritten and had to be restored from a chat transcript.
- Runtime aliases such as `sys.modules.setdefault("core", ...)`. A module imported as `core.x` and as `sidecar.x` becomes TWO
  module objects with separate globals; singletons duplicate, patches miss, and bugs hide. A crash on a stale import is the fix.
- Re-export files (`from sidecar.pi_bridge import *` in another folder). The guard fails if `sidecar/pi_bridge.py` stops DEFINING
  `run_pi_turn` and `get_node_executable`.
- `locus/`, `locus-os/`, `src/` at the top level; second copies of anything; `locus-os-legacy` inside the repo (keep it outside).

## The Pi bridge contract (sidecar -> Pi)
- File `sidecar/pi_bridge.py` defines `get_node_executable()` and `run_pi_turn(...)`. Every runtime Pi launch goes through it.
- Command: `[node, "packages/coding-agent/dist/cli.js", "--approve", "--no-context-files", "-p", <prompt>, ...]`, `stdin=DEVNULL`,
  no `shell=True`, a timeout, stdout and stderr captured, session id per caller (cron: `cron_<job_id>`).
- `--approve` makes Pi trust project-local files (this is how `.pi/extensions` loads headless). Use it only with cwd = this repo.
  Never pass it with cwd inside a repo you did not write (research or coding delegation into other projects).
- `--no-context-files` (`-nc`) stops Pi from loading AGENTS.md/CLAUDE.md, which would otherwise inject THESE developer rules
  into every cron, Telegram, and conductor turn. The cwd stays the repo root for now; moving the runtime cwd is a separate decision.
- Extension -> sidecar calls use the sidecar HTTP API on :8420 only. No imports across the language boundary.

## Imports and naming
- Python: absolute imports `from sidecar.<module> import ...`. No `core`, no `locus_os`, no relative hops above the package.
- A new Python module goes in the matching `sidecar/<area>/` folder named in the spec's file table. A new TS tool goes in
  `locus-extension/src/tools/` and is registered in `locus-extension/src/tools/index.ts`.
- Renaming or moving: `git mv`, then fix every importer in the same commit, then run the guard. No leftovers, no aliases.
- Python 3.11+ syntax only (no backslashes inside f-string braces). Windows, Linux, and macOS must all work: use `pathlib`, never
  hard-code drive letters or `\\`.

## `.locus` versus the repo
Code and built-in tools live in the repo. Secrets, user config, databases, caches, logs live in `~/.locus` (`.env`,
`config.yaml`, `store.db`, `memory/`, `logs/`). Each spec feature states which side its files fall on. Never write user data
into the repo and never read a secret from a repo file.

## Ports
sidecar 8420 · neo4j 7687 · postgres 5432 · redis 6379 · couchdb 5984: ALL bound to 127.0.0.1; CouchDB is reached remotely only
over HTTPS or a private network (10-security.md S-2). A new port needs the owner's approval.
