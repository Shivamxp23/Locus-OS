# 09 - Spec errata and decisions (where LOCUS_FEATURE_LOGIC_DECOMPOSITION.md is wrong, silent, or in conflict)

Status words. **DECIDED** binds everyone. **DEFAULT**: build on it and say so in the handoff; the owner may change it. **OPEN**: an
agent that touches it STOPS and asks; prompt P3 settles OPEN rows with the owner, one question at a time. Only the owner changes a status
(edit this file, commit with `LOCUS_ALLOW_GUARD_EDIT=1`). Line numbers refer to the spec as attached on 2026-10-05; section E reproduces every claim.

## A. Index
| ID | Status | Topic | Blocks |
|---|---|---|---|
| D-1 | DECIDED | Which task-priority formula (TWS) is real | - |
| D-2 | DECIDED | Vault has 8 canonical folders | - |
| D-3 | DECIDED | What "scale" means for per-task priority | - |
| D-4 | DECIDED | How far auditability goes | - |
| D-5 | DECIDED | What "meta-harness" means in code | - |
| D-6 | DECIDED | Spec TypeScript paths map into `locus-extension/src/` | - |
| D-7 | DEFAULT | Redis: sixth container | state engine, inner loop, approval gate |
| D-8 | DECIDED | The "85 features" claim is wrong | - |
| D-9 | OPEN (owner edits spec) | Duplicate section ids | tracker mapping by id |
| D-10 | DECIDED | Where the `locus.*` config tree is stored | every feature (via the accessor) |
| D-11 | DEFAULT | `inner_loop_audit` and `inner_loop_log` are two tables | F-0058 |
| D-12 | DEFAULT | Registry / config file names and off conventions (03) | every feature |
| D-13 | DECIDED | How a hybrid TUI reaches the VM | - |
| D-14 | DEFAULT | `LOCUS_HOME` and timezone come from config | every path and schedule |
| D-15 | DECIDED | Format of owner-defined research cron jobs | the "ultimate goal" |
| D-16 | DECIDED | Runtime working directory for Pi | S-3 follow-up |
Security items S-1 to S-3 are in 10-security.md; they are not optional.

## B. The decisions

**D-1 Task priority formula (DECIDED 2026-10-15).** The spec states three things: 25.4 (line 4464) `TWS = P*0.4 + U*0.4 + D*0.2` plus a faction lag bonus; 25.12 (line 4656) with 4 factors; Appendix C (line 8205) repeats 25.4 and specifies "this table wins".
Decision: "Appendix C / 25.4 formula: `TWS = Priority*0.4 + Urgency*0.4 + Difficulty*0.2` + faction lag bonus (+2 if lag >3h, +4 if >6h, -1 if ahead), with Appendix C faction split (Health 25 / Leverage 25 / Craft 30 / Expression 20)."
Rule: Tasks are scored using `TWS = P*0.4 + U*0.4 + D*0.2 + FactionLagBonus`. Faction targets follow Appendix C (Health: 25%, Leverage: 25%, Craft: 30%, Expression: 20%). The faction lag bonus adds +2 if a faction is behind by >3 hours, +4 if >6 hours, and -1 if ahead of schedule.

**D-2 Vault (DECIDED).** `00-System 01-Projects 02-Areas 03-Resources 04-Captures 05-Daily 06-Content 07-Archives`. Old names map by the
alias table in `tools/guard/guard.toml` (06-vault-memory-audit.md).

**D-3 "Scale" (DECIDED 2026-10-15).** Nearest ideas in spec: Three-Layer Goal Stack (25.5; schema `goal_stack.level` = vision / milestone / daily).
Decision: "Scale = Three-Layer Goal Stack level (vision, milestone, daily); each level is scored using the D-1 formula with roll-up derived from active child tasks."
Rule: Task and goal scale corresponds to `goal_stack.level` (`vision`, `milestone`, `daily`). Each item is scored with the D-1 formula. A parent goal's priority score rolls up as the weighted average of its active child tasks' scores combined with its own intrinsic priority.

