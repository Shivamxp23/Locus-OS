# P0 Audit Report — Gemini

## Summary
No real secrets were found in the repository; one unit-test fixture key in .keysndocs was redacted.
Upstream Pi Agent under packages/ is byte-identical to pristine reference (0 differences).
Repository working tree is clean on branch guardrails/install; git hooks remain disabled.
The guard check reports 7 FAILs: missing runtime folders, missing pi_bridge, and CouchDB default password.
Deterministic tracker verification shows 125 features with a verified average completion of 9.6%.
72 overclaims were identified against the legacy spreadsheet claim of 71.4% average completion.
113 features have NO_EVIDENCE in the repository because implementation files were not migrated.
Earlier sessions created bespoke agent loops and Git vault sync in legacy, violating core laws.
Docker Compose in the legacy tree exposes database ports to 0.0.0.0 with hardcoded default passwords.
Sprint 1 backlog stories US-01 through US-03 correctly target these architectural and security defects.

## Guard output
```text
LOCUS GUARD  mode=full  root=C:\Users\soni8\Desktop\everything\University 2.0\Project(s)\5_Locus\locus-os
[FAIL] layout-required: Required folder `sidecar` is missing.  (sidecar)
[FAIL] layout-required: Required folder `locus-extension` is missing.  (locus-extension)
[FAIL] layout-required: Required folder `locus_cli` is missing.  (locus_cli)
[FAIL] layout-required: Required file `sidecar/__init__.py` is missing.  (sidecar/__init__.py)
[FAIL] layout-required: Required file `docker-compose.yml` is missing.  (docker-compose.yml)
[FAIL] must-define: `sidecar/pi_bridge.py` is missing.  (sidecar/pi_bridge.py)
[FAIL] secrets: Looks like a couchdb-default-password credential. Rotate it NOW if it was ever pushed or pasted anywhere, then remove it.  (.keysndocs/Documentation/Chat Reports/6_October/2nd October/Locus_CouchDB_LiveSync_and_Architecture_Alignment_Session.md:158)
[WARN] git: No git remote configured: the repo exists on one disk only. Add a private remote and push.
[WARN] git: Hooks not active. Run: git config core.hooksPath .githooks
[WARN] layout-baseline: Top-level baseline not adopted yet. Review the folder listing, then run: python tools/guard/check.py --adopt-top-level   (unknown top-level entries: .keysndocs, RUNBOOK.md)
[WARN] segment-size: docs/agent/11-agile-workflow.md is 8806 bytes (limit 7500). Segments must stay concentrated: split it.  (docs/agent/11-agile-workflow.md)
[WARN] spec-lint: 26 KNOWN spec defects still open (docs/agent/09-spec-errata.md). Agents must stop and ask when a task touches one.
[WARN] stale-locus-core: 1 reference(s) to a non-canonical path; canonical is `locus-extension/src/`.  (AGENTS.md:13)
[WARN] stale-locus-core: 40 reference(s) to a non-canonical path; canonical is `locus-extension/src/`.  (.keysndocs/Documentation/Implementation Plans/LOCUS_FEATURE_LOGIC_DECOMPOSITION.md:415)
[WARN] stale-locus-extensions: 3 reference(s) to a non-canonical path; canonical is `locus-extension/src/`.  (.keysndocs/Documentation/Implementation Plans/LOCUS_FEATURE_LOGIC_DECOMPOSITION.md:544)
[WARN] stale-locus-os-src-core: 1 reference(s) to a non-canonical path; canonical is `locus-extension/src/`.  (AGENTS.md:13)
[WARN] stale-locus-os-src-core: 11 reference(s) to a non-canonical path; canonical is `locus-extension/src/`.  (.keysndocs/Documentation/Implementation Plans/LOCUS_FEATURE_LOGIC_DECOMPOSITION.md:1179)
[WARN] stale-src-extensions: 1 reference(s) to a non-canonical path; canonical is `locus-extension/src/`.  (AGENTS.md:14)
[WARN] stale-src-extensions: 1 reference(s) to a non-canonical path; canonical is `locus-extension/src/`.  (.keysndocs/Documentation/Implementation Plans/LOCUS_FEATURE_LOGIC_DECOMPOSITION.md:6667)

FAIL: 7 FAIL, 12 WARN, 0 INFO  (2.3s)
```

