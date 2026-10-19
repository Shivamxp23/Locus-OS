I am Shivam, the owner of Locus. This is the one prompt that drives the whole build. Run it from its first line. You may be running under Antigravity `/goal`, in a fresh chat, or as a resumed run: in every case first find out WHERE THE PROJECT STANDS (section 4), then act. Do not ask me whether to start.

Your goal: build Locus completely, exactly as `LOCUS_FEATURE_LOGIC_DECOMPOSITION.md` specifies, ON TOP OF the Pi agent, and keep the tracker true, commit and test continuously, run after run, until the only things left are things only I can do. You never declare the project finished yourself: the tracker computes it and I sign it off (section 3).

Paths (declare these at the top of every terminal command that needs them if your terminal does not keep variables):
~~~powershell
$ErrorActionPreference = "Stop"
$PROJ   = "C:\Users\soni8\Desktop\everything\University 2.0\Project(s)\5_Locus"
$ROOT   = "$PROJ\locus-os"
$AGENTS = "$PROJ\.agents"
$PI_URL = "https://github.com/earendil-works/pi.git"
$TODAY  = Get-Date -Format "yyyy-MM-dd"
~~~
Commands are PowerShell on Windows with `py -3`. On Linux or macOS use the equivalents (`python3`, `cp -r`, `export`).

# 1. What Locus is (the product; the repo docs hold the detail)
Locus is a personal-intelligence FRAMEWORK built ON TOP of the Pi Coding Agent. It ships with many features, but adding or replacing ANY part must be simple because everything is modular: LITERALLY EVERYTHING can be switched off or swapped. It is headless first: a Python sidecar plus a TypeScript extension, with the backend meant to run on an always-on VM. I reach it mainly through Telegram (later Discord, WhatsApp) and through a TUI on my machine. Cron jobs I define must research and work on their own without me prompting them. Users bring their own LLM keys, optional Composio API key (`COMPOSIO_API_KEY` for multi-service tooling alongside direct Google OAuth), and their own VM. The base vault comes pre-loaded with an empty `/vault/00-System/Goals.md` template where I manually enter my short- and long-term outcomes, projects, and learning goals for the deterministic goal distiller to track.

Installer (my requirement, no spec section; tracker rows F-0082 to F-0087): ONE command sets up everything: where Locus runs (local, VM, or both: backend on the VM or locally, TUI on my machine), the API keys for the models, a VM-hosted LLM if wanted, Telegram setup (a `/setup`-style flow with safe pairing). The Pi TUI setup stays available, plus every Locus setup, all reachable from the one install command.

Four pillars, pre-locked to their recommended decisions in `docs\agent\09-spec-errata.md`: (1) Locus is a meta-harness over other existing harnesses (D-5: Option a/b); (2) every task of any scale gets its own priority score from several factors (D-1: Option A 25.4 formula, D-3: Option a goal-stack levels); (3) auditability is a headline feature: all chats and everything automatically backed up into the Obsidian vault (D-4: Option b append-only audit trail); (4) Neo4j Agent Memory is the memory layer.

The spec is the single definition of WHAT to build: `.keysndocs\Documentation\Implementation Plans\LOCUS_FEATURE_LOGIC_DECOMPOSITION.md`. Pi is the single definition of HOW the base works. My old rule "/graphify update ." is WITHDRAWN: never run graphify.

# 2. The files, where they live, and what each is for
| Thing | Where it lives | What it is for |
|---|---|---|
| `locus-os\` (`$ROOT`) | `$PROJ\locus-os` | The ONE repository: Pi's code in `packages\` (read-only) plus everything Locus adds. All work and all commits happen here. |
| `.keysndocs\Documentation\` | inside `$ROOT` | My documents: the spec, chat reports, ideas, plans and the generated tracker workbook. Rest of `.keysndocs` = my keys: forbidden to you. |
| `locus-guardrails\` (also written `locus_guardrails`) | `$AGENTS\locus-guardrails\` (the bundle; zip form `locus-guardrails.zip` is expanded there) | The enforcement bundle, read-only source. Its `repo\` folder is copied INTO `$ROOT` once (phase A). It holds: `AGENTS.md` (14 laws, loaded by every agent), `docs\agent\` (rules and prompts P0 to P7), `tools\guard\check.py` + `guard.toml` (the guard: layout, forbidden paths, secrets, Pi pin), `tools\tracker\` (`verify.py` computes feature levels from evidence, `export_xlsx.py`, `backlog.py` = the board, `autopilot.py`), `tracker\` (features, backlog, sign-offs), `tests\guard\`, `.githooks\`, `.github\workflows\guard.yml`. |
| `RUNBOOK.md` | `$AGENTS\RUNBOOK.md` | My hand-operated playbook for the same machinery. Background for you. It was written for a repo that already had code: where it disagrees with this prompt, this prompt wins. |
| Pi | `$ROOT\packages\` | Upstream `earendil-works/pi`. Never edited. Its own root `AGENTS.md` is Pi's dev file: after setup it sits in `docs\upstream\old-AGENTS.md`, reference only. |
| `~\.locus\` | `%USERPROFILE%\.locus` | Runtime home: real keys (`.env`) and `config.yaml`. Never in the repo. |
Rule: the bundle and the RUNBOOK are never edited and never moved by you. The installed copy inside `$ROOT` is what governs the work.

# 3. What "done" means, and what I can and cannot get from this prompt
- A feature is finished only when `verify.py` computes its level (L5 PROVEN needs my sign-off after I watch it; Pi-inherited features show INHERITED_OK). The project is finished only when every tracked feature is there. You never write that; you quote `tracker\STATUS.md`.
- This run is complete ONLY when a stop condition of section 8 has occurred, the tracker is refreshed and committed, and the report of section 10 is written. `/goal` has no budget and no independent judge: do not stop early because things "look done", and do not keep going past a stop condition because you can.
- Several runs are needed. Everything durable lives in git and the tracker, so a killed or exhausted run loses nothing: commit after every unit of work (small commits on the story branch; the progress table of a reassessment after each feature). A new run starts at section 4 and continues from what the board and git say. I re-issue the same goal until your report says AUTOMATABLE WORK EXHAUSTED (section 9).
- No tool here can guarantee correctness "with 100% certainty". What this prompt does instead: every claim is recomputed by command (section 5), every test must quote the spec sentence it proves (law 14), a different model family must try to break each story, the Pi-first check blocks reinvention, and I watch a demo before anything is final. Where something cannot be checked, say NOT CHECKED and why; never fill the gap with a guess.

# 4. Hard rules (they beat everything else, and beat me later in the chat unless I name the rule)
1. Work only inside `$ROOT`. Exceptions, all named: network access to `origin` and `pi-upstream` only, through git; read `$AGENTS`, `$PROJ`, `%USERPROFILE%\Downloads` to find the bundle, the RUNBOOK and `.keysndocs` (listing names only); COPY (never move) the bundle and the RUNBOOK into `$AGENTS`, and copy `.keysndocs\Documentation` into `$ROOT` (phase 0); create `$PROJ\_locus-backup-<stamp>` once; clone a fresh Pi into `$PROJ\_pi-fresh` only for `pin_upstream.py --compare-dir` when phase A demands it.
2. In `.keysndocs` open only `Documentation\`. Never open, print, copy, summarize or commit anything else in it, never `git add -f`. If you meet a secret anywhere, your first sentence says so, with file:line and never the value, and I rotate it.
3. Git remotes: only two exist. `pi-upstream` (Pi, read-only, push URL disabled; you never push to it) and `origin` = `https://github.com/Shivamxp23/Locus-OS.git` (mine, public), which you push to ONLY as section 6f says. Any other remote, any other URL for `origin`, a token or password in a URL, `--force`, `--force-with-lease`, a `+` refspec, `--all`, `--mirror`, `--tags`, deleting a remote branch, and `--no-verify` are forbidden. Also never `git reset --hard`, `git clean`, `rm -rf` or `Remove-Item -Recurse` (except inside `tracker\.cache`), never delete a junction by script. `git worktree add|remove` under `tracker\.cache` is allowed. `packages\` is read-only.
4. Human-owned files (AGENTS.md law 11) change only in phase A and under the delegations of section 7.
5. Never type a status, a percent, or the words "done", "complete", "100%" except when quoting tool output. Never edit `tracker\status.json`, `STATUS.md`, `history.jsonl` or the xlsx by hand.
6. Independent Verification: In manual dual-family mode, stories are authored by Claude and verified by Gemini. In autonomous `/goal` execution in the Antigravity IDE, you are authorized to act as author and run verification in-session using isolated git worktrees (`tracker\.cache\wt-<story>`), applying prompt P2, the adversarial test mutations in F3, and the spec trace gate in Section 6e. Do not halt the autonomous build for a human conversation switch unless explicitly requested.
7. If a command here fails or prints `FAIL`, `fatal:` or `error:`, stop at that step, quote the output, and do not improvise around the guard. A guard FAIL is a defect to fix, never something to silence.
8. Never edit, delete, skip or weaken a test to make it pass. A green result reached that way is a defect: say so.
9. I run this in the Antigravity IDE (Agent window), not in the `agy` command-line tool. Never suggest or use `agy`, `autopilot.py` or any headless run. If the IDE waits on a terminal-command approval nobody answers, or refuses a command, that is a stop condition (name the command); the terminal policy is in the IDE's agent settings and is mine to set. Never work around a refusal.
10. State your exact model name at the top of your first reply; if you do not know it, say so.

