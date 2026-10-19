# 09 - Spec errata and decisions (where LOCUS_FEATURE_LOGIC_DECOMPOSITION.md is wrong, silent, or in conflict)

Status words. **DECIDED** binds everyone. **DEFAULT**: build on it and say so in the handoff; the owner may change it. **OPEN**: an
agent that touches it STOPS and asks; prompt P3 settles OPEN rows with the owner, one question at a time. Only the owner changes a status
(edit this file, commit with `LOCUS_ALLOW_GUARD_EDIT=1`). Line numbers refer to the spec as attached on 2026-10-05; section E reproduces every claim.

## A. Index
| ID | Status | Topic | Blocks |
|---|---|---|---|
| D-1 | DECIDED | Which task-priority formula (TWS) is real | F-0055, F-0056, every task-scoring feature |
| D-2 | DECIDED | Vault has 8 canonical folders | - |
| D-3 | DECIDED | What "scale" means for per-task priority | with D-1 |
| D-4 | DECIDED | How far auditability goes | any audit/backup work beyond spec 19.2 and 19.3 |
| D-5 | DECIDED | What "meta-harness" means in code | F-0020 beyond coding delegation |
| D-6 | DECIDED | Spec TypeScript paths map into `locus-extension/src/` | - |
| D-7 | DEFAULT | Redis: sixth container | state engine, inner loop, approval gate |
| D-8 | DECIDED | The "85 features" claim is wrong | - |
| D-9 | OPEN (owner edits spec) | Duplicate section ids | tracker mapping by id |
| D-10 | DECIDED | Where the `locus.*` config tree is stored | every feature (via the accessor) |
| D-11 | DEFAULT | `inner_loop_audit` and `inner_loop_log` are two tables | F-0058 |
| D-12 | DEFAULT | Registry / config file names and off conventions (03) | every feature |
| D-13 | OPEN | How a hybrid TUI reaches the VM | hybrid mode (F-0085) |
| D-14 | DEFAULT | `LOCUS_HOME` and timezone come from config | every path and schedule |
| D-15 | OPEN | Format of owner-defined research cron jobs | the "ultimate goal" |
| D-16 | OPEN (low urgency) | Runtime working directory for Pi | S-3 follow-up |
Security items S-1 to S-3 are in 10-security.md; they are not optional.

## B. The decisions

**D-1 Task priority formula (DECIDED by the owner on 2026-10-19: Option A, the recommendation below).** The spec states three things. 25.4 (line 4464): `TWS = P*0.4 + U*0.4 + D*0.2` (Priority, Urgency,
Difficulty) plus a faction lag bonus (+2 if lag over 3 h, +4 over 6 h, -1 if ahead). 25.12 (line 4656): `TWS = D*0.35 + L*0.25 + U*0.20 + C*0.20
+ LagBonus`, with `LagBonus = min(2.5, 0.5 * deferral_count)`. Appendix C (line 8205) repeats the 25.4 formula and says "this table wins".
The faction weekly split conflicts too: Appendix C Health 25 / Leverage 25 / Craft 30 / Expression 20; 25.12 (lines 4675-4678) Craft 40 / Health 25 /
Leverage 20 / Expression 15. Both claim `LOCUS_SYSTEM_v1.md` as the source, and that file was not provided, so nobody can check it.
Options: **A** Appendix C / 25.4 (3 factors, faction lag bonus; the spec's own precedence rule selects it). **B** 25.12 (4 factors, deferral bonus;
richer, fits "multi-factor" better, contradicts Appendix C). **C** the owner writes the formula in the grill.
Recommendation: A with Appendix C's faction split, until the owner opens `LOCUS_SYSTEM_v1.md` sections 3.2 and 10 and says otherwise.
(An earlier note of mine leaned to B; the spec's own precedence rule says A, so A is the recommendation.)

**D-2 Vault (DECIDED).** `00-System 01-Projects 02-Areas 03-Resources 04-Captures 05-Daily 06-Content 07-Archives`. Old names map by the
alias table in `tools/guard/guard.toml` (06-vault-memory-audit.md).

**D-3 "Scale" (DECIDED by the owner on 2026-10-19: Option a, the recommendation below).** The words multi-scale, task scale, scale-aware, "varying scale" appear 0 times in the spec. Nearest ideas: the Three-Layer
Goal Stack (25.5; schema `goal_stack.level` = vision / milestone / daily) and the five pattern horizons H1-H5 (6 h to all-time).
Options: **a** scale = goal-stack level, every goal and task at any level gets its own score from the D-1 formula, with a roll-up rule between
levels. **b** scale = effort size (minutes to months) as a new input. **c** scale = time horizon to deadline.
Recommendation: a, because the level already exists in the spec and the schema. The grill must settle the roll-up rule (does a vision's score
derive from its children, or stand alone?).

**D-4 Auditability (DECIDED by the owner on 2026-10-19: Option b, the recommendation below).** See 06-vault-memory-audit.md. Options: **a** only 19.2 + 19.3 as written (trajectories; nightly archiver of EXTERNAL
AI chats). **b** (a) plus one append-only audit trail for every channel message, tool call, approval, cron run, and inner-loop thought, redacted
first, exported nightly to `05-Daily/Logs/audit-YYYY-MM-DD.md` and carried by LiveSync. **c** (b) plus a hash chain and an owner-facing viewer.
Recommendation: b now, c later. Questions for the grill: does "all chats" include Locus's own Telegram and TUI sessions (the spec archiver mostly
imports external ones), retention, what is redacted.