```text
features 125 | verified avg 9.6% | old claimed avg 71.4% | integrated+ 12 | proven 0 | overclaims 72 | no-evidence 113
by level: {'INHERITED_OK': 12, 'NO_EVIDENCE': 113}
guard: FAIL {'FAIL': 7, 'WARN': 12, 'INFO': 0}
```

## Verdict table

| Path | Verdict | Evidence |
|---|---|---|
| `.githooks/` | KEEP | Mechanical guardrail enforcement; AGENTS.md law 2 |
| `.github/` | KEEP | CI workflow running check.py and backlog.py; AGENTS.md law 2 |
| `.keysndocs/` | KEEP | Authoritative specification decomposition and documentation; guard.toml spec_path |
| `docs/agent/` | KEEP | 11 focused architectural guidelines; AGENTS.md law 2 |
| `packages/` | KEEP | Pristine upstream Pi Agent; verified byte-identical by tools/guard/pin_upstream.py |
| `tests/guard/` | KEEP | 238 unit tests verifying guard, tracker, and autopilot; AGENTS.md law 2 |
| `tools/guard/` | KEEP | Core enforcement engine (check.py, guard.toml); AGENTS.md law 2 |
| `tools/tracker/` | KEEP | Deterministic evidence engine and backlog board; AGENTS.md law 2 |
| `tracker/` | KEEP | Ground truth features.yaml, backlog.yaml, sprints.jsonl; AGENTS.md law 2 |
| `sidecar/` | FIX | Required directory missing from locus-os; guard layout-required |
| `locus-extension/` | FIX | Required directory missing from locus-os; guard layout-required |
| `locus_cli/` | FIX | Required directory missing from locus-os; guard layout-required |
| `vault/` | FIX | Required 8 canonical directories missing; 06-vault-memory-audit.md |
| `locus-os-legacy/core/agent.py` | DISCARD | Bespoke agent loop bypassing Pi; violates AGENTS.md law 1 and 01-vision.md |
| `locus-os-legacy/gateway/agent.py` | DISCARD | Second bespoke agent loop; violates AGENTS.md law 1 and 01-vision.md |
| `locus-os-legacy/core/vault/git_sync.py` | DISCARD | Git sync of vault; explicitly forbidden by 01-vision.md |
| `locus-os-legacy/core/vault/obsidian_sync.py` | DISCARD | Local file sync; forbidden by 01-vision.md (LiveSync CouchDB only) |
| `locus-os-legacy/setup_categories/` | DISCARD | Root duplicate of locus_cli/setup_categories; violates AGENTS.md law 2 |
| `locus-os-legacy/core/life_os_persistent.py` | DISCARD | Overgrown duplicate of life_os.py (41 KB vs 26 KB); consolidate to single module |
| `locus-os-legacy/core/conductor.py` | FIX | 11-step master conductor; migrate to sidecar/conductor.py, route turns to pi_bridge |
| `locus-os-legacy/core/cause_chain.py` | FIX | 9-step root cause chain pipeline; migrate to sidecar/cause_chain.py per spec §30.2 |
| `locus-os-legacy/core/neo4j_memory.py` | FIX | Neo4j Agent Memory integration; migrate to sidecar/neo4j_memory.py per spec §4.1 |
| `locus-os-legacy/core/security/` | FIX | Redaction, sanitization, injection filter; migrate to sidecar/security/ per spec §13 |
| `locus-os-legacy/locus_cli/main.py` | FIX | Main CLI router; migrate to locus_cli/main.py and strip stale core imports |
| `locus-os-legacy/locus_cli/setup.py` | FIX | Setup wizard; migrate to locus_cli/setup.py with one-time pairing per 10-security.md S-1 |
| `locus-os-legacy/docker-compose.yml` | FIX | Missing CouchDB, unhardened ports, default credentials; rewrite per 10-security.md S-2 |
| `locus-os-legacy/scripts/init_database.py` | FIX | PostgreSQL schema initialization; migrate to scripts/init_database.py |
| `locus-os-legacy/scripts/*.mjs, *.ts` | DISCARD | Upstream Pi scripts duplicated at root; belongs in packages/ |
| `locus-os-legacy/install.ps1` | FIX | PowerShell installer; update to canonical layout without NTFS junctions |
| `locus-os-legacy/install.sh` | FIX | Shell installer; update to canonical layout without core/ references |
| `locus-os-legacy/install.bat` | FIX | Windows batch wrapper; retain as clean entrypoint |
| `locus-os-legacy/locus.bat` / `locus.cmd` | FIX | Shell launchers; update to invoke canonical sidecar/locus-extension runtime |