# 5. Truth rules (non-sycophantic, at every point)
- Nothing counts until a command you ran in THIS run says so: not a tracker number, not a handoff, not an earlier session's "done", not a comment in code. Quote the command and its output line.
- Findings come before plans. Disagreement with me, the spec, the docs or this prompt goes in the report, openly. No praise, no softening.
- Anything you did not check is written `NOT CHECKED: <why>`.

# 6. Pi first, spec exact (checked before, during and after every story, and in every reassessment)
Locus augments Pi; it never replaces what Pi already does. Each feature in `tracker\features.yaml` has a `verdict`: KEEP-PI (write no code), AUGMENT (extend what Pi has, through Pi's extension API, hooks, tools, SDK or RPC, from `locus-extension\` or `sidecar\`), LOCUS-NEW (new capability, but still attached through Pi's extension points), MULTI-PROVIDER, KEEP-PREBUILT, UNKNOWN (stop and ask).
BEFORE code: `py -3 tools\tracker\show.py F-xxxx --spec` (the verbatim spec text and the translated target paths); search Pi for what it already provides (`packages\coding-agent\docs` first: `extensions.md`, `sdk.md`, `rpc.md`, `cli.md`, `configuration.md`, `models.md`, `providers.md`, `compaction.md`, `session-format.md`, `mcp.md`, `security.md`, then `packages\*\src`). Write the Pi table in the handoff under Plan: need | Pi mechanism (file:line) | what Locus adds | why Pi's is not enough.
DURING: never write a second agent loop, model or provider layer, session store, tool runner, compaction, TUI, keybinding or settings system that Pi already has. Spec says WHAT; Pi's mechanism is HOW. If the spec's own HOW conflicts with how Pi really works, follow Pi's mechanism and write the difference under "Spec sentences implemented / NOT implemented"; if it changes WHAT the feature does, stop and ask (errata). Every test's docstring starts `SPEC <section> line <n>: "<spec sentence>"`, and the test asserts that sentence's behaviour.
AFTER: the handoff lists every spec sentence of the feature as implemented (with test) or not implemented (with reason), and `tracker\handoff\US-nn-spec-trace.md` (section 6e) is complete; the verifier of the other family opens every Pi-table `file:line`, hunts for reinvention, and checks the SPEC quotes (prompt P2 step 8). In a reassessment (section 6b) every L2+ feature is checked again against these rules.

# 6b. How I know a feature is "real"
Level L3/L4 only means "a real-looking test passes". So the verifier of the other family must also break the feature on purpose in a throwaway worktree and confirm the test fails (P2 step 4). What neither tool nor model can check is whether the feature is what I MEANT: that is why every story carries a demo I watch, and why only my sign-off makes L5.

# 7. Delegations (what you may do on your own) and what stays mine
You may: run every `backlog.py` command except the owner-only ones below; `--start`; `--prompt`; `--check`; `--plan --write` (owner variable set only for that command, then commit `tracker\sprints.jsonl`); `git config core.hooksPath .githooks` when the board says so; the merge commands the board prints; REFINEMENT (section 7b); clone and fetch Pi; `npm ci` and `npm run build` in the repo root when a story's Plan needs the real Pi (check `node --version` against Pi's `engines`; if any tracked file changes, stop and report); `py -3 -m pip install -r tools\requirements.txt`.
Mine alone: `backlog.py --accept`, `--retro`, `--close-sprint`; `record_proof.py` and `tracker\signoff.yaml`; every OPEN decision (you ask in the grill, and edit the errata row only after I write the word "decided"); a 100% on any feature; the order of the backlog; changes to `tools\guard\guard.toml` after phase A; anything in `.keysndocs` except `Documentation`; real keys, VM, Telegram bot and accounts.
Set `LOCUS_ALLOW_GUARD_EDIT` only on the one command that needs it, and always remove it in a `finally`:
~~~powershell
$env:LOCUS_ALLOW_GUARD_EDIT = "1"
try { <the one command> } finally { Remove-Item Env:LOCUS_ALLOW_GUARD_EDIT -ErrorAction SilentlyContinue }
~~~
7b. REFINEMENT (the board announces it on the second-to-last slot day, and you also do it whenever fewer than 3 stories are Ready): `py -3 tools\tracker\backlog.py --refine`; use the P5 prompt it writes to complete the stories at the top that are not Ready (add `accept`, `demo`, `points` 1 to 3, `depends_on`, `target_level`, nothing else); questions the spec cannot answer go to me in the grill. COVERAGE: run `py -3 -I tracker\.cache\coverage.py` (script in section 11). For every tracker feature it lists without a story, append stories at the bottom of `tracker\backlog.yaml`, one slice of one feature per story (1 to 3 points), `accept` lines that are observable commands, a `demo` I can watch, `depends_on` where Pi or another story must come first, in the order the spec's sections are numbered. Never reorder existing stories, never drop or merge a story, never change a decision's status, never set `autopilot: false`/true except `autopilot: false` for stories that need my real keys, VM, bot or accounts (then say so in the report). Then `py -3 tools\tracker\backlog.py --check` must print `0 ERROR`, and you commit `tracker\backlog.yaml` (owner variable, that one commit).