**D-5 Meta-harness (DECIDED by the owner on 2026-10-19: Option a, the recommendation below).** The word appears 0 times. What exists: `HarnessProvider` in the 25-interface table (default "Pi (fallback)"), spec
3.7 + 11.5 "Coding Harness Delegation" (line 2556: Antigravity, Claude Code, OpenCode, Pi as subprocesses), and master-conductor Stage 8 routing
"coding -> harness, research -> autoresearch". So the idea exists for coding only. Options: **a** coding delegation as the spec says. **b** generalize
`HarnessProvider` to any task type (research, ops, writing) with a registry and a result contract. **c** (b) plus Locus acting as an MCP/ACP client
and server toward other harnesses. Recommendation: a first (F-0020), b after the owner names the harnesses and task types. The spec's
`--dangerously-skip-permissions` example for Claude Code is not accepted (10-security.md S-3).

**D-6 Paths (DECIDED).** Python: `locus-os/sidecar/x.py` means `sidecar/x.py` (the leading `locus-os/` is the repo root). TypeScript: strip the leading
`locus-os/`, `locus/`, `src/`, `core/`, `extensions/` segments and put the rest under `locus-extension/src/`. Examples: `locus/core/channel-registry.ts`
-> `locus-extension/src/channel-registry.ts`; `locus/providers/channels/telegram.ts` -> `locus-extension/src/providers/channels/telegram.ts`;
`locus-os/src/tui/dashboard.ts` -> `locus-extension/src/tui/dashboard.ts`. `tools/tracker/show.py` prints each feature's translated targets.

**D-7 Redis (DEFAULT).** The spec mentions Redis on 35 lines across more than a dozen sections (inner loop, state engine, approval gate, dashboard,
conductor, 30.9 which names container `locus-redis` on 6379), yet section 23 lists five containers without it. Default: `redis` is a sixth compose service on loopback;
every Redis read keeps the spec's own fallback to PostgreSQL (`state_snapshots`); the 30.9 toggle governs it. The owner may drop Redis instead, which
removes `locus-redis` and activates the PostgreSQL fallbacks everywhere.

**D-8 Count (DECIDED).** The spec says "85 features total" (line 134). It has 135 `## Feature` headings (some cover ranges). The tracker has 125 rows:
81 from the old workbook, 7 owner requirements or session reports with no spec section (F-0082 to F-0087 and F-0125), and 37 spec sections the old workbook never
listed (rows marked `origin: spec-gap`). The verifier's spec-gap list, not any of these numbers, is the coverage truth.

**D-9 Duplicate ids (OPEN, owner edits the spec).** Section 2.4 is both State Engine (line 1704) and Provider Registry (line 2460); 2.5 is both Context
Forge (1752) and Model Selection (2465); 26.1 is the heading of the combined "12.1-12.5 + 26.1" scheduler section (4217) and of "Inner Loop" (4768).
Until the owner renumbers, the tracker cites these by title and line, and agents never edit the spec.

**D-10 Config location (DECIDED by the owner on 2026-10-19: the recommendation below, unchanged).** The spec says both: Pi `settings.json` under a `locus` key (lines 465, 545, 5283-5327) and `.locus/config.yaml`
(31 mentions). An earlier session already analysed it and chose `~/.locus/.env` for secrets and `~/.locus/config.yaml` for the rest.
Recommendation: `LOCUS_HOME/config.yaml` is the only home of the `locus.*` tree; the TypeScript accessor reads the same file (the sidecar may not be
up when Pi starts); Pi keeps its own `settings.json` for Pi's settings only. Until decided, nobody reads either file outside the accessor (03).

**D-11 Inner-loop tables (DEFAULT).** Spec 26.1 step 9 writes `inner_loop_audit` (one row per candidate thought: text, scores, routing); the schema
and the data-flow summary list `inner_loop_log` (one row per pass: tokens, suppressed, surfaced). Default: two tables, one each.