## Discard table

| Path | Reason | Replaced by | Imported by (grep proof) |
|---|---|---|---|
| `core/agent.py` | Bespoke agent loop bypassing Pi; violates AGENTS.md law 1 | Pi Agent loop via `sidecar/pi_bridge.py` | `grep 'from core.agent': core/cause_chain.py, core/locus_tools.py, core/title_generator.py, gateway/agent.py, core/context/compactor.py, core/delegation/subagent.py, core/heartbeat/proactive_chain.py` |
| `gateway/agent.py` | Second bespoke agent loop; violates AGENTS.md law 1 | Pi Agent loop via `sidecar/pi_bridge.py` | `grep 'gateway.agent': core/conductor.py, core/cron_runner.py, gateway/slash_commands.py, core/deployment/systemd_generator.py` |
| `core/vault/git_sync.py` | Git vault sync forbidden; 01-vision.md mandates CouchDB LiveSync only | CouchDB LiveSync bridge (`sidecar/vault/livesync_bridge.py`) | `grep 'git_sync': core/maintenance.py, core/scheduler_wiring.py, core/session_export.py, core/diagnostics/db_health.py, core/heartbeat/vault_synthesis.py` |
| `core/vault/obsidian_sync.py` | Non-CouchDB vault sync; 01-vision.md mandates CouchDB LiveSync only | CouchDB LiveSync bridge | `grep 'obsidian_sync': core/maintenance.py, core/life_os_persistent.py` |
| `setup_categories/` | Root-level folder violating AGENTS.md law 2; duplicate of `locus_cli/setup_categories` | `locus_cli/setup_categories/` | `grep 'setup_categories.handlers': gateway/bot.py, gateway/slash_commands.py` |
| `core/life_os_persistent.py` | Duplicate implementation of `core/life_os.py` | Canonical `sidecar/life_os.py` | `grep 'life_os_persistent': core/maintenance.py, core/scheduler_wiring.py, gateway/checkin_flow.py, core/mcp/server.py` |
| `scripts/browser-smoke-entry.ts` (+ 19 other Pi scripts) | Duplicated from `deps/pi/scripts/`; violates AGENTS.md law 2 | Upstream `packages/` internal build scripts | None in Locus Python/TS code |

## Duplicates
1. **Agent Loops**: `core/agent.py` and `gateway/agent.py` both implement ad-hoc execution loops instead of delegating to Pi.
2. **Setup Categories**: `setup_categories/` at repository root duplicates `locus_cli/setup_categories/`.
3. **LifeOS State**: `core/life_os.py` (26 KB) and `core/life_os_persistent.py` (41 KB) both implement DCS/TWS state tracking and task scoring with divergent logic.
4. **Memory Implementations**: `core/memory.py`, `core/neo4j_memory.py`, and `core/memory/store.py` duplicate graph storage access patterns.
5. **Security Redaction**: `core/security.py` duplicates functionality in `core/security/redact.py` and `core/security/sanitizer.py`.
6. **Pi Launch**: Multiple shell scripts (`locus.bat`, `locus.cmd`, `install.ps1`) attempt ad-hoc Pi invocation rather than routing through a unified `pi_bridge.py`.