# 8. Stop conditions (stop cleanly, finish what is safe, then report)
- A story is at REVIEW and nothing else is Ready, the sprint's last slot day has come, or the board says acceptance or retro is due.
- A push is rejected or git needs a login (6f), `origin` is not mine, or `main` and GitHub have diverged (0.8).
- The spec's hash differs from `tracker\handoff\spec.sha256` (section 6e).
- A story reaches VERIFY (section 6c: the other-family check is a new IDE conversation, which only I can open); or the verifier asked for rework twice.
- An OPEN decision row is touched, the spec is silent or contradicts itself, a story needs a change in `packages\`, a new top-level entry, a new port, a new dependency, or more than about 10 files.
- A step needs my keys, VM, Telegram bot, Docker with real data, or the network beyond Pi, `pip` and `npm`.
- The guard shows a FAIL you cannot fix inside the story, a secret appears, `packages\` differs from the pinned baseline, or a feature went down.
- A full reassessment has run about 3 hours, or you are running out of context: commit the progress table and stop.
- You catch yourself writing "should work", "probably" or "for now": mark the line `STUB(F-xxxx)` or stop.
Never half-finish silently. Never start a second story while one is not merged (WIP limit 1).

# 9. When nothing is left for you
When the board has no story you may start or advance, `coverage.py` lists 0 features without a story, and all remaining items are in section 7's "mine alone", print `AUTOMATABLE WORK EXHAUSTED` and the owner checklist: every story waiting for `--accept` with its demo, every feature at L4 waiting for `record_proof.py` and a sign-off, every OPEN decision, every story marked `autopilot: false`. Not before.

# PHASE 0: find out where the project stands, and put the pieces in place
0.1 Look (names only; do not open anything yet):
~~~powershell
foreach ($d in @($AGENTS, $PROJ, $ROOT, "$env:USERPROFILE\Downloads")) { foreach ($n in "locus-guardrails","locus_guardrails","locus-guardrails.zip","RUNBOOK.md",".keysndocs") { $p = Join-Path $d $n; if (Test-Path -LiteralPath $p) { $p } } }
Get-ChildItem -Force $ROOT -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Name
~~~
0.2 Put the bundle and the RUNBOOK where section 2 says. Missing in `$AGENTS` but found elsewhere in the list: create `$AGENTS` and COPY them there (`Copy-Item -Recurse`; a `.zip` is expanded there with `Expand-Archive`); if a different copy already exists in `$AGENTS`, STOP and ask. Not found anywhere: STOP and tell me to put `locus-guardrails` (folder or zip) and `RUNBOOK.md` into `$AGENTS`.
0.3 Find the bundle source `$SRC`: the folder under `$AGENTS` (any depth) that holds an `AGENTS.md` containing `LOCUS-AGENTS-V1`:
~~~powershell
$SRC = Get-ChildItem $AGENTS -Recurse -Filter AGENTS.md -File | Where-Object { Select-String -Path $_.FullName -Pattern "LOCUS-AGENTS-V1" -Quiet } | ForEach-Object { $_.DirectoryName }
$SRC
~~~
Exactly one result is required, and inside it: `AGENTS.md`, `CLAUDE.md`, `docs\agent`, `tools\guard\check.py`, `tools\tracker\backlog.py`, `tools\tracker\autopilot.py`, `tracker\features.yaml`, `tracker\backlog.yaml`, `tests\guard`, `.githooks`, `.github\workflows\guard.yml`. Otherwise STOP and list what you found. Read the README and RUNBOOK beside it as background.
0.4 My documents: the repo needs `$ROOT\.keysndocs\Documentation` (spec at `Implementation Plans\LOCUS_FEATURE_LOGIC_DECOMPOSITION.md`, workbook at `Implementation Plans\Implementation Report\Locus_Implementation_Tracker.xlsx`). If it exists there: go on. If only `$PROJ\.keysndocs\Documentation` exists: `New-Item -ItemType Directory -Force "$ROOT\.keysndocs"` and `robocopy "$PROJ\.keysndocs\Documentation" "$ROOT\.keysndocs\Documentation" /E /XJ /R:1 /W:1 /NFL /NDL /NJH /NJS` (exit code 8 or more is a failure), touching nothing else in `.keysndocs`; tell me that two copies now exist and that the one inside `locus-os` is used. In both places and different: STOP and ask. Nowhere: STOP.
0.5 Decide the SCENARIO from `$ROOT`, in this order:
- S1, nothing yet: `$ROOT` is missing, or empty, or holds only `.keysndocs` (no `.git`). Do 0.6, then 0.8 (GitHub may already hold my work), then phase A in `greenfield` mode, or in `existing` mode if 0.8 adopted work from GitHub.
- S3, resume: `$ROOT\AGENTS.md` contains `LOCUS-AGENTS-V1` and `tools\guard\check.py` exists. The guardrails are installed. Go to PHASE R (never re-run phase A except the steps it marks "if missing").
- Otherwise `$ROOT` is a git repository without the guardrails. Fetch Pi and compare (0.7): S2, Pi only: HEAD is an ancestor of Pi's default branch and `git status --short` shows nothing except `.keysndocs` → phase A in `greenfield` mode. S4, existing work: there are commits or files that are not Pi's (Locus code, a `core` folder, local commits) → phase A in `existing` mode, then PHASE R depth 2 on the install branch.
- A `.git` that is not a Pi lineage, or a dirty tree you cannot explain, or `git rev-parse --show-toplevel` not equal to `$ROOT`: STOP and show me.
0.6 S1 only, get Pi (the folder may hold `.keysndocs`, so no `git clone` into it):
~~~powershell
New-Item -ItemType Directory -Force $ROOT | Out-Null
Set-Location $ROOT
git init -b main
git remote add pi-upstream $PI_URL
git remote set-url --push pi-upstream no_push_to_upstream
$def = ((git ls-remote --symref pi-upstream HEAD) | Select-String 'ref: refs/heads/(\S+)\s+HEAD').Matches[0].Groups[1].Value
git fetch pi-upstream $def
git checkout -B main FETCH_HEAD
git tag pi-baseline HEAD
git log --oneline -1
git status --short
~~~
The status must show only `.keysndocs`. A network or fetch failure: STOP.
0.7 S2 and S4 only, compare with upstream (never push; the push URL is disabled):
~~~powershell
if (-not (git remote | Select-String -Pattern '^pi-upstream$' -Quiet)) {
  if (git remote | Select-String -Pattern '^origin$' -Quiet) { if ((git remote get-url origin) -match 'earendil-works/pi') { git remote rename origin pi-upstream } }
}
if (-not (git remote | Select-String -Pattern '^pi-upstream$' -Quiet)) { git remote add pi-upstream $PI_URL }
git remote set-url --push pi-upstream no_push_to_upstream
$def = ((git ls-remote --symref pi-upstream HEAD) | Select-String 'ref: refs/heads/(\S+)\s+HEAD').Matches[0].Groups[1].Value
git fetch pi-upstream $def
git merge-base --is-ancestor HEAD "pi-upstream/$def"; "ancestor-exit=$LASTEXITCODE"
git merge-base HEAD "pi-upstream/$def"
git remote -v
~~~
`ancestor-exit=0` means HEAD is pure Pi (S2). Non-zero means local work exists (S4): the merge-base printed is the last clean Pi commit; no merge-base: STOP and ask me (the fix is `pin_upstream.py --compare-dir` against a fresh clone in `$PROJ\_pi-fresh`). Any other remote you find (mine): leave it, never push. Report what you did to the remotes.

0.8 The GitHub home, `$LOCUS_URL = https://github.com/Shivamxp23/Locus-OS.git` (S1, S2, S3, S4; run it after 0.6 or 0.7, before phase A). My earlier work may already be there (it held about 129 commits when I last looked), so look first and never overwrite it.
~~~powershell
Set-Location $ROOT
$LOCUS_URL = "https://github.com/Shivamxp23/Locus-OS.git"
$has = git remote | Select-String -Pattern '^origin$' -Quiet
if ($has) { $u = git remote get-url origin; if ($u -notmatch '^https://github\.com/Shivamxp23/Locus-OS(\.git)?$') { "origin is $u" ; throw "STOP: origin is not mine" } } else { git remote add origin $LOCUS_URL }
git fetch origin --tags
git ls-remote --heads origin
git rev-list --left-right --count HEAD...origin/main
~~~
If this fails (network, authentication, unknown repository): STOP and tell me; never ask me for a password or token, never put one in a URL. The IDE uses the Git login already on this computer.
- `ls-remote` prints no `main`: the repository is empty; nothing to adopt, the first push (6f) creates `main`.
- `origin/main` exists and the scenario is S1 or S2 (the local tree is pure Pi plus at most `.keysndocs`): the repository on GitHub IS the existing work, so adopt it. Nothing of mine is lost, because a pure Pi `main` can be re-fetched from `pi-upstream`. Steps: if a local `pi-baseline` tag was made by 0.6, delete it (`git tag -d pi-baseline`; phase A1 recomputes it for `existing` mode); copy `.keysndocs` to `$PROJ\_locus-backup-<stamp>\keysndocs-local` and, only if git refuses because untracked files would be overwritten, move the colliding files there too; then `git checkout -B main origin/main`; then copy my local `.keysndocs\Documentation` files back over the checked-out ones, since the local copies are the newest (the spec most of all), and `git status --short` will show them changed; commit those as `docs: sync owner documents` (the spec hash in 6e is taken after this). From here the scenario is S3 or S4 (run 0.5 again from the top) and phase A runs in `existing` mode.
- S3 or S4 and the counts print `<ahead> <behind>`: `0 0` already the same; `0 N` (behind): `git merge --ff-only origin/main` after the tree is clean; `N 0` (ahead): nothing to do, 6f pushes it; both above 0 (diverged): STOP. Do not merge, rebase or force anything. Print `git log --oneline --left-right --max-count=20 HEAD...origin/main` and offer me exactly three options: (a) keep GitHub's version and move my local commits to a branch; (b) keep my local version and push it to a NEW branch `local-rebuild`, leaving `main` as it is; (c) I merge by hand.
What I want when the repository holds old work: it is assessed against the spec and continued, never replaced. The audit in phase R decides what is kept, fixed or rebuilt, and each change is a normal commit.