**D-4 Auditability (DECIDED 2026-10-15).** See 06-vault-memory-audit.md.
Decision: "Spec 19.2 & 19.3 plus an append-only audit trail (redacted tool calls, channel messages, approvals, cron runs) exported nightly to vault/05-Daily/Logs/audit-YYYY-MM-DD.md."
Rule: Trajectory recording (spec 19.2) and external AI chat archiving (spec 19.3) are implemented as specified. In addition, an append-only audit log records channel messages, tool executions, approval decisions, cron runs, and inner-loop transitions; all records are redacted through `security.redact_patterns` and written nightly to markdown files under `vault/05-Daily/Logs/audit-YYYY-MM-DD.md`.

**D-5 Meta-harness (DECIDED 2026-10-15).** Spec 3.7 + 11.5 describes coding delegation to subprocesses (Antigravity, Claude Code, OpenCode, Pi).
Decision: "Coding delegation first (spec 3.7 / 11.5: delegating coding subtasks to Pi, Claude Code, or external coding agents in isolated scratch worktrees, never using --dangerously-skip-permissions per S-3)."
Rule: `HarnessProvider` implements coding task delegation across subagents. Delegated jobs execute in isolated scratch worktrees (never in the primary repository or vault). All invocations respect security law S-3 (no `--dangerously-skip-permissions`).

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

**D-10 Config location (DECIDED 2026-10-15).** The spec says both: Pi `settings.json` under a `locus` key (lines 465, 545, 5283-5327) and `.locus/config.yaml`
(31 mentions). Decision: "LOCUS_HOME/config.yaml is the canonical home of the locus.* tree; secrets stay in ~/.locus/.env".
Rule: `LOCUS_HOME/config.yaml` is the only home of the `locus.*` tree; the TypeScript accessor reads the same file (the sidecar may not be
up when Pi starts); Pi keeps its own `settings.json` for Pi's settings only. All modules access configuration via `sidecar.config` or
`locus-extension/src/config.ts`; nobody reads either file outside the accessor.

**D-11 Inner-loop tables (DEFAULT).** Spec 26.1 step 9 writes `inner_loop_audit` (one row per candidate thought: text, scores, routing); the schema
and the data-flow summary list `inner_loop_log` (one row per pass: tokens, suppressed, surfaced). Default: two tables, one each.

**D-12 Names and off behaviour (DEFAULT).** As written in 03-modularity.md.

**D-13 Hybrid TUI transport (DECIDED 2026-10-15).** Spec 28.1 says the TUI and Telegram share one session and says nothing about a TUI on another machine.
Decision: "SSH loopback tunnel (`ssh -L 8420:127.0.0.1:8420`) keeping all VM service ports strictly on 127.0.0.1 per security law S-2."
Rule: In hybrid mode, backend services on the VM bind exclusively to 127.0.0.1 (sidecar :8420, CouchDB :5984). The local machine running the Pi TUI connects via an SSH port forward (`ssh -L 8420:127.0.0.1:8420 <vm_host>`). No public ports or unauthenticated reverse proxies are opened on the VM.

**D-14 Home and timezone (DEFAULT).** `LOCUS_HOME` (default `~/.locus`) replaces the spec's `C:\Users\soni8\.locus`. Times and the timezone
(the spec writes IST everywhere) come from config; the owner's default is `Asia/Kolkata`.

**D-15 Research cron jobs (DECIDED 2026-10-15).** The owner's ultimate goal has no spec section. Decision: "Research jobs are defined in YAML files under LOCUS_HOME/jobs/ (or config key locus.research.jobs) with cron schedules, prompts, model tiers, and vault destinations".
Rule: Each job defines `{name, schedule, prompt, tier, allowed_paths, budget, destination, notify, retry}`. The scheduler invokes `sidecar/cron_runner.py` with `session_id="cron_<job_id>"`, executing the prompt via `run_pi_turn`. Outputs write to the specified markdown destination under `vault/` (e.g. `vault/05-Daily/Research/`) and run metadata is appended to the execution log table.

**D-16 Runtime cwd (DECIDED 2026-10-15).** Pi runs with cwd = the repo root so `--approve` loads `.pi/extensions` / `locus-extension`; `--no-context-files` stops developer rules from leaking in. Decision: "Pi bridge runs from repo root with mandatory --approve --no-context-files flags until installer packaging moves to -e extension flags".
Rule: `sidecar/pi_bridge.py` executes Pi with working directory set to repository root, enforcing `--approve --no-context-files`. Future installer packaging may move to dedicated runtime directory with `-e <path>`.

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