**D-12 Names and off behaviour (DEFAULT).** As written in 03-modularity.md.

**D-13 Hybrid TUI transport (OPEN).** Spec 28.1 says the TUI and Telegram share one session and says nothing about a TUI on another machine.
Options: **a** SSH tunnel to the VM's loopback :8420 (no new open port). **b** Tailscale/WireGuard. **c** HTTPS reverse proxy with auth.
Recommendation: a first, b later.

**D-14 Home and timezone (DEFAULT).** `LOCUS_HOME` (default `~/.locus`) replaces the spec's `C:\Users\soni8\.locus`. Times and the timezone
(the spec writes IST everywhere) come from config; the owner's default is `Asia/Kolkata`.

**D-15 Research cron jobs (OPEN).** The owner's ultimate goal has no spec section. Needed: job format (name, schedule, prompt, tier, allowed paths,
budget, destination), how results are stored and reported, how a failed job is retried, where its trail goes (D-4).

**D-16 Runtime cwd (OPEN, low urgency).** Pi runs with cwd = the repo so `--approve` loads `.pi/extensions`; `--no-context-files` stops the developer
rules leaking in. Cleaner: a dedicated runtime folder and `-e <extension>` so `--approve` is not needed. Decide after the installer works.

## C. The four principles you asked about, checked against the spec
| Principle | In the spec? | Evidence |
|---|---|---|
| Meta-harness over other harnesses | Partly | 0 hits for the word; `HarnessProvider`, 3.7 + 11.5, Stage 8 routing (coding only) |
| A multi-factor priority score per task at every scale | Conflicting | two formulas (D-1); 0 hits for scale (D-3); goal stack 25.5 |
| Auditability as a headline feature, all chats auto-backed up to the vault | Partly | 0 hits for the word; 19.2, 19.3, scattered audit tables (D-4) |
| Neo4j Agent Memory as the memory substrate | Yes, in detail | 23 lines; 4.1-4.2, 4.18, Appendix D (clone at `5_Locus/deps/agent-memory`) |
Also absent from the spec: any installer, `/setup`, or pairing (0 hits for "pairing"); only `locus setup`, `locus doctor`, `locus gateway install`.

## D. Why the old numbers were not trusted (facts, not opinion)
1. An earlier AI report said all four principles were "deeply documented". Text search finds the words auditability, meta-harness, and multi-scale 0 times.
2. Tracker row F-0082 has `pct 100` and "install.ps1, install.sh, install.bat created", while its own notes column says "CRITICAL: No install scripts exist!".
3. F-0083 counts "First-Touch Auto-Pairing verified" as done: that is vulnerability S-1. It names no evidence file.
4. F-0084 counts a `sys.modules` fallback shim as the fix for the `core/` duplication: the shim is what creates duplicate module instances (02-architecture-lock.md).
5. The two trackers from the earlier sessions disagreed with each other (145 rows against 86), and the old workbook listed no row at all for 37 spec sections.
6. On a checkout holding only the spec, the verifier puts all 125 features at level 0, and 84 of them carry OVERCLAIM against the old workbook (measured on the spec you sent).
   Expect the first honest number on your real repo to be far below the old 71.4% average.

## E. Reproduce (PowerShell, from the repo root; `Select-String` ignores case by default)
~~~powershell
$S = ".keysndocs\Documentation\Implementation Plans\LOCUS_FEATURE_LOGIC_DECOMPOSITION.md"
@(Select-String -Path $S -Pattern "auditab|meta-harness|multi-scale|varying scale|pairing").Count                  # 0
@(Select-String -Path $S -Pattern "neo4j-labs/agent-memory|Neo4j Agent Memory").Count                                # 23
Select-String -Path $S -Pattern "^## Feature .(2\.4|2\.5|26\.1)\b"                                                   # D-9
Select-String -Path $S -Pattern "TWS = |Faction weekly split|Craft \(Work"                                          # D-1
Select-String -Path $S -Pattern "85 features total"                                                                  # D-8
@(Select-String -Path $S -Pattern "^## Feature ").Count                                                              # 135
@(Select-String -Path $S -Pattern "redis").Count                                                                     # 35
@(Select-String -Path $S -Pattern "config\.yaml").Count; @(Select-String -Path $S -Pattern "settings\.json").Count   # 31 and 5
Select-String -Path $S -Pattern "inner_loop_audit|inner_loop_log"                                                    # D-11
Select-String -Path $S -Pattern "00-System-Data|02-Reviews|05-Logs|06-Resources|07-Diagrams"                         # D-2
Select-String -Path $S -Pattern "dangerously-skip-permissions"                                                       # S-3
~~~