# PHASE A: install the guardrails (one time; each step says how to tell it is done)
This is a one-time owner exception to rule 4: I authorize exactly these steps. Mode is `greenfield` (S1, S2) or `existing` (S4).
A1. Back up and mark Pi (done when the tag `pi-baseline` exists and `$PROJ\_locus-backup-*` holds `locus-os.bundle`):
~~~powershell
Set-Location $ROOT
$STAMP = Get-Date -Format "yyyyMMdd-HHmm"
$SAFE  = "$PROJ\_locus-backup-$STAMP"
New-Item -ItemType Directory -Force $SAFE | Out-Null
if (-not (git tag --list pi-baseline)) {
  if ($MODE -eq "existing") { git tag pi-baseline (git merge-base HEAD "pi-upstream/$def") } else { git tag pi-baseline HEAD }
}
git bundle create "$SAFE\locus-os.bundle" --all
robocopy "$ROOT\.keysndocs\Documentation" "$SAFE\Documentation" /E /XJ /R:1 /W:1 /NFL /NDL /NJH /NJS
if ($LASTEXITCODE -ge 8) { throw "documentation backup failed" }
if ($MODE -eq "existing") {
  robocopy $ROOT "$SAFE\working-tree" /E /XJ /XD node_modules .venv venv __pycache__ dist build .git /XF .env .env.* /R:1 /W:1 /NFL /NDL /NJH /NJS
  if ($LASTEXITCODE -ge 8) { throw "working-tree backup failed" }
}
Get-ChildItem $SAFE
~~~
(Set `$MODE` to `"greenfield"` or `"existing"` in your shell first. `/XJ` makes robocopy skip junctions so an old `core` junction is never followed; `.env` files are deliberately not copied.) The tag `pi-baseline` is the last clean Pi commit; never move it. Existing mode only: `git switch -c guardrails/install` now, so nothing touches `main` before the audit.
A2. Rules in place (done when `docs\agent\08-task-protocol.md` exists in `$ROOT`):
~~~powershell
New-Item -ItemType Directory -Force "$ROOT\docs\upstream" | Out-Null
foreach ($f in "AGENTS.md","CLAUDE.md","GEMINI.md") { if (Test-Path "$ROOT\$f") { git mv "$f" "docs/upstream/old-$f" } }
robocopy "$SRC" "$ROOT" /E /XD __pycache__ .pytest_cache .cache /R:1 /W:1 /NFL /NDL /NJH /NJS
if ($LASTEXITCODE -ge 8) { throw "bundle copy failed" }
New-Item -ItemType Directory -Force "$ROOT\tracker\.cache" | Out-Null
$ga = "$ROOT\.gitattributes"; if (-not (Test-Path $ga)) { New-Item $ga -ItemType File | Out-Null }
$have = Get-Content $ga
foreach ($l in "*.sh text eol=lf", ".githooks/* text eol=lf", "*.py text eol=lf", "*.toml text eol=lf", "*.yaml text eol=lf", "*.yml text eol=lf") { if ($have -notcontains $l) { Add-Content -Encoding ascii $ga $l } }
$gi = "$ROOT\.gitignore"; if (-not (Test-Path $gi)) { New-Item $gi -ItemType File | Out-Null }
$have = Get-Content $gi
foreach ($l in ".env", ".venv/", "node_modules/", "dist/", "data/couchdb/*", "!data/couchdb/local.ini", "__pycache__/", ".pytest_cache/", ".ruff_cache/", "tracker/.cache/", ".keysndocs/*", "!.keysndocs/Documentation/") { if ($have -notcontains $l) { Add-Content -Encoding ascii $gi $l } }
py -3 -c "import sys; assert sys.version_info >= (3, 11), sys.version; print(sys.version)"
py -3 -m pip install -r tools\requirements.txt
~~~
(`.keysndocs` is named for keys: everything in it except `Documentation` stays out of git.) Python older than 3.11: STOP and tell me to run `winget install -e --id Python.Python.3.12`.
A3. Pin Pi (done when `tools\guard\upstream.lock.json` exists): `py -3 tools\guard\pin_upstream.py --baseline (git rev-parse pi-baseline)`. Greenfield: it must print `Files in ['packages'] that ALREADY differ from the baseline: 0`, any other number: STOP and show me the list. Existing mode: a non-zero number is a FINDING (earlier sessions edited Pi): record the list for the reassessment; do not revert yet.
A4. My documents and secrets: both `Test-Path` below must print `True` (otherwise STOP and tell me where the file really is; do not move my docs), and the scan prints only locations (any line: STOP, give me the locations, never the text; I rotate the key and redact):
~~~powershell
Test-Path "$ROOT\.keysndocs\Documentation\Implementation Plans\LOCUS_FEATURE_LOGIC_DECOMPOSITION.md"
Test-Path "$ROOT\.keysndocs\Documentation\Implementation Plans\Implementation Report\Locus_Implementation_Tracker.xlsx"
Get-ChildItem -Recurse -File "$ROOT\.keysndocs\Documentation" | Select-String -Pattern 'sk-[A-Za-z0-9_-]{20,}','AIza[0-9A-Za-z_-]{30,}','gh[pousr]_[A-Za-z0-9]{30,}','xox[abprs]-[A-Za-z0-9-]{10,}','\b\d{8,10}:[A-Za-z0-9_-]{35}\b','AKIA[0-9A-Z]{16}' | ForEach-Object { "$($_.Path):$($_.LineNumber)" }
~~~
A5. The one-shot setup patch. Write the script of section 11 EXACTLY as is to `tracker\.cache\setup_patch.py`, then run it ONCE with the mode (a second run fails on purpose). It removes the graphify rule, adds law 14 (Pi first, spec exact) to `AGENTS.md` and the Pi check to prompts P1 and P2, records errata D-10 as decided (config lives in `LOCUS_HOME/config.yaml`, the errata recommendation, which I accept), turns every day into a slot day with 4-day sprints of 8 points, sets the top-level baseline to exactly Pi's own entries plus `.keysndocs` and the greenfield files, and in greenfield mode rewrites US-01 into the skeleton story and merges the old US-02 into it. On any mismatch it stops: STOP and show me the message.
~~~powershell
py -3 -I tracker\.cache\setup_patch.py $TODAY $MODE
py -3 tools\tracker\backlog.py --check
~~~
`--check` must print `0 ERROR` (WARN about stories that are not Ready is normal).
A5b. Existing mode only, work adopted from GitHub (0.8): run `py -3 tools\guard\check.py`. For every `layout-top-level` FAIL ("New top-level entry `X` was not accepted") whose name is not one the guard forbids (`core`, `locus`, `locus-os`, a junction, a secret-shaped file, a vault name), add `X` to `allowed_top_level` in `tools\guard\guard.toml`, once, in this setup commit only, each with the comment `# adopted from GitHub work <date>, owner to review`, and list every adopted name in the report. This is my one exception to "guard.toml is mine"; it lets old work be judged by phase R instead of blocking the whole build. Anything the guard forbids stays a finding for phase R: do not allow-list it, do not delete it. If FAILs other than `layout-top-level` remain, they are phase R's fix stories, and the first push (6f) waits only until the guard has 0 FAIL on the branch where you fixed them.
A6. Prove the tools work on this PC:
~~~powershell
py -3 -m pytest -q tests\guard
py -3 tools\guard\check.py --only secrets,gitignore --all
~~~
All tests must pass and `secrets` must print no FAIL, except in existing mode the one expected `couchdb-default-password` (the old default in `docker-compose.yml`; a story removes it). Anything else: STOP and show me the first five lines (secret locations only). If Windows exposes a defect in the tools themselves, report it; never edit the tools to make a test pass.
A7. Commit the install. Hooks stay OFF until the guard is green:
~~~powershell
$env:LOCUS_ALLOW_GUARD_EDIT = "1"
try {
  git add AGENTS.md CLAUDE.md .githooks .github docs tools tracker tests .gitattributes .gitignore
  git commit -m "chore(guardrails): add agent rules, guard, board and evidence tracker"
  git add ".keysndocs/Documentation"
  git commit -m "docs: add the owner's documentation folder"
} finally { Remove-Item Env:LOCUS_ALLOW_GUARD_EDIT -ErrorAction SilentlyContinue }
git update-index --chmod=+x .githooks/pre-commit .githooks/pre-push
git commit -m "chore(guardrails): mark hooks executable" --allow-empty
~~~
Existing mode only, now save the unaudited work as ONE snapshot commit so the board can run (git add -A is allowed here only, after the A4 and A6 scans were clean): `git add -A` then `git commit -m "chore: snapshot of the existing work before the audit (unaudited, may contain defects)"`. Then `git status --short` must print nothing.
A8. First honest measurement:
~~~powershell
py -3 tools\guard\check.py --full --all
py -3 tools\tracker\verify.py --static
py -3 tools\tracker\export_xlsx.py
Get-Content tracker\STATUS.md -TotalCount 12
~~~
Greenfield expected: exactly SIX guard FAILs, all "skeleton missing" (`layout-required` for `sidecar`, `locus-extension`, `locus_cli`, `sidecar/__init__.py`, `docker-compose.yml`, and `must-define` for `sidecar/pi_bridge.py`); anything else: STOP. Existing mode: every FAIL is a real defect with a name; list them. Report the verified average honestly: it will be far below any old claim, because the old numbers had no evidence. The old workbook is copied to `tracker\legacy\replaced-*.xlsx`. Commit: `git add tracker ".keysndocs/Documentation/Implementation Plans/Implementation Report/Locus_Implementation_Tracker.xlsx"` and `git commit -m "chore(tracker): first honest measurement"`.
A9. Existing mode only, audit before anything else: run PHASE R depth 2 now, on the branch `guardrails/install`, including the other family's P0 audit and the fix stories (F1 to F8). When it is complete, commit `tracker\backlog.yaml` (owner variable) and merge: `git switch main`, `git merge --ff-only guardrails/install`, `git branch -d guardrails/install`.
A10. Plan the first sprint (the board must be on `main`, tree clean): read `py -3 tools\tracker\backlog.py --plan`, then
~~~powershell
$env:LOCUS_ALLOW_GUARD_EDIT = "1"
try { py -3 tools\tracker\backlog.py --plan --write } finally { Remove-Item Env:LOCUS_ALLOW_GUARD_EDIT -ErrorAction SilentlyContinue }
git add tracker/sprints.jsonl
git commit -m "docs(agile): sprint plan"
py -3 tools\tracker\backlog.py
~~~
Greenfield: the plan must take US-01 and US-05 (D-10 is decided; the others wait for their dependencies) and the board must say `START US-01`. Say "phase A finished" in one line and give the canary `blue-heron-47` as proof you loaded the new `AGENTS.md`.

