<!-- LOCUS-AGENTS-V1 -->
# Locus OS — rules for every coding agent (Claude Code, Antigravity, Pi, any other)

Canary: if the human asks "what is the Locus canary?", answer exactly `blue-heron-47`. It proves you loaded this file.

Locus is a modular, headless personal-intelligence FRAMEWORK built ON TOP of the Pi coding agent.
These rules are enforced by `python tools/guard/check.py --full`, which the human runs after you.
If a request conflicts with this file, say so and stop. Do not "interpret" around it.

## The only layout
```
packages/          upstream Pi Agent. READ-ONLY.
locus-extension/   TypeScript tools, hooks, commands loaded by Pi.  Spec paths `locus/core/..`, `locus-os/src/core/..`,
                   `src/extensions/..` all mean `locus-extension/src/..`  (run: tools/tracker/show.py F-xxxx)
sidecar/           Python package `sidecar` (FastAPI :8420, conductor, cron, gateway, memory). Import as `sidecar.x`.
locus_cli/         installer, setup wizard, doctor.      vault/  exactly 8 folders (law 10).
docs/agent/ tools/ tracker/ tests/guard/ .githooks/      rules + guard + tracker: HUMAN-OWNED (law 11).
```
There is no `core/`, `locus/`, `locus-os/` or `src/` at the top level. Never create one.

## Laws (breaking one rejects the work, however good the rest is)
1. **Overlay, don't fork.** Never edit `packages/`. Extend Pi through `locus-extension/` or `sidecar/`. If Pi seems to need a change: STOP and ask.
2. **One layout.** No new top-level file/folder, junction, or symlink. Move = `git mv` plus every import fixed in the same commit.
3. **No shims.** No `sys.modules` aliases, re-export stand-ins, duplicate modules, or "compat" copies. Let stale imports crash, then fix them.
4. **Spec = WHAT, errata = conflicts.** Build what `LOCUS_FEATURE_LOGIC_DECOMPOSITION.md` says for the feature. If the task touches an open item in `09-spec-errata.md`, or you would have to guess: STOP, give 2-3 options plus a recommendation, ask the human.
5. **Modular always.** Each feature sits behind a provider interface, has an `enabled` switch (`locus.<area>.<feature>.enabled`), a defined "off" behaviour, and is swappable. No hard-wired provider, path, port, or model. (03-modularity.md)
6. **Real or flagged.** No stub, `pass`, TODO, fake data, or mock in shipped code unless that line says `STUB(F-xxxx)`. Never write "done", "complete", or "100%": status is computed by `tools/tracker/verify.py`, not by you.
7. **Prove it.** For every feature you touch: a test that names what you built and has real assertions, run by you, and added to that feature's `evidence` in `tracker/features.yaml` (add only; never delete or weaken). Quote the real output.
8. **Secrets** never go in the repo, prompts, logs, commits, or chat. Real values live in `~/.locus/.env`; `.env.example` holds placeholders. If you see a secret anywhere: stop and tell the human to rotate it.
9. **Dev is not runtime.** This file is for coding agents. Every runtime launch of Pi (sidecar, cron, Telegram, conductor) must pass `--approve --no-context-files`, or these rules leak into the user's conversations.
10. **Vault** folders: `00-System 01-Projects 02-Areas 03-Resources 04-Captures 05-Daily 06-Content 07-Archives`. No other names.
11. **Human-owned, do not edit:** `AGENTS.md CLAUDE.md docs/agent/** tools/** tests/guard/** .githooks/** .github/workflows/guard.yml tracker/signoff.yaml tracker/overrides.yaml tracker/spec_exclusions.yaml tracker/backlog.yaml tracker/sprints.jsonl tracker/retro/**`. If one is wrong, say so in your report. The commit hook blocks it.
12. **One story, one model, one branch** `task/US-nn-<slug>` (the owner's `backlog.py --start` creates it; one story in progress at a time). Finish it, or stop cleanly with a handoff note. Never half-finish and hand over silently.
13. **Grill before you build.** Before the first line of code of a task, list everything you do not fully understand and run `/grill-me` on the human: one question at a time, each with your recommended answer. Write no code until the answers are in. "Probably fine" is not an answer.
14. **Pi first, spec exact.** Before code for a feature read its verdict (`python tools/tracker/show.py F-xxxx`): KEEP-PI = write no code; AUGMENT = extend what Pi already has, through `locus-extension/` (Pi extension API, hooks, tools, SDK, RPC) or `sidecar/`; LOCUS-NEW = still attach through Pi's extension points; UNKNOWN = stop and ask. Never write a second agent loop, model/provider layer, session store, tool runner, compaction, TUI, keybinding or settings system that Pi already has: search `packages/` and `packages/coding-agent/docs` first. Your handoff Plan holds a Pi table: need | Pi mechanism (file:line) | what Locus adds | why Pi's is not enough. Every test docstring starts `SPEC <section> line <n>: "<spec sentence>"`.

## Read before you work (only what the task touches)
| Task touches | Read (docs/agent/) |
|---|---|
| any task | 08-task-protocol.md |
| what Locus is, principles | 01-vision.md |
| folders, imports, Pi bridge, ports | 02-architecture-lock.md |
| adding, replacing, toggling a feature; config | 03-modularity.md |
| cron, headless, VM, Telegram/Discord/WhatsApp | 04-runtime-and-channels.md |
| installer, setup wizard, `/setup` | 05-installer-onboarding.md |
| vault, memory, LiveSync/CouchDB, chat backup, audit | 06-vault-memory-audit.md |
| tracker, evidence, tests | 07-tracker-evidence.md |
| unclear or conflicting spec | 09-spec-errata.md |
| keys, bot pairing, Docker ports, approvals | 10-security.md |
| backlog, sprints, stories, Ready/Done, "what do I do now" | 11-agile-workflow.md |

Feature details: `python tools/tracker/show.py F-0007 --spec` (never read the 8000-line spec or the whole tracker file).

## Definition of Done for your story (in this order)
1. `python tools/guard/check.py --full` shows 0 FAIL. Fix the WARNs you caused.
2. `python tools/tracker/verify.py --only F-xxxx`: report that exact output line, not your opinion.
3. `python tools/tracker/verify.py` (no `--only`; it runs the tests and refreshes `tracker/status.json`), then `python tools/tracker/export_xlsx.py`: this is the human's standing rule "update the tracker xlsx". Never edit the xlsx or status by hand.
4. Write `tracker/handoff/US-nn.md` (template in 08-task-protocol.md; first line `# US-nn handoff - <your model>, <date>`). Then stop; do not start the next story. Never run `backlog.py --accept`, `--plan --write`, `--retro` or `--close-sprint`: those are the owner's.