## Unbacked claims
Top 30 features from `tracker/legacy/legacy_claims.json` claiming high completion but having NO code or tests in the clean repository:

1. `F-0002` | Claimed: 100.0% | System Prompt Construction | Searched: `locus-extension/src/hooks/index.ts`
2. `F-0003` | Claimed: 100.0% | Tool System (13 Canonical Tools) | Searched: `locus-extension/src/tools/index.ts`
3. `F-0005` | Claimed: 100.0% | Extension Lifecycle | Searched: `locus-extension/index.ts`
4. `F-0012` | Claimed: 100.0% | Onboarding Flow | Searched: `locus_cli/setup.py`
5. `F-0060` | Claimed: 100.0% | Obsidian Self-Hosted LiveSync & CouchDB | Searched: `sidecar/vault/livesync_bridge.py`, `docker-compose.yml`, `data/couchdb/local.ini`
6. `F-0082` | Claimed: 100.0% | Install Script (ALL platforms) | Searched: `install.ps1`, `install.sh`, `install.bat`, `locus.bat`, `locus.cmd`
7. `F-0083` | Claimed: 100.0% | Telegram Setup via /setup command | Searched: no evidence files declared
8. `F-0084` | Claimed: 100.0% | core/ vs sidecar/ Deduplication | Searched: `sidecar/`, `sidecar/__init__.py`
9. `F-0085` | Claimed: 100.0% | VM Backend Setup | Searched: `HEADLESS_VM_AND_CRON_SETUP_GUIDE.md`, `install.sh`, `docker-compose.yml`
10. `F-0029` | Claimed: 90.0% | Coding Context | Searched: no evidence files declared
11. `F-0046` | Claimed: 90.0% | Telegram Gateway | Searched: `sidecar/gateway/`, `gateway/`
12. `F-0055` | Claimed: 90.0% | DCS / TWS / Factions | Searched: `sidecar/life_os.py`
13. `F-0066` | Claimed: 90.0% | Health Checks | Searched: `locus_cli/main.py`
14. `F-0078` | Claimed: 90.0% | Master Conductor | Searched: `sidecar/conductor.py`
15. `F-0004` | Claimed: 85.0% | Model Management & Escalation | Searched: `sidecar/life_os.py`
16. `F-0031` | Claimed: 85.0% | CLI / Doctor Diagnostics | Searched: `locus_cli/main.py`
17. `F-0056` | Claimed: 85.0% | Operating Modes / Scheduler | Searched: `sidecar/life_os.py`, `sidecar/scheduler/`
18. `F-0057` | Claimed: 85.0% | Goal Tracker (3-Layer Stack) | Searched: `sidecar/life_os.py`
19. `F-0059` | Claimed: 85.0% | PageIndex Retrieval | Searched: `sidecar/search/pageindex.py`
20. `F-0064` | Claimed: 85.0% | Dual Interface / Check-ins | Searched: `sidecar/gateway/`, `locus-extension/`
21. `F-0007` | Claimed: 80.0% | Post-Turn Review | Searched: `sidecar/learning/reflector.py`
22. `F-0009` | Claimed: 80.0% | Rate Limit Tracking | Searched: `sidecar/rate_limiter.py`
23. `F-0021` | Claimed: 80.0% | Neo4j Agent Memory (POLE+O) | Searched: `sidecar/neo4j_memory.py`
24. `F-0027` | Claimed: 80.0% | Session Management | Searched: `sidecar/memory.py`, `sidecar/session_export.py`
25. `F-0037` | Claimed: 80.0% | Injection Filter | Searched: `sidecar/security/injection_filter.py`
26. `F-0010` | Claimed: 75.0% | Usage/Cost Tracking | Searched: `sidecar/cost_tracker.py`
27. `F-0011` | Claimed: 75.0% | Title Generation | Searched: `sidecar/title_generator.py`
28. `F-0041` | Claimed: 75.0% | Data Redaction | Searched: `sidecar/security/redact.py`
29. `F-0042` | Claimed: 75.0% | Think Token Scrubbing | Searched: `sidecar/security/think_scrubber.py`
30. `F-0043` | Claimed: 75.0% | Message Sanitization | Searched: `sidecar/security/sanitizer.py`