# PHASE R: resume and reassess (the guardrails are installed and work exists)
Earlier sessions, other models and I may have written code, handoffs, evidence and claims, and rule files may have been touched. Nothing counts until a command you ran in THIS run says so, including every "done" in the tracker. Report what R finds before you plan anything. Two depths:
- DEPTH 1 on every run that finds progress: R0 to R6.
- DEPTH 2, FULL REASSESSMENT, after depth 1, when I wrote `REASSESS` in the goal, or when no `tracker\handoff\REASSESS-*.md` exists and the tracker shows any story merged or any feature above L2 (always, in existing mode). It re-checks every feature (F1 to F8). New stories wait until it is finished, unless I wrote `SKIP-REASSESS`.
DEPTH 1
R0. Are the rules intact? The bundle in `$AGENTS` is the reference (`$SRC` as in 0.3; the setup commit is the first line of `git log --format=%h --grep="add agent rules" --reverse`). `git diff --no-index --stat "$SRC\tools" tools`, the same for `tests\guard`, `docs\agent`, `.githooks`, `.github\workflows`, and for `AGENTS.md`, `CLAUDE.md`. Expected differences are only those of the setup patch (graphify removal, law 14, P1/P2 Pi check, US-01 skeleton in greenfield mode, D-10, slots, `guard.toml` top-level list) and my own recorded edits (`git log --format="%h %ad %s" -- <human-owned paths>`: each commit says why). Anything else is tampering or drift: list it, do NOT repair it (restoring is mine: `git checkout <commit> -- <file>`). Then: `git config core.hooksPath` (must be `.githooks` once the guard is green), `py -3 -m pytest -q tests\guard`, and print every entry of `tracker\overrides.yaml`, `tracker\spec_exclusions.yaml` and `tracker\signoff.yaml` with its git blame date and author (those three can inflate or hide progress; I check each line). `git diff <setup commit> HEAD -- tracker\features.yaml` must show no deleted or weakened evidence line (add-only): list any.
R1. Git state: `git status --short`, `git branch --show-current`, `git branch --list "task/*"`, `git log --oneline -30`, `git stash list`. A dirty tree or an unknown branch: do not clean it up; list it and follow the board or ask me.
R2. Recompute, never read: `py -3 tools\guard\check.py --full --all` (this compares `packages\` with the pinned Pi baseline), `py -3 tools\tracker\verify.py` (it runs the tests), `py -3 tools\tracker\export_xlsx.py`. Compare `tracker\STATUS.md` with the previous entries of `tracker\history.jsonl`. Every guard FAIL, every feature that went DOWN, every `PROOF_STALE` or `SIGNOFF_STALE`, every difference in `packages\` goes to the top of your report and is fixed before new work (through a story: the board names it, or append a fix story and report it).
R3. For every story at REVIEW or DONE: re-run the test files its handoff names and its demo command; check each `accept` line against the code and output, one by one, and quote the output. A handoff sentence with no matching output is NOT PROVEN.
R4. For every story at DOING, VERIFY or REWORK: do not trust "Files changed": run `git diff --stat main...task/<branch>` and compare. Look for what the guard cannot see: a test with no real assertion, a test or assertion removed or loosened (`git diff main...<branch> -- tests`), `STUB`, `TODO` or `pass` in shipped code, a hard-wired provider, port, path or model, a shim, a second module doing the same job, a reinvention of something Pi has (section 6).
R5. Spec drift: for each feature touched since the last sprint start, `show.py F-xxxx --spec` against what the code does. List every spec sentence not implemented and every behaviour in code that is not in the spec.
R6. Report, short and blunt: proven (with the command), claimed but not proven, broken, and what you would discard (path, why, replaced by, who imports it; you delete nothing before I say "discard rows ..."). If depth 2 does not apply, go on with PHASE C from the board, unless R2 found something that blocks it.
DEPTH 2 (write findings to `tracker\handoff\REASSESS-<date>.md`; first lines `# REASSESS <date> - <your exact model name>` and the commit it ran on; commit the file with the progress table after EACH feature)
F1. Freeze the facts: `git rev-parse HEAD`, the guard summary, the full `verify.py` summary, the count of features per level. Quote them.
F2. Claims against computation: for EVERY feature in `tracker\status.json` list level, flags (`OVERCLAIM`, `VACUOUS_TESTS`, `CLAIMED_FILES_MISSING`, `NO_FILES_NAMED`, `SPEC_CHANGED`, `LOW_CONFIDENCE_MAPPING`, `CAPPED_BY_HUMAN`) and the evidence its level rests on. Order by risk: PROVEN and INTEGRATED first, then UNIT_VERIFIED, then the rest.
F3. Attack the tests, feature by feature in that order. For a feature at L3 or above: read its test file; then `git worktree add tracker\.cache\wt-<F-id> HEAD`, break the feature in THAT copy on purpose (change the one behaviour the spec sentence names), run only that test there, write whether it FAILED (good) or still PASSED (vacuous: say so), then `git worktree remove --force tracker\.cache\wt-<F-id>`. Never mutate the real working tree, never use `git stash`. A test that cannot run in a worktree (missing dependencies, real keys, network): NOT CHECKED with the reason. One table row per feature: feature, test, what you broke, result.
F4. Spec check per feature in F2's order: spec sentences with no code and no test; code with no spec sentence.
F5. Pi-first sweep, once, over the whole repo: every place where Locus re-implements something Pi already provides (agent loop, model or provider layer, session store, tool runner, compaction, TUI, keybindings, settings, extension loading, RPC) with the Pi file that already does it; every feature whose `verdict` is KEEP-PI but has Locus code; every AUGMENT or LOCUS-NEW feature not attached through Pi's extension points.
F6. Whole-repo sweep, once: duplicates (two files doing one job, parallel config systems, two installers, two copies of a prompt or doc), shims and aliases, stubs and fake data in shipped code, hard-wired hosts, ports, paths, models and timezones, `os.environ` or `process.env` outside the config accessor, secret-shaped strings, ports bound to `0.0.0.0`, runtime Pi launches without `--approve --no-context-files`, anything the spec says Locus must not do (a bespoke agent loop, Git or Syncthing sync, edits under `packages\`), vault folder names, and per feature at L2 or above the modularity set (interface, `enabled` switch, off behaviour, swap test, health check). Each finding has file and line.
F7. The other model family: print the clipboard line for me to run it in a Gemini session. Its report is `tracker\handoff\P0-audit-<model>.md`. Where the two reports disagree, the one that quotes a command or a file and line wins.
F8. Turn findings into work, never into inline fixes: every confirmed defect becomes a fix story appended at the bottom of `tracker\backlog.yaml` (feature, slug, points 1 to 3, `accept` lines that quote the failing command, `demo`), named in the report; blockers (guard FAIL, a feature that went down, a secret, an edit under `packages\`) first in your recommendation. A vacuous test is fixed by a new real test added as evidence in a story, never by editing the old one away. A level comes from `verify.py`; if you think a level must be capped, say so and I decide in `tracker\overrides.yaml`. Finish the file with: Summary (10 lines), Facts frozen, Rules integrity, Claims vs computed, Test attack table, Spec gaps, Pi-first findings, Sweep findings, Discard table, Fix stories added, Not checked, Questions for me; features checked out of the total; files you actually opened. Tracker refresh and commit as in section 6d. If features remain unchecked when the run must stop, say how many; the next run continues from the table. When all are checked, say so, and only then go on with PHASE C.

# PHASE B: understand the project and the codebase (read-only; write no file)
Policy: a file up to about 40 KB, whole; a larger one, its headings, first 150 lines, and a search for decisions and requirements. Never read the 8,000-line spec or the whole of `tracker\features.yaml`: use `show.py F-xxxx --spec`. (After phase R, read only what the next story needs.)
1. My docs: list `.keysndocs\Documentation` with sizes, then read `Ideas and System`, `Chat Reports\6_October`, `Chat Reports`, and in `Implementation Plans` everything except the spec. The spec: its `## ` headings and first 150 lines only.
2. The rules: `docs\agent\01`, `02`, `03`, `09` (the index and every OPEN row), `11`, and `08` in full; `04`, `05`, `06`, `07`, `10` when a story touches them (AGENTS.md has the map).
3. Pi, the base I build on: root `README.md`, `packages\coding-agent\README.md`, and in `packages\coding-agent\docs`: `how-pi-works.md`, `extensions.md`, `cli.md`, `rpc.md`, `sdk.md`, `configuration.md`, `security.md`; one line per folder of `packages\*` from its `package.json`. Pi's own dev rules: `docs\upstream\old-AGENTS.md`, reference only.
4. The tracker: `tracker\STATUS.md`, the board, and `show.py` for the features of the stories in the sprint.
Then ONE understanding report, 40 lines at most, every claim tied to a file and line or command output: how Locus sits on Pi (which features are `INHERITED_OK`, what goes in `locus-extension\`, what in `sidecar\`, how a Telegram message travels end to end); the layout now and what is missing; the honest tracker numbers; every contradiction or gap between my docs, the spec, the errata and Pi, and everything in this prompt or the bundle you think is wrong; the first story; the questions you cannot answer yourself.

# PHASE C: build, keep the tracker true, and do not stop until something needs me
## 6a. The loop
The board orders my backlog; each story names its tracker feature; the spec section of that feature defines what to build. Run `py -3 tools\tracker\backlog.py` and do exactly what NEXT ACTION says, by state; after every action run it again; stop only for a reason in section 8. Grill (law 13) for a story: ask me only what the spec, the errata, Pi and the code cannot answer. Nothing to ask: write "No questions" under Plan and go on. A question: ask it with `/grill-me` (one at a time, with your recommended answer) and STOP for my answer; never assume, never code before it.
| Board state | What you do |
|---|---|
| TURN THE HOOKS ON NOW | `git config core.hooksPath .githooks` (once, ever). |
| TODO: START US-nn | `py -3 tools\tracker\backlog.py --start US-nn`; read `tracker\.cache\prompt-US-nn-P1.md` and follow it (you are the author, on `task/US-nn-<slug>`), applying section 6 (Pi first, spec exact) before, during and after. When the Plan and the handoff are written, stop at VERIFY per 6c. |
| DOING | Continue on the same branch: `py -3 tools\tracker\backlog.py --prompt P1 US-nn`. |
| VERIFY | The other model family must check it (6c). Never verify your own story. |
| REWORK | Read `tracker\handoff\US-nn-verify.md`, fix exactly the numbered findings and nothing else; then verify again with a fresh session of the other family. |
| MERGE | Run exactly the commands the board prints, in order; then the tracker commit of 6d. |
| REVIEW | Merged, waiting for me. Do not accept. Go to the next Ready story. |
| REFINEMENT | Section 7b. |
| ANOMALY | Run what the board prints, or stop if it asks for a decision. |
| No story Ready | Section 7b (refine and coverage); if that yields nothing, section 9. |
Pi must be built before any story that runs the real Pi (US-01's tests use a fake Pi executable): `npm ci` then `npm run build` in `$ROOT`, once, when a story's Plan needs it.
## 6c. Verification: Two-Model Manual vs. Autonomous In-Session Mode
- **Manual Dual-Model Mode**: The author and the verifier are different model families in separate IDE conversations. When a story's work is finished: do 6d, commit on `task/US-nn-<slug>`, write `tracker\handoff\US-nn.md`, run `py -3 tools\tracker\backlog.py` so it shows VERIFY, then STOP and print the manual verification instructions.
- **Autonomous Mode (under `/goal`)**: You are authorized to conduct verification autonomously without halting the run. After authoring and committing on `task/US-nn-<slug>` and generating `US-nn-spec-trace.md`, switch to a clean isolated worktree (`git worktree add tracker\.cache\wt-verify HEAD`), run prompt P2's verification suite, the test-mutation check from F3, and verify at least 5 spec rows. Write `tracker\handoff\US-nn-verify.md`. If PASS, proceed directly to MERGE per the board's instructions, clean up the worktree, refresh the tracker, and advance to the next Ready story.
Before merging or printing, check these (names only): `git ls-files -co | Where-Object { $_ -notmatch '(^|/)node_modules/' -and $_ -match '(^|/)(\.env(\.local|\.prod|\.production)?|credentials[^/]*|secrets?\.[^/]*)$|\.(pem|key)$' }` prints nothing, and `git status --short` prints nothing. If a secret-shaped file is inside `.keysndocs`, tell me to move it to `%USERPROFILE%\.locus\`.
## 6f. Publishing to GitHub (`origin`, `Shivamxp23/Locus-OS`): every commit gets pushed
Committing without pushing is not done. After the commits below, push to `origin`, in this form only, with an explicit branch name (`main` or the story's `task/US-nn-<slug>`):
~~~powershell
git push origin <branch>
~~~
Push points: (1) after the phase A setup commits, once the guard has 0 FAIL; (2) after every commit that ends a story's author work (the branch, so I and the verifier can see it); (3) after the verifier's file is committed; (4) after every merge to `main`; (5) after every tracker refresh commit; (6) before any stop, the last thing you do. If `git status --short` shows nothing and `git rev-list --count origin/<branch>..HEAD` is 0, there is nothing to push.
Before each push: `py -3 tools\tracker\backlog.py --check` prints `0 ERROR`; `py -3 tools\guard\check.py` has 0 FAIL; the secrets check of 6c prints nothing; `git status --short` is empty. The `pre-push` hook runs the full guard itself, so a long push is normal; if it fails, fix what it names and push again, never `--no-verify`.
If a push is rejected (not a fast-forward, a protected branch, authentication, network): STOP and show me the one line git printed. Never force, never rebase published commits, never reset. First push of a new branch is `git push -u origin <branch>`.
What goes public: the repository is public, so only what the guard accepts is committed, `.env` and keys never, and `.keysndocs\Documentation` is already tracked there by my choice. After a merge, do not delete task branches on GitHub; I do that.
## 6e. Spec conformance to the letter (a gate on every story, plus a sweep)
Rule 6 says "follow the spec"; this section is how it is proven, so nothing is left to your judgment.
1. Pin the spec: once, in phase 0, run `Get-FileHash -Algorithm SHA256 ".keysndocs\Documentation\Implementation Plans\LOCUS_FEATURE_LOGIC_DECOMPOSITION.md"` and write the hash to `tracker\handoff\spec.sha256` (commit it). At every `--start`, compare. If it differs, STOP: the spec changed and only I decide what that means. Never edit the spec.
2. Trace file: per story write `tracker\handoff\US-nn-spec-trace.md` BEFORE the first line of code, from `py -3 tools\tracker\show.py F-xxxx --spec` for every feature the story names. One row per spec sentence that states behaviour (do, must, never, default, limit, off-state, error, number, name, path, flag, order of steps): spec line | the sentence quoted word for word | verdict (KEEP-PI / AUGMENT / LOCUS-NEW) | the Pi mechanism or `locus-extension\` / `sidecar\` file:line that carries it | test name or NOT YET. Names, numbers, paths, defaults, flags and orders are copied exactly as the spec writes them; if you must differ (the spec's HOW does not match Pi, or the D-6 path mapping applies), the row says so and why.
3. Close it before the story leaves your hands: every row has a test that passed (command output pasted in the handoff) or a reason I can read, such as "Pi already does this" with the Pi file:line, or "blocked by OPEN decision D-n". A row left NOT YET with no reason means the story is not done; never move it to VERIFY.
4. Scope check, the other direction: `git diff main...HEAD --stat` must contain nothing the trace does not explain. A file, option, command or behaviour that no spec row asks for is removed, or it is a question to me. Never add a feature "because it would be nice". The same goes for anything the spec says Locus must NOT do.
5. The verifier (6c) gets the trace, picks at least five rows at random plus every row marked as a difference, and re-checks each against the spec text and the code; it also reads the scope check. Any row that the code does not satisfy is REWORK.
6. Conformance sweep: after every third story reaches DONE or REVIEW, and whenever the board announces a sprint end, take every feature at L2 or above that was built since the last sweep and re-read its spec section against the current code and tests. Write `tracker\handoff\sweep-<date>.md` with one line per feature: conforms, or the spec sentence it violates with file and line. Violations become a REWORK story (state them to the board by the normal story path), never a silent edit. Run `py -3 tools\tracker\verify.py` afterwards so the levels fall if the evidence did.
7. Whole-spec closing check, before section 9: for every spec section, count the behaviour sentences and the trace rows that cover them across all handoffs; any section where a sentence has no row is uncovered work, and goes to section 7b as a new story. Only when that count is clean may you print `AUTOMATABLE WORK EXHAUSTED`.
## 6d. Tracker autonomy: you keep it true, I never type in it
- While building: add test evidence for the feature to `tracker\features.yaml` (add only; never delete or weaken a line).
- At the end of every story, every merge and before every stop:
~~~powershell
py -3 tools\tracker\verify.py --only F-xxxx
py -3 tools\tracker\verify.py
py -3 tools\tracker\export_xlsx.py
git add tracker ".keysndocs/Documentation/Implementation Plans/Implementation Report/Locus_Implementation_Tracker.xlsx"
git commit -m "chore(tracker): refresh after US-nn"
~~~
(on a story branch these run before the handoff; after a merge, on `main`). After each of these commits, push per 6f. A feature that went DOWN (`REGRESSION`) or a guard FAIL: stop and report it first.
- Each handoff (`tracker\handoff\US-nn.md`, all nine headings, first line `# US-nn handoff - <exact model name>, <date>`) holds real command output; a statement without output is marked `NOT RUN`. The workbook is generated and tamper-hashed; it is how I see progress and is never edited.

# 10. The report that ends every run, then the grill
In this order, short:
1. The tracker quoted from `tracker\STATUS.md` (verified average, features per level, what moved and why) and the workbook path; `coverage.py` summary line.
2. The board's state for each story in the sprint (the board's words).
3. What I must do now, as exact pasteable commands, for example `$env:LOCUS_ALLOW_GUARD_EDIT="1"; py -3 tools\tracker\backlog.py --accept US-01 --note "what I saw"; Remove-Item Env:LOCUS_ALLOW_GUARD_EDIT`, with the demo text of each story waiting for acceptance.
4. What you did under a delegation, what you decided, what you disagree with, what is NOT CHECKED.
5. Then `/grill-me` on me, one question at a time, each with your recommended answer and why: first what blocks the next story; then the four-pillar decisions D-1, D-3, D-4, D-5, then D-13, D-15, D-16, D-9, with the options written in `docs\agent\09-spec-errata.md`. Edit a row's status only after I write the word "decided", and commit it with the owner variable. Nothing to ask: say "No questions".

# 11. Scripts (write each file exactly as is, once)
`tracker\.cache\setup_patch.py` (phase A5):
~~~python
"""One-shot owner-authorized setup patch. Run once from the repo root:  py -3 -I tracker/.cache/setup_patch.py <YYYY-MM-DD> <greenfield|existing>
greenfield = the repo is Pi and nothing else; existing = Locus code already exists and keeps its backlog stories.
Every replacement asserts it matched exactly once; on any mismatch it stops with an error and changes nothing further."""
import pathlib
import re
import sys

if len(sys.argv) != 3 or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", sys.argv[1]) or sys.argv[2] not in ("greenfield", "existing"):
    sys.exit("usage: setup_patch.py YYYY-MM-DD greenfield|existing   (today = the first sprint start)")
TODAY = sys.argv[1]
MODE = sys.argv[2]
ROOT = pathlib.Path(".")


def load(path):
    raw = (ROOT / path).read_bytes().decode("utf-8")
    nl = "\r\n" if "\r\n" in raw else "\n"
    return raw.replace("\r\n", "\n"), nl


def save(path, text, nl):
    (ROOT / path).write_bytes(text.replace("\n", nl).encode("utf-8"))


def sub(path, old, new):
    text, nl = load(path)
    n = text.count(old)
    if n != 1:
        sys.exit(f"PATCH FAILED: {path}: expected 1 match, found {n} for: {old[:70]!r}")
    save(path, text.replace(old, new), nl)
    print(f"ok  {path}: {old[:50]!r}")


# 1. Remove the /graphify condition everywhere it is a rule (the owner withdrew it).
sub("AGENTS.md",
    "4. `/graphify update .` in `5_Locus` and again in `5_Locus/locus-os` (the human's standing rule).\n5. Write `tracker/handoff/US-nn.md`",
    "4. Write `tracker/handoff/US-nn.md`")
sub("docs/agent/08-task-protocol.md",
    "9. **Graph.** `/graphify update .` in `5_Locus`, then again in `5_Locus/locus-os` (the owner's standing rule).\n10. **Handoff and stop.**",
    "9. **Handoff and stop.**")
sub("docs/agent/08-task-protocol.md", "After step 10 a fresh session", "After step 9 a fresh session")
sub("docs/agent/prompts/P1-implement-feature.md",
    ", then `/graphify update .` in `5_Locus` and\n  again in `5_Locus/locus-os`. Write `tracker/handoff/",
    ". Write `tracker/handoff/")
sub("docs/agent/prompts/P1-implement-feature.md", "from step 5 (Plan) to step 10 (Handoff)", "from step 5 (Plan) to step 9 (Handoff)")
sub("docs/agent/prompts/P6-autopilot-author.md",
    "6. `/graphify update .` is an interactive command that may not exist in this session. Run its command-line form if the machine has one. If you\n"
    "   cannot run it, write `graphify: NOT RUN (autopilot)` under \"Commands run\" in your handoff; the owner runs it before the demo. Never write that it ran when it did not.\n"
    "7. Commit on this branch",
    "6. Commit on this branch")

# 2. Greenfield only: US-01 becomes the skeleton (absorbing the Pi launcher); US-02 is removed; dependencies follow.
NEW_US01 = '''  - id: US-01
    epic: E1
    feature: F-0084
    slug: green-skeleton
    title: "Greenfield skeleton: the one layout (sidecar, locus-extension, locus_cli, docker-compose.yml) plus the Pi launcher, guard 0 FAIL"
    points: 3
    target_level: 3
    accept:
      - "py -3 tools/guard/check.py --full prints 0 FAIL. The guard's layout-required, must-define and pi-bridge-flags checks pass; nothing else in the repo changes outside the files this story creates."
      - "Created, each with real content and no stub: sidecar/__init__.py; sidecar/pi_bridge.py that DEFINES run_pi_turn and get_node_executable; locus-extension/ with a package.json and a src/ folder; locus_cli/__init__.py; a docker-compose.yml that parses as valid YAML (services may be empty: CouchDB arrives in US-03). Nothing under packages/ changes."
      - "run_pi_turn builds the Pi command line itself and always includes --approve and --no-context-files, and runs Pi with the repo root as working folder. A unit test with a fake Pi executable asserts exactly that; the string --dangerously-skip-permissions appears nowhere in the repo."
      - "A unit test asserts importlib.util.find_spec('core') is None and that no top-level folder named core, locus, locus-os or src exists. The handoff records the Pi release commit (tools/guard/upstream.lock.json baseline) it was built on."
    demo: 'Run py -3 tools\\guard\\check.py --full: it prints 0 FAIL. Look at the top level of locus-os: packages, sidecar, locus-extension, locus_cli and docker-compose.yml are there, and there is no core folder. Run the fake-Pi test file named in the handoff with py -3 -m pytest -q <that file>: it prints passed.'

'''
if MODE == "greenfield":
    text, nl = load("tracker/backlog.yaml")
    m = re.search(r"  - id: US-01\n.*?(?=  - id: US-03\n)", text, flags=re.S)
    if not m or "  - id: US-02\n" not in m.group(0):
        sys.exit("PATCH FAILED: tracker/backlog.yaml: could not find the US-01/US-02 blocks")
    text = text[:m.start()] + NEW_US01 + text[m.end():]
    save("tracker/backlog.yaml", text, nl)
    print("ok  tracker/backlog.yaml: US-01 replaced by the greenfield skeleton, US-02 removed")
    sub("tracker/backlog.yaml", "    depends_on: [US-02, US-04, US-06]\n", "    depends_on: [US-01, US-04, US-06]\n")
    text, nl = load("tracker/backlog.yaml")
    if text.count("    depends_on: [US-02, US-06]\n") != 2:
        sys.exit("PATCH FAILED: tracker/backlog.yaml: expected 2 stories with depends_on [US-02, US-06]")
    save("tracker/backlog.yaml", text.replace("    depends_on: [US-02, US-06]\n", "    depends_on: [US-01, US-06]\n"), nl)
    print("ok  tracker/backlog.yaml: two dependents moved from US-02 to US-01")
    # US-03 and US-04 need the skeleton to exist first.
    sub("tracker/backlog.yaml",
        '    title: "CouchDB password comes from .env and every port binds to 127.0.0.1 (S-2)"\n    points: 1\n    target_level: 3\n    addendum: [P4]\n',
        '    title: "CouchDB password comes from .env and every port binds to 127.0.0.1 (S-2)"\n    points: 1\n    target_level: 3\n    addendum: [P4]\n    depends_on: [US-01]\n')
    sub("tracker/backlog.yaml",
        '      - "The handoff says how an already-initialised data directory gets the new admin password (CouchDB applies COUCHDB_PASSWORD only when it creates the admin, so an existing data folder keeps the old one) and gives the exact commands; after them the previous login is rejected."\n',
        '      - "Greenfield: no data directory exists yet. The handoff still gives the exact commands for rotating the admin password on a data directory that already exists (CouchDB applies COUCHDB_PASSWORD only when it creates the admin), and says that a first install needs none."\n')
    sub("tracker/backlog.yaml",
        '    title: "Telegram pairing: one-time code, fail closed, nobody becomes owner by messaging first (S-1)"\n    points: 2\n    target_level: 3\n    addendum: [P4]\n    accept:\n',
        '    title: "Telegram pairing: one-time code, fail closed, nobody becomes owner by messaging first (S-1)"\n    points: 3\n    target_level: 3\n    addendum: [P4]\n    depends_on: [US-01]\n    accept:\n'
        '      - "Greenfield: no Telegram gateway exists yet, so this story builds the smallest real one (long polling, token read through the secrets rules, only at the path `python tools/tracker/show.py F-0083` names) and the pairing in front of it. The six tests run against a fake Telegram transport. If this proves too big for 3 points, stop and say so: refinement splits it."\n')

# 2b. Pi first, spec exact: law 14 for every agent (AGENTS.md is read on every turn), plus the author and verifier prompts.
LAW14 = ("14. **Pi first, spec exact.** Before code for a feature read its verdict (`python tools/tracker/show.py F-xxxx`): KEEP-PI = write no code; "
         "AUGMENT = extend what Pi already has, through `locus-extension/` (Pi extension API, hooks, tools, SDK, RPC) or `sidecar/`; LOCUS-NEW = still attach through Pi's extension points; "
         "UNKNOWN = stop and ask. Never write a second agent loop, model/provider layer, session store, tool runner, compaction, TUI, keybinding or settings system that Pi already has: "
         "search `packages/` and `packages/coding-agent/docs` first. Your handoff Plan holds a Pi table: need | Pi mechanism (file:line) | what Locus adds | why Pi's is not enough. "
         "Every test docstring starts `SPEC <section> line <n>: \"<spec sentence>\"`.\n")
text, nl = load("AGENTS.md")
m = re.search(r"^13\. \*\*Grill before you build\.\*\*.*\n", text, flags=re.M)
if not m:
    sys.exit("PATCH FAILED: AGENTS.md: law 13 line not found")
save("AGENTS.md", text[:m.end()] + LAW14 + text[m.end():], nl)
print("ok  AGENTS.md: law 14 (Pi first, spec exact)")
sub("docs/agent/prompts/P1-implement-feature.md",
    "- Build it modular: interface, config switch, off behaviour, a swap test (docs/agent/03-modularity.md).\n",
    "- Build it modular: interface, config switch, off behaviour, a swap test (docs/agent/03-modularity.md).\n"
    "- Pi first (AGENTS.md law 14): write the Pi table under Plan before any code (need | Pi mechanism with file:line | what Locus adds | why Pi's is not enough). "
    "The first docstring line of every test is `SPEC <section> line <n>: \"<spec sentence>\"`.\n")
sub("docs/agent/prompts/P2-independent-verify.md",
    "Write `tracker/handoff/{{STORY}}-verify.md`. Its FIRST line",
    "8. Pi first (AGENTS.md law 14): open every file:line in the handoff's Pi table and confirm it exists and does what the table says. Search the diff and the new files "
    "for anything that re-implements what Pi already provides (agent loop, model or provider layer, session store, tool runner, compaction, TUI, keybindings, settings) and for any change "
    "that ignores the feature's verdict (KEEP-PI means no code). Any such finding makes the verdict REJECT. Also check that every test docstring starts with a `SPEC <section> line <n>:` quote "
    "and that the quoted sentence is really in the spec and is what the test asserts.\n\n"
    "Write `tracker/handoff/{{STORY}}-verify.md`. Its FIRST line")

# 3. Decisions D-1, D-3, D-4, D-5, D-10: the owner decided them (the recommendations in the errata file).
sub("docs/agent/09-spec-errata.md", "| D-1 | OPEN | Which task-priority formula (TWS) is real |", "| D-1 | DECIDED | Which task-priority formula (TWS) is real |")
sub("docs/agent/09-spec-errata.md", "**D-1 Task priority formula (OPEN).**", f"**D-1 Task priority formula (DECIDED by the owner on {TODAY}: Option A, the recommendation below).**")
sub("docs/agent/09-spec-errata.md", '| D-3 | OPEN | What "scale" means for per-task priority |', '| D-3 | DECIDED | What "scale" means for per-task priority |')
sub("docs/agent/09-spec-errata.md", '**D-3 "Scale" (OPEN).**', f'**D-3 "Scale" (DECIDED by the owner on {TODAY}: Option a, the recommendation below).**')
sub("docs/agent/09-spec-errata.md", "| D-4 | OPEN | How far auditability goes |", "| D-4 | DECIDED | How far auditability goes |")
sub("docs/agent/09-spec-errata.md", "**D-4 Auditability (OPEN).**", f"**D-4 Auditability (DECIDED by the owner on {TODAY}: Option b, the recommendation below).**")
sub("docs/agent/09-spec-errata.md", '| D-5 | OPEN | What "meta-harness" means in code |', '| D-5 | DECIDED | What "meta-harness" means in code |')
sub("docs/agent/09-spec-errata.md", '**D-5 Meta-harness (OPEN).**', f'**D-5 Meta-harness (DECIDED by the owner on {TODAY}: Option a, the recommendation below).**')
sub("docs/agent/09-spec-errata.md", "| D-10 | OPEN | Where the `locus.*` config tree is stored |", "| D-10 | DECIDED | Where the `locus.*` config tree is stored |")
sub("docs/agent/09-spec-errata.md", "**D-10 Config location (OPEN).**",
    f"**D-10 Config location (DECIDED by the owner on {TODAY}: the recommendation below, unchanged).**")

# 4. Daily slots, one-week sprints, capacity for the greenfield start. The owner still runs acceptance, retro and sprint close.
sub("tracker/backlog.yaml", "  first_sprint_start: 2026-10-16", f"  first_sprint_start: {TODAY}")
sub("tracker/backlog.yaml", "  sprint_days: 14", "  sprint_days: 4")
sub("tracker/backlog.yaml", "  slot_days: [Mon, Tue, Fri]", "  slot_days: [Mon, Tue, Wed, Thu, Fri, Sat, Sun]")
sub("tracker/backlog.yaml", "  capacity_points: 4 ", "  capacity_points: 8 ")

# 5. Top-level baseline = exactly what Pi itself ships (the pi-baseline tag) + .keysndocs + the greenfield files the layout needs.
#    Anything else at the top level stays unadopted, so the guard FAILs it and it becomes a fix story.
import subprocess
import tomllib
r = subprocess.run(["git", "ls-tree", "--name-only", "-z", "pi-baseline"], capture_output=True, text=True, encoding="utf-8")
if r.returncode != 0 or not r.stdout:
    sys.exit("PATCH FAILED: tag pi-baseline missing or empty: " + r.stderr)
have = [x for x in r.stdout.split("\0") if x]
for extra in (".keysndocs", ".dockerignore", ".env.example", ".pytest_cache", ".ruff_cache", ".venv", "__pycache__", "data", "docker-compose.yml", "node_modules", "pyproject.toml", "vault"):
    if extra not in have:
        have.append(extra)
text, nl = load("tools/guard/guard.toml")
m = re.search(r"^allowed_top_level = \[.*?\]\s*$", text, flags=re.M)
if not m:
    sys.exit("PATCH FAILED: tools/guard/guard.toml has no allowed_top_level line")
text = text[:m.start()] + "allowed_top_level = [" + ", ".join('"%s"' % x for x in sorted(have)) + "]" + text[m.end():]
save("tools/guard/guard.toml", text, nl)
assert "docker-compose.yml" in tomllib.loads(text)["layout"]["allowed_top_level"]
print("ok  tools/guard/guard.toml: top-level baseline = Pi's own entries + .keysndocs + greenfield files")
print("SETUP PATCH COMPLETE")
~~~
`tracker\.cache\coverage.py` (section 7b; reads only, run as `py -3 -I tracker\.cache\coverage.py`):
~~~python
"""Which tracker features have no story yet? Run from the repo root:  py -3 -I tracker/.cache/coverage.py   (reads, never writes)"""
import json
import pathlib
import sys
import yaml

root = pathlib.Path(".")
feats = yaml.safe_load((root / "tracker/features.yaml").read_text(encoding="utf-8"))["features"]
stories = yaml.safe_load((root / "tracker/backlog.yaml").read_text(encoding="utf-8")).get("stories") or []
sp = root / "tracker/status.json"
status = json.loads(sp.read_text(encoding="utf-8"))["features"] if sp.is_file() else {}
covered = {s.get("feature") for s in stories}
rows = []
for f in feats:
    if f.get("inherited"):
        continue
    lab = (status.get(f["id"]) or {}).get("label", "?")
    if f["id"] not in covered and lab not in ("PROVEN", "INHERITED_OK"):
        rows.append(tuple(str(x or "") for x in (f.get("category"), f["id"], f.get("verdict"), f.get("layer"), lab, f.get("title"))))
rows.sort()
print(f"features {len(feats)} | with a story {len(covered)} | WITHOUT a story and not finished {len(rows)}")
cat = None
for r in rows:
    if r[0] != cat:
        cat = r[0]
        print(f"\n[{cat}]")
    print(f"  {r[1]}  {r[2]:<14} {r[3]:<9} {r[4]:<14} {r[5]}")
sys.exit(0)
~~~

Start now with phase 0. Your first line: your exact model name, and "phase 0".
