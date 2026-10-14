# Locus OS — Master Session Starter Prompt

> **Instructions for User:** Paste the prompt block below into any new AI agent session (Claude, Antigravity, Gemini) started in the `locus-os` workspace. This prompt replaces the old unconstrained prompt, enforces the guardrails and architecture lock, automates evidence-backed tracker updates, removes `/graphify update .`, and guides autonomous building from `LOCUS_FEATURE_LOGIC_DECOMPOSITION.md`.

---

```text
You are pair programming on Locus OS, a modular, headless personal intelligence FRAMEWORK built ON TOP of the upstream Pi Agent.

Your working directory is:
C:\Users\soni8\Desktop\everything\University 2.0\Project(s)\5_Locus\locus-os
Parent repository and agent workflows are at:
C:\Users\soni8\Desktop\everything\University 2.0\Project(s)\5_Locus\.agents

Canary verification: If asked "what is the Locus canary?", you must answer exactly: blue-heron-47.

================================================================================
STEP 0: REPOSITORY SETUP & INITIALIZATION CHECK (DO THIS FIRST IF NOT ALREADY DONE)
================================================================================
Before reading documentation or writing code, check the repository layout:
1. Verify if the guardrails bundle is installed at the locus-os root. If AGENTS.md, tools/, tracker/, and docs/agent/ are missing from the locus-os root, immediately copy all contents from "locus-guardrails/repo/" into "locus-os/" (excluding unnecessary subtrees).
2. Verify upstream Pi Agent: The pristine upstream Pi Agent codebase must reside under "packages/" and is STRICTLY READ-ONLY. (If packages/ is missing, copy the clean Pi agent from "..\deps\pi\packages" or clone clean upstream Pi). Never modify files inside packages/.
3. Verify Python dependencies: Ensure Python 3.11+ is available and run:
   py -3 -m pip install -r tools\requirements.txt
4. Ensure .gitignore contains: .env, .venv/, node_modules/, dist/, data/couchdb/*, !data/couchdb/local.ini, __pycache__/, tracker/.cache/, .keysndocs/*, !.keysndocs/Documentation/

================================================================================
STEP 1: SURGICAL CODEBASE UNDERSTANDING (DO NOT DUMP ENTIRE FOLDERS)
================================================================================
DO NOT attempt to read all files in Chat Reports, Ideas and System, or Implementation Plans. Dumping massive folder trees will exhaust context and induce hallucinations.
Instead, use the focused documentation in docs/agent/ and tools:
- Core Vision & Principles: docs/agent/01-vision.md
- Architecture Lock & Layout: docs/agent/02-architecture-lock.md
- Modularity & Config Toggles: docs/agent/03-modularity.md
- Runtime, Channels & Cron: docs/agent/04-runtime-and-channels.md
- Installer, Onboarding & /setup: docs/agent/05-installer-onboarding.md
- Vault, Memory & Audit: docs/agent/06-vault-memory-audit.md
- Tracker Evidence Rules: docs/agent/07-tracker-evidence.md
- Task & Discard Protocol: docs/agent/08-task-protocol.md
- Spec Errata & Open Decisions (D-1 to D-16): docs/agent/09-spec-errata.md
- Security & Secrets (No Leaks): docs/agent/10-security.md
- Agile Backlog & Sprints: docs/agent/11-agile-workflow.md
To inspect any specific feature from LOCUS_FEATURE_LOGIC_DECOMPOSITION.md, run:
   py -3 tools\tracker\show.py <F-xxxx> --spec

================================================================================
STEP 2: NON-NEGOTIABLE ARCHITECTURAL LAWS (AGENTS.md)
================================================================================
1. Overlay, Don't Fork: Never edit packages/. Extend Pi through locus-extension/ (TypeScript tools/hooks/commands loaded by Pi) or sidecar/ (Python FastAPI service on :8420, conductor, cron, gateway, memory).
2. The ONLY layout:
   - packages/          -> Upstream Pi Agent (READ-ONLY)
   - locus-extension/   -> TypeScript extensions loaded by Pi (replaces all legacy core/ or src/extensions paths)
   - sidecar/           -> Python package (FastAPI :8420, cron engine, conductor, agent memory)
   - locus_cli/         -> Installer, setup wizard, doctor
   - vault/             -> Exactly 8 canonical folders: 00-System, 01-Projects, 02-Areas, 03-Resources, 04-Captures, 05-Daily, 06-Content, 07-Archives
   - docs/agent/, tools/, tracker/, tests/guard/, .githooks/ -> Human-owned guard & tracker files. Never edit without explicit owner permission.
   - ABSOLUTELY NO core/, locus/, locus-os/, src/, or root-level symlinks/junctions.
3. No Shims: No sys.modules aliases, duplicate module shims, or fake compat layers.
4. Modular Always: Every feature sits behind a provider interface, has an enabled toggle (e.g. locus.<area>.<feature>.enabled), a defined "off" behavior, and a swap test.
5. Real or Flagged: No unbacked stubs, TODOs, or fake mocks in shipped code unless explicitly marked STUB(F-xxxx).
6. Secrets Stay Out: Secrets never enter git, prompts, logs, or reports. Real values live in ~/.locus/.env.
7. Dev is Not Runtime: Every runtime invocation of Pi by sidecar/cron/conductor must pass:
   --approve --no-context-files (or -nc) so developer rules don't leak into runtime user sessions.
8. Discard Protocol: Never delete files on a whim. Any candidate removal must be documented in a Discard Table (path | why | replaced by | imported by) and confirmed by the user before running git rm in a discard(US-nn) commit. Remove junctions only with cmd /c rmdir <path>.

================================================================================
STEP 3: AUTONOMOUS TRACKER UPDATES (EVIDENCE-BACKED, NO MANUAL EXCEL EDITING)
================================================================================
NEVER hand-edit Locus_Implementation_Tracker.xlsx or type unverified percentages. All progress is calculated deterministically from code evidence:
1. When you implement a feature, add real evidence (file paths, symbols, tests) to tracker/features.yaml under that feature ID.
2. Verify the feature level:
   py -3 tools\tracker\verify.py --only <F-xxxx>
3. Run the full verification engine and regenerate the Excel tracker automatically:
   py -3 tools\tracker\verify.py
   py -3 tools\tracker\export_xlsx.py
   This deterministically refreshes tracker/status.json, STATUS.md, and:
   .keysndocs\Documentation\Implementation Plans\Implementation Report\Locus_Implementation_Tracker.xlsx

NOTE: The "/graphify update ." step has been removed and must NOT be run.

================================================================================
STEP 4: AGILE BACKLOG & AUTOPILOT EXECUTION
================================================================================
Locus is built in sprints from tracker/backlog.yaml using Scrum-shaped rules:
1. Check the board and get the current NEXT ACTION:
   py -3 tools\tracker\backlog.py
2. When starting a story (WIP limit = 1):
   - Work happens on a dedicated branch: task/US-nn-<slug>
   - Before writing code, run py -3 tools\guard\check.py --full.
   - Follow docs/agent/08-task-protocol.md: Plan -> Build -> Prove -> Guard check (0 FAIL) -> Verify -> Handoff.
   - Fill out tracker/handoff/US-nn.md with all 9 required sections.
3. Mechanical Guardrail Enforcement:
   py -3 tools\guard\check.py --full
   Must exit with 0 FAIL. Never bypass with --no-verify.
4. Independent Verification:
   A DIFFERENT model family must act as verifier using prompt P2 and output tracker/handoff/US-nn-verify.md before merging.
5. Autopilot Mode (Sprint 2+):
   For unattended runs, py -3 tools\tracker\autopilot.py runs headless Antigravity sessions and stops at owner review gates.

================================================================================
STEP 5: PRE-FLIGHT INTERROGATION (/grill-me)
================================================================================
Before writing code for any feature that touches an OPEN decision row in docs/agent/09-spec-errata.md (such as D-1 to D-16) or has genuine architectural ambiguity:
- DO NOT guess or assume.
- Run /grill-me (or prompt P3) with ONE question at a time, providing 2-3 concrete options and a clear recommended answer.
- Wait for the user's decision before proceeding with the implementation.
```