## Security
No real active secrets or credentials were found in the tracked repository.

1. **S-0 (Secrets Storage)**:
   - Historical test artifact `.keysndocs/.../Locus_Architecture_Audit_and_Reset_Session.md` line 3106 contained a dummy GitHub token matching credential regex; redacted during initialization.
   - Known baseline finding: CouchDB default password referenced in `.keysndocs/.../Locus_CouchDB_LiveSync_and_Architecture_Alignment_Session.md` line 158.
2. **S-1 (Telegram First-Touch Pairing Vulnerability)**:
   - In `locus-os-legacy/gateway/bot.py` lines 42-58: `_is_allowed` designates the first user to message the bot as the administrator/owner, allowing unauthorized takeover if the username is discovered.
   - Must be replaced by one-time setup pairing codes expiring in 10 minutes (story `US-04`).
3. **S-2 (CouchDB and Database Port Exposure)**:
   - In `locus-os-legacy/docker-compose.yml` lines 10, 48, 60, 82: ports `8420:8420`, `7474:7474`, `7687:7687`, `5432:5432`, `6379:6379` bind to `0.0.0.0` rather than `127.0.0.1`.
   - Default passwords (`locuspassword`) are present in compose file lines 15, 17, 51, 64 without strict validation from `.env` (addressed in story `US-03`).
4. **S-3 (Pi Invocation Flags)**:
   - Legacy scripts invoked Pi or Node directly without enforcing mandatory runtime flags `--approve --no-context-files`, causing repository-level developer rules to bleed into user runtime sessions (addressed in story `US-02`).

## Questions for the owner
1. **Decision D-10 (Config location)**: Should `~/.locus/config.yaml` be locked as the definitive single source of truth for the `locus.*` configuration tree across both Python (sidecar) and TypeScript (locus-extension), with `~/.locus/.env` reserved exclusively for secrets? (Recommended: Yes).
2. **Legacy Code Migration in US-01**: In `locus-os-legacy`, candidate files for `sidecar/` exist in `core/` (e.g. `conductor.py`, `cause_chain.py`, `neo4j_memory.py`). Do you approve migrating these modular logic files into `sidecar/` while completely purging the bespoke agent loop (`core/agent.py`, `gateway/agent.py`) and Git sync (`core/vault/git_sync.py`)?
3. **Decision D-1 (TWS Task Priority Formula)**: The spec has conflicting formulas between §25.4 (`TWS = P*0.4 + U*0.4 + D*0.2` + lag bonus) and §25.12 (`TWS = D*0.35 + L*0.25 + U*0.20 + C*0.20` + deferral bonus). Do you confirm adopting Appendix C / §25.4 as recommended?

## Not checked
- **Live VM and Network Connectivity**: No remote VM, Tailscale, or public domain endpoints were probed or contacted.
- **Telegram Bot Webhook/Polling**: No live messages were sent to Telegram API endpoints; token validation was static.
- **Database Engine Connectivity**: No live connections to running Neo4j, PostgreSQL, or CouchDB daemon instances were initiated; checks were conducted via static syntax, schema, and compose inspection.

Files opened: 31
