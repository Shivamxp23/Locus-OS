# RUNBOOK: Sprint 0 (two evenings), then one sprint after another. No decisions needed.

How this works. Locus is built in sprints of 14 days (Scrum-shaped; the full rules are `docs\agent\11-agile-workflow.md`). You are the
Product Owner; Claude writes, Gemini checks, and a script (`tools\tracker\backlog.py`, "the board") works out where every story stands
from git and files, then prints the one thing to do next. Two parts:
1. **Sprint 0** (Mon 12 Oct and Tue 13 Oct, 19:30): setup and safety. You do it from this file, in order. Nothing is built.
2. **Every evening from Fri 16 Oct**: paste the variables, run the board, do exactly what NEXT ACTION says. The later sections of this
   file only explain what the board will print, so nothing surprises you.
3. **Optional, from Sprint 2**: the autopilot lets Antigravity run the sprint's stories while you are away and stops at the first thing that
   needs you (last section: AUTOPILOT). It cannot finish the project by itself, and it is not for Sprint 1.

Everything runs in Windows PowerShell. STOP rule: if a command prints `fatal:`, `error:` or red text, stop at that step, copy the whole
output into a new Claude session and say "RUNBOOK step <number> failed". I only had Linux (tests pass on Python 3.11 and 3.13): the
PowerShell lines are written for your folders but were never run on Windows. Python commands use `py -3`.

Assumptions I made (wrong? change `config:` at the top of `tracker\backlog.yaml`, then commit it as in step 4 of Sprint 0 slot 2):
your Locus evenings are Mon, Tue and Fri at 19:30; a sprint is 14 days; one story at a time; capacity 4 points per sprint at first;
the first sprint starts Fri 16 Oct. A missed evening is not made up: the next one starts with the board.

Variables (paste at the start of every PowerShell window, every evening):
~~~powershell
$ErrorActionPreference = "Stop"
$ROOT   = "C:\Users\soni8\Desktop\everything\University 2.0\Project(s)\5_Locus\locus-os"
$BUNDLE = "$env:USERPROFILE\Downloads\locus-guardrails"
$STAMP  = Get-Date -Format "yyyyMMdd-HHmm"
$SAFE   = "C:\Users\soni8\Desktop\everything\University 2.0\Project(s)\5_Locus\_locus-backup-$STAMP"
Set-Location $ROOT
~~~

## Your calendar
| When | Sprint | What |
|---|---|---|
| Mon 12 Oct 19:30 | 0 | Slot 1, about 75 min: contain, back up, install, measure |
| Tue 13 Oct 19:30 | 0 | Slot 2, about 100 min: two audits, backlog, merge |
| Fri 16 Oct 19:30 | 1 | PLANNING (30 min), then the first story |
| Mon 19, Tue 20, Fri 23 Oct | 1 | Board (2 min), then story work |
| Mon 26 Oct | 1 | REFINEMENT (30 min), then story work |
| Tue 27 Oct | 1 | REVIEW + RETRO (45 min), `--close-sprint`. Sprint 1 ends Thu 29 Oct |
| Fri 30 Oct, Mon 2, Tue 3, Fri 6, Mon 9, Tue 10 Nov | 2 | the same six slots; planning Fri 30 Oct, review Tue 10 Nov |
| Fri 13 Nov, Mon 16, Tue 17, Fri 20, Mon 23, Tue 24 Nov | 3 | the same six slots; planning Fri 13 Nov, review Tue 24 Nov |
`py -3 tools\tracker\backlog.py --calendar` prints every later date.

---------------------------------------------------------------------------------------------------------------------

# SPRINT 0, slot 1: Mon 12 Oct 19:30 (about 75 minutes)

## 1. Freeze (2 min)
Close Antigravity and every Claude/Gemini session. Nothing may write while you copy. Open ONE PowerShell window and paste the variables.
Do not paste them again during this slot (`$STAMP` would change and `$SAFE` with it).

## 2. Where you are (1 min)
~~~powershell
git branch --show-current
~~~
Prints `main`: go on. Prints `master`: run `git branch -m main`, then go on. Anything else: STOP ("RUNBOOK step 2 failed").

## 3. Contain the known holes (15 min). Do all three now, without checking whether they "really" happened
Reason: until the pairing fix ships (story US-04) the first person who messages your bot becomes its owner, and until US-03 ships
CouchDB listens on every network interface with a default password. Rotating costs nothing; a leaked key costs a lot.
a. Telegram: in the Telegram app open @BotFather, send `/revoke`, choose your Locus bot. It prints a NEW token. Put the new token only in
   `$env:USERPROFILE\.locus\.env`. The old token is dead from this moment.
b. Docker, on this PC and then on the VM (log in to the VM the way you always do):
~~~powershell
docker ps --format "{{.Names}}  {{.Ports}}"
~~~
   For every line that shows `0.0.0.0:5984` run `docker stop <that name>`. An empty list, or a docker error such as "cannot connect",
   means nothing is running: done. Do NOT run `docker compose down -v` (the `-v` deletes your data).
c. Keys: open the dashboard of every provider Locus uses (Groq, and any other LLM provider). Revoke every key that was EVER pasted into a
   chat, a report, a file inside `locus-os`, or the old tracker, and create a new one. Not sure whether a key was pasted somewhere?
   Rotate it. New keys go only into `$env:USERPROFILE\.locus\.env`: never into the repo, a prompt, a log, a commit or a chat.
Until the board shows US-03 and US-04 as DONE: do not start the old Telegram bot and do not run `docker compose up`.

## 4. Back up (10 min). Your code and your tracker end up in three independent places
~~~powershell
Set-Location $ROOT
New-Item -ItemType Directory -Force $SAFE | Out-Null
git tag "backup/pre-guardrails-$STAMP"
git bundle create "$SAFE\locus-os.bundle" --all
robocopy $ROOT "$SAFE\working-tree" /E /XJ /XD node_modules .venv venv __pycache__ dist build .git /XF .env .env.* /R:1 /W:1 /NFL /NDL /NJH /NJS
if ($LASTEXITCODE -ge 8) { throw "robocopy failed" }
Copy-Item "$ROOT\.keysndocs\Documentation\Implementation Plans\Implementation Report\Locus_Implementation_Tracker.xlsx" "$SAFE\Locus_Implementation_Tracker.ORIGINAL.xlsx"
Get-ChildItem $SAFE
~~~
`/XJ` makes robocopy skip junctions, so the old `core` junction is never followed. `.env` files are deliberately NOT copied (secrets).
STOP unless the listing shows `locus-os.bundle`, `working-tree`, and `Locus_Implementation_Tracker.ORIGINAL.xlsx`.

## 5. Install the guardrails (15 min)
~~~powershell
Expand-Archive -Path "$env:USERPROFILE\Downloads\locus-guardrails.zip" -DestinationPath "$env:USERPROFILE\Downloads" -Force
Set-Location $ROOT
New-Item -ItemType Directory -Force "$ROOT\docs\upstream" | Out-Null
foreach ($f in "AGENTS.md","CLAUDE.md","GEMINI.md") { if (Test-Path "$ROOT\$f") { Move-Item "$ROOT\$f" "$ROOT\docs\upstream\old-$f" } }
robocopy "$BUNDLE\repo" $ROOT /E /R:1 /W:1 /NFL /NDL /NJH /NJS
if ($LASTEXITCODE -ge 8) { throw "copy failed" }
$ga = "$ROOT\.gitattributes"
if (-not (Test-Path $ga)) { New-Item $ga -ItemType File | Out-Null }
$have = Get-Content $ga
foreach ($l in "*.sh text eol=lf", ".githooks/* text eol=lf", "*.py text eol=lf", "*.toml text eol=lf", "*.yaml text eol=lf", "*.yml text eol=lf") { if ($have -notcontains $l) { Add-Content -Encoding ascii $ga $l } }
py -3 -c "import sys; assert sys.version_info >= (3, 11), sys.version; print(sys.version)"
~~~
If the last line prints an `AssertionError`: run `winget install -e --id Python.Python.3.12`, close PowerShell, open a new one, paste the
variables again, and run only that last line again. Then:
~~~powershell
py -3 -m pip install -r tools\requirements.txt
~~~
Already installed an OLDER zip (one without `tools\tracker\autopilot.py`)? Do not repeat this step. Do only this, once. It copies the new files and leaves your
whole `tracker\` folder (measurements, backlog, sign-offs) untouched:
~~~powershell
Set-Location $ROOT
git status --short
git branch --show-current
~~~
`git status --short` must print nothing; the branch must be `guardrails/install` or `main`. Then:
~~~powershell
Expand-Archive -Path "$env:USERPROFILE\Downloads\locus-guardrails.zip" -DestinationPath "$env:USERPROFILE\Downloads" -Force
robocopy "$BUNDLE\repo" $ROOT /E /R:1 /W:1 /NFL /NDL /NJH /NJS /XD "$BUNDLE\repo\tracker"
if ($LASTEXITCODE -ge 8) { throw "copy failed" }
$env:LOCUS_ALLOW_GUARD_EDIT = "1"
git add AGENTS.md CLAUDE.md docs tools tests .githooks .github
git commit -m "chore(guardrails): update to the autopilot edition"
Remove-Item Env:LOCUS_ALLOW_GUARD_EDIT
py -3 -m pip install -r tools\requirements.txt
~~~

## 6. Make the working tree clean, safely (10 min)
The board refuses to start a story on a dirty tree, so everything you have today is saved as ONE snapshot commit on a new branch. First
the safety scan: it checks exactly the files `git add -A` is about to take.
~~~powershell
git switch -c guardrails/install
$gi = "$ROOT\.gitignore"
if (-not (Test-Path $gi)) { New-Item $gi -ItemType File | Out-Null }
$have = Get-Content $gi
foreach ($l in ".env", ".venv/", "node_modules/", "dist/", "data/couchdb/*", "!data/couchdb/local.ini", "__pycache__/", "tracker/.cache/", ".keysndocs/*", "!.keysndocs/Documentation/") { if ($have -notcontains $l) { Add-Content -Encoding ascii $gi $l } }
py -3 tools\guard\check.py --only secrets,gitignore --all
~~~
(`.keysndocs` is named for keys and docs, so everything in it except `Documentation` stays out of git.)
Read the output. It must show no `secrets` FAIL except one kind: a FAIL that names `couchdb-default-password` is EXPECTED (it is the old
default in `docker-compose.yml`; story US-03 removes it): ignore that one only. Any other secrets FAIL: STOP. Open the file named in it,
delete the key text, rotate that key at its provider (the old one counts as leaked), save, and run the last line again until only the
expected one is left. Then:
~~~powershell
git add AGENTS.md CLAUDE.md .githooks .github/workflows/guard.yml tools tracker tests/guard docs/agent .gitattributes .gitignore
if (Get-ChildItem docs\upstream -File -ErrorAction SilentlyContinue) { git add docs/upstream }
git commit -m "chore(guardrails): add agent rules, guard, board and evidence tracker"
git add -A
git commit -m "chore: snapshot of the working tree before the audit (unaudited, may contain defects)"
git update-index --chmod=+x .githooks/pre-commit .githooks/pre-push
git commit -m "chore(guardrails): mark hooks executable" --allow-empty
git status --short
~~~
The last line should print nothing. The hooks are NOT switched on: the board tells you when (after the guard shows 0 FAIL).

## 7. First honest measurement (10 min)
~~~powershell
py -3 tools\guard\pin_upstream.py
py -3 tools\guard\check.py --full --all
py -3 tools\tracker\verify.py --static
py -3 tools\tracker\export_xlsx.py
Get-Content tracker\STATUS.md -TotalCount 12
~~~
What you will see, and what it means:
- `pin_upstream` prints how many files in `packages\` differ from the last clean Pi commit. Not 0 = earlier sessions edited Pi. Do nothing yet.
  If it prints WARNING or an error, copy the text: you give it to the audit tomorrow.
- The guard prints FAIL lines. Expect several (for example a `core` folder, a junction, a missing `--approve --no-context-files`, the
  CouchDB default password). That is the point: each FAIL is a real defect with a name, and Sprint 1 removes them.
- `STATUS.md` shows the verified average. It will be FAR below the old 71.4%. That is the real number; the old one was not backed by code.
- Your old workbook was copied to `tracker\legacy\replaced-*.xlsx`; the file at the old path is now the generated one.

## 8. Save the measurement and stop (2 min)
~~~powershell
git add tracker
git commit -m "chore(tracker): first honest measurement"
~~~
Nothing else tonight. Do not start Claude on code.

---------------------------------------------------------------------------------------------------------------------

# SPRINT 0, slot 2: Tue 13 Oct 19:30 (about 100 minutes)

## 1. Two audits at the same time (40 min). Both only read
Open the folder `locus-os` (never `5_Locus`: the rules load from the folder you open) in TWO Antigravity windows, one with a Claude
session and one with a Gemini session, each a NEW conversation. If Antigravity will not open the same folder twice, do Claude first and
Gemini second, with the same steps. In PowerShell:
~~~powershell
py -3 tools\tracker\backlog.py --prompt P0
Get-Content -Raw -Encoding UTF8 tracker\.cache\prompt-P0.md | Set-Clipboard
~~~
In each window: first message "what is the Locus canary?" It must answer `blue-heron-47`; if not, close that window and reopen the folder.
Second message: paste the clipboard (and, if step 7 of slot 1 printed a WARNING about `packages\`, paste that text after it). Each model
writes `tracker\handoff\P0-audit-<model>.md` and stops.

## 2. Read both reports (20 min)
Open the two files in `tracker\handoff\`. If a report's first line says it found a real key: rotate that key now (provider dashboard),
delete it from the file by hand, then go on. Where the two disagree, believe the one that quotes a command or a file and line. Nothing
is deleted tonight: anything marked DISCARD goes into a story's discard table and only your approval removes it (08-task-protocol.md).

## 3. Turn the audits into stories (30 min)
~~~powershell
py -3 tools\tracker\backlog.py --prompt P5
Get-Content -Raw -Encoding UTF8 tracker\.cache\prompt-P5.md | Set-Clipboard
~~~
NEW Claude session on `locus-os`, canary first, paste. It reads both reports, adds a story for every finding no story covers (security
first, then layout and duplicates, then the rest), and asks you one question at a time with its own recommended answer. Answer each.
It may write only `tracker\backlog.yaml`. When it says it is finished:
~~~powershell
py -3 tools\tracker\backlog.py --check
~~~
It must print `0 ERROR`. If it prints ERROR lines, paste them into the same session and say "fix these"; repeat until `0 ERROR`. A WARN
about a story that is not Ready is normal: Refinement fixes those.

## 4. Commit the backlog and merge Sprint 0 into main (10 min)
~~~powershell
$env:LOCUS_ALLOW_GUARD_EDIT = "1"
git add tracker
git commit -m "docs(agile): backlog after the Sprint 0 audit"
Remove-Item Env:LOCUS_ALLOW_GUARD_EDIT
git switch main
git merge --ff-only guardrails/install
git branch -d guardrails/install
py -3 tools\tracker\backlog.py
~~~
The board must print `No active sprint.` and `Sprint 1 planning day: Fri 2026-10-16 19:30`. Sprint 0 is finished. Hooks stay OFF.
(`$env:LOCUS_ALLOW_GUARD_EDIT = "1"` is you saying "I, the owner, am changing a rule file on purpose". Always remove it right after the
commit. Agents never set it.)

---------------------------------------------------------------------------------------------------------------------

# EVERY EVENING FROM FRI 16 OCT

~~~powershell
# paste the variables first, then:
py -3 tools\tracker\backlog.py
~~~
Do exactly what NEXT ACTION says and nothing else. When it says "Not a slot day" or "Nothing to do", close the laptop.
If the board prints `TURN THE HOOKS ON NOW`, run the command it shows (once, ever): from then on every commit runs the guard.

## What each slot contains
| Slot | First (time-boxed) | Then |
|---|---|---|
| 1 (Fri) | PLANNING, 30 min | the story the board names |
| 2, 3, 4 (Mon, Tue, Fri) | the board, 2 min | story work |
| 5 (Mon) | REFINEMENT, 30 min | story work |
| 6 (Tue) | REVIEW (demos) and RETRO, 45 min, then `--close-sprint` | nothing |

## What the board will tell you to do, by state (it prints the exact commands every time)
| State | You do |
|---|---|
| PLANNING | `--plan` (read it), owner variable on, `--plan --write`, `git add tracker/sprints.jsonl`, commit, owner variable off |
| TODO: START US-nn | `--start US-nn` (it makes the branch `task/US-nn-<slug>` and writes the prompt); NEW Claude session on `locus-os`; canary; copy the prompt with the `Set-Clipboard` line it prints and paste; answer its questions one at a time; when it says it is finished run `py -3 tools\guard\check.py --full`, then the board |
| DOING | the author session has not finished: let it finish, or open a new Claude session on the same branch with `--prompt P1 US-nn` |
| VERIFY | `--prompt P2 US-nn`; NEW session of the OTHER model (Gemini) on the SAME branch; canary; paste; it writes `tracker\handoff\US-nn-verify.md` and stops; then the board |
| REWORK | the verifier said no: NEW Claude session on the branch, paste P1 and say "Fix exactly the numbered findings in tracker\handoff\US-nn-verify.md and nothing else"; then verify again with a NEW Gemini session |
| MERGE | the commands the board prints, in this order: only if the verdict file is not committed yet, `git add` and `git commit` it (these two lines are missing when it already is); then switch to `main`, `git merge --ff-only`, delete the branch, `verify.py`, `export_xlsx.py`, `git add tracker`, commit |
| REVIEW | merged; waits for the Review slot; nothing to do |
| REFINEMENT (Mon, slot 5) | `--refine`; it lists the open decision rows and the stories that are not Ready and writes the prompts (P3 settles decisions, P5 completes stories); then `--check`, owner variable on, commit, owner variable off |
| REVIEW + RETRO (Tue, slot 6) | owner variable on; watch each demo; worked: `--accept US-nn --note "what I saw"`; did not work: do nothing (it stays in REVIEW and Refinement adds a fix story); `--retro`, fill the three sections in Notepad (exactly ONE line under "One change"); `--close-sprint`; `git add tracker`; commit; owner variable off |
| ANOMALY | files reached `main` without a verdict: run what the board prints |

Rules the board enforces so you do not have to remember them: one story in progress at a time; a story enters a sprint only when it is
Ready (small, has acceptance criteria and a demo, no open decision, dependencies merged); the author never verifies; a story is DONE only
after the guard shows 0 FAIL, the tracker level reaches the story's target, all nine handoff headings exist, a DIFFERENT model said
ACCEPT, it is merged `--ff-only`, and YOU watched the demo; velocity counts only DONE stories; nothing enters a running sprint.
A story marked `completes_feature: true` (today only US-06) also needs, after `--accept`:
~~~powershell
py -3 tools\tracker\record_proof.py F-0125 --note "what I watched"
~~~
Paste the line it prints into `tracker\signoff.yaml`, then owner variable on, `git add tracker/signoff.yaml`, commit, owner variable off.
Only that makes a feature 100%.

## If something looks wrong
| You see | Do |
|---|---|
| `REFUSED: ... is not Ready` | Not today. The board names the next story in the sprint, or says to run `--refine`; the story gets fixed at the next REFINEMENT. |
| `REFUSED: WIP limit 1: finish US-nn first` | Do the NEXT ACTION for US-nn. A second story cannot start until it is merged. |
| `REFUSED: start from main (you are on 'task/...')` | `git switch main`, then the board again. |
| `REFUSED: the working tree is not clean` | `git status --short`. Only files under `tracker\`: `git add tracker`, commit `chore(tracker): refresh`. Anything else: `git stash push -u -m "stray-$STAMP"` (nothing is lost; `git stash list` shows it), then the board again. |
| `REFUSED: ... human-owned file ... Only the owner runs it` | You ran an owner command without the variable. `$env:LOCUS_ALLOW_GUARD_EDIT = "1"`, run it again, then `Remove-Item Env:LOCUS_ALLOW_GUARD_EDIT`. |
| A new top-level folder you did not ask for (`core`, `locus`, `src`) | `py -3 tools\guard\check.py --full` names it. Do not merge; tell the session it broke AGENTS.md law 2. |
| `git status` lists `AGENTS.md`, `tools\` or `docs\agent\` as modified | An agent edited the rules. Undo: `git checkout -- AGENTS.md CLAUDE.md tools docs/agent tests/guard .githooks .github tracker/backlog.yaml tracker/signoff.yaml tracker/overrides.yaml tracker/spec_exclusions.yaml` |
| A session did not answer `blue-heron-47` | It did not load the rules. Close it, reopen the folder `locus-os`, ask again. |
| The author wants to delete a junction (`core`) | Only with `cmd /c rmdir "$ROOT\core"` (removes the link, never the target). Never `Remove-Item -Recurse`. |
| The Excel shows a number you doubt | `py -3 tools\tracker\verify.py --only F-xxxx` prints the reasons. The workbook is generated; fix the evidence, never the cell. |
| A new idea or bug appears mid-sprint | Do not build it. Paste it as your first answer in the next REFINEMENT's P5 session. A leaked secret is the exception: rotate it now. |
| Sprint 0 is not finished by Fri 16 Oct | In `tracker\backlog.yaml` change `first_sprint_start:` to the next Friday after you finish, then commit as in Sprint 0 slot 2 step 4. |
| A commit is blocked by the guard | Read the guard text. Only rule files need the owner variable; never `--no-verify`. |

---------------------------------------------------------------------------------------------------------------------

# AUTOPILOT (optional, from Sprint 2): Antigravity runs the sprint's stories while you are away

What it is: one script, `tools\tracker\autopilot.py`. It does what the board's NEXT ACTION tells you to do, one step at a time: a fresh headless
Antigravity session (`agy -p`) per step, Claude as the author, Gemini as the verifier, plain git commands for the merge. It stops at the first thing
that needs you: a question, a demo, a failure, the end of the sprint. It never plans a sprint, accepts a story, runs the retro or closes a sprint, and it
cannot make anything "100%": only you can (`--accept`, `record_proof.py`, `tracker\signoff.yaml`). So "until the whole project is 100%" does not exist
here; "until the next thing that needs me" does.
Not before Sprint 2: Sprint 1 (US-01 to US-03) is security work that you do by hand. US-01, US-12, US-14, US-15 and US-20 are marked `autopilot: false`
in the backlog: the autopilot stops in front of them and leaves them to you.
Honesty: I tested the script only against a fake `agy` on Linux. I never ran it against the real Antigravity CLI and never on Windows. That is why the first
runs below are supervised, one step at a time.

## A. One-time setup (30 min, any evening in Sprint 1)
0. Check the hands-on flags. This must print FIVE lines (US-01, US-12, US-14, US-15, US-20):
~~~powershell
Select-String -Path tracker\backlog.yaml -Pattern "autopilot: false"
~~~
If it prints fewer, your backlog was written before this feature. At the next REFINEMENT (P5 session) say: "Add the line `autopilot: false` directly after the `target_level:` line of
US-01, US-12, US-14, US-15 and US-20, one line each, and change nothing else." Then `py -3 tools\tracker\backlog.py --check` must print `0 ERROR`. Do not run the autopilot before this.
1. Install the command-line tool, then open a NEW PowerShell window:
~~~powershell
irm https://antigravity.google/cli/install.ps1 | iex
agy --version
~~~
2. Sign in once: type `agy`, finish the Google sign-in in the browser, then close that window. Headless runs use the saved sign-in.
3. See the model names and copy two EXACTLY as printed: the newest Claude Sonnet (or Opus) line and the newest Gemini Pro line.
~~~powershell
agy models
$AUTHOR   = "<the Claude line>"
$VERIFIER = "<the Gemini line>"
~~~
Write those two lines under your variables block; every run below needs them.
4. Allow the few shell commands the sessions need. Without this every command is refused silently (a headless session prints a notice and carries on).
Open `$env:USERPROFILE\.gemini\antigravity-cli\settings.json` in Notepad (create the file if it does not exist; if `agy` keeps its settings elsewhere on your PC,
`Get-ChildItem $env:USERPROFILE\.gemini -Recurse -Filter settings.json` finds it) and put exactly this in it, or merge the `permissions` block into what is there:
~~~json
{
  "permissions": {
    "allow": [
      "command(regex:^git (status|diff|log|show|add|commit|rev-parse|ls-files|mv|rm|branch --show-current)( .*)?$)",
      "command(py)",
      "command(python)",
      "command(regex:^npm (test|run (build|lint|test|typecheck))$)"
    ]
  }
}
~~~
This list has no `git push`, `git reset`, `git clean`, `git switch`, `curl`, `docker`, `ssh` or `Remove-Item` (the script itself switches and merges branches). When a run stops because a command was refused, the notice is in the last
lines of `tracker\.cache\autopilot.log` (`Get-Content tracker\.cache\autopilot.log -Tail 3`): add that one command and nothing wider. Be clear about what `py` means: a session
that may run `py` can run any code as you. The autopilot narrows and checks what sessions do; it is not a sandbox. That is why part B hides your keys.

## B. Before EVERY run (3 min)
~~~powershell
# paste the variables first, then:
Set-Location $ROOT
git status --short
Remove-Item tracker\.cache\STOP -ErrorAction SilentlyContinue
if (Test-Path "$env:USERPROFILE\.locus\.env") { Rename-Item "$env:USERPROFILE\.locus\.env" ".env.off" }
git ls-files -co | Where-Object { $_ -notmatch '(^|/)node_modules/' -and $_ -match '(^|/)(\.env(\.local|\.prod|\.production)?|credentials[^/]*|secrets?\.[^/]*)$|\.(pem|key)$' }
~~~
`git status --short` must print nothing (if it prints files, run the board and follow it first). The `Rename-Item` line hides your keys file from the sessions; the `git ls-files` line must
print nothing (it lists every file in the folder, ignored by git or not, that is named like a key file: `.env`, `*.pem`, `*.key`, `credentials*`, `secrets.*`; anything it prints sits inside the folder the sessions can read, so move it to `$env:USERPROFILE\.locus\` first).

## C. The first runs: watch each one (the first autopilot evening, about 60 min plus waiting)
~~~powershell
py -3 tools\tracker\autopilot.py --author-model $AUTHOR --verifier-model $VERIFIER --dry-run
~~~
It must print `DRY RUN: the next action would be START US-nn (...)`, and nothing is changed. Any other line is the answer: see table D. Then ONE step:
~~~powershell
py -3 tools\tracker\autopilot.py --author-model $AUTHOR --verifier-model $VERIFIER --max-steps 1
~~~
It asks each model for the canary first (the smoke test: it proves `agy -p` returns, the names are right and the rules load), then starts the story and runs the author once.
Nothing prints while a model works; allow up to 45 minutes. When it stops, run `py -3 tools\tracker\backlog.py`: the story should be VERIFY, and `git log --oneline -5` shows the author's
commits. Nothing was merged, so if you dislike what you see the manual steps of the board still work. Run the same command again (verifier: the board must show MERGE or
REWORK), and once more (merge). After one story went through all three, run unattended:
~~~powershell
py -3 tools\tracker\autopilot.py --author-model $AUTHOR --verifier-model $VERIFIER --max-steps 12 --max-minutes 240
~~~
A story that is accepted the first time takes 3 steps; each rework round adds 2. While it runs do not touch the folder: no commit, no branch switch, no edit, and do not open the
same folder in the Antigravity window. To stop early open a second PowerShell window and run `New-Item tracker\.cache\STOP`: it ends after the current step.
Every run, when it stops (always):
~~~powershell
if (Test-Path "$env:USERPROFILE\.locus\.env.off") { Rename-Item "$env:USERPROFILE\.locus\.env.off" ".env" }
py -3 tools\tracker\backlog.py
~~~
Read the last lines the autopilot printed, find them in table D, do that; then the board.

## D. What it printed, and what you do
| It printed | Meaning | You do |
|---|---|---|
| `no sprint is active: planning is yours` | no sprint is planned | the Planning slot: the board |
| `sprint S2 ended on ...` or `nothing is left to start in sprint ...` | the work is done or the time is up | the Review slot: demos, `--accept`, retro, `--close-sprint`; if a story waits in REVIEW, watch its demo first |
| `US-nn is marked 'autopilot: false'` | a story for you | do it by hand with the board (NEXT ACTION); run the autopilot again after it is merged |
| `the author has questions only you can answer: tracker/handoff/US-nn-questions.md` or `waiting for your answers` | the author could not decide alone (this replaces `/grill-me`) | open that file in Notepad; under every `Answer:` write your answer after the colon; save; run the autopilot again. If a question is about an OPEN decision row, answer it with the recommendation only if you accept it, else leave the story for Refinement |
| `the step budget is used` or `the time budget is used` or `the STOP file exists` | you set the limit | run it again (delete `tracker\.cache\STOP` first if it exists) |
| `AUTOPILOT STOPPED, SOMETHING UNEXPECTED: ... agy exited ...` or `agy did not answer within ...` or `agy status ...` | the session failed or hung | `Get-Content tracker\.cache\autopilot.log -Tail 5`; sign in again by typing `agy` once; update `agy` with the install line; run again. If it hangs twice: stop using the autopilot and use the board by hand (nothing is lost) |
| `the reply did not contain the Locus canary` | that session did not load AGENTS.md | open `locus-os` (never `5_Locus`) in the window where you started; or add `--inline-rules` to the command |
| `no progress after 2 attempts` | a session ran and changed nothing the board can see (often a refused command) | `Get-Content tracker\.cache\autopilot.log -Tail 3` for a refused-command notice; add that one command to the allow list (A4), or do the step by hand with the board |
| `the guard shows FAIL on task/...; nothing was merged` | the work breaks a rule | `py -3 tools\guard\check.py --full`; paste its output into a NEW Claude session on the same branch with "fix exactly these FAILs"; then the board |
| `the verifier did not accept it after 2 rounds of rework` | the story is too big or the findings are real | read `tracker\handoff\US-nn-verify.md`; fix by hand with the board, or leave the branch and let Refinement split the story |
| `is merged, but a feature went DOWN: REGRESSION ...` | the story broke another feature | do not run the autopilot again; paste the line into a new Claude session: "RUNBOOK autopilot regression" |
| `uncommitted files on ...` or `git switch ... failed` | something changed in the folder while it ran | `git status --short`; follow the "working tree is not clean" row of the table at the end of the RUNBOOK; then the board |
| `AUTOPILOT DID NOT START: ... smoke test failed` | `agy -p` hangs or fails here, a name is wrong, or the rules did not load | read the text after "smoke test failed". A hang is a known `agy` bug on some versions and PCs: update `agy`, try once more, else use the board by hand |
| `AUTOPILOT DID NOT START: ... commit hooks are off` | the guard is not wired to commits | `git config core.hooksPath .githooks` (the board tells you when) |
| `AUTOPILOT DID NOT START: ... owner variable` | the owner variable is set in this window | `Remove-Item Env:LOCUS_ALLOW_GUARD_EDIT` |
| `AUTOPILOT DID NOT START: ... not in the output of agy models` or `agy models failed` | wrong slug or not signed in | copy the slug exactly from `agy models`; type `agy` once to sign in |
| `AUTOPILOT DID NOT START: ... the guard shows FAIL before the first step` | the repo is already red | `py -3 tools\guard\check.py --full`, fix, then run again |

## E. Rules that stay true
- Never add `--dangerously-skip-permissions` or `--agy-args "--dangerously-skip-permissions"`. Never use an IDE "Always Proceed"/Turbo setting or an auto-click browser extension for this: the
  IDE setting has been reported not to take effect, and an auto-click extension is unreviewed code that presses Allow on whatever a model asks for.
- It uses your Antigravity quota: a story is 3 to 7 sessions. If the quota runs out, `agy` fails and the autopilot stops with an `agy status` or `agy exited` line.
- A story the autopilot merged is still only REVIEW. It is DONE after you watched the demo and ran `--accept`. The autopilot does not shorten that.
- `/graphify update .` is an interactive command that a headless session may be unable to run. When it could not, its handoff says "graphify: NOT RUN (autopilot)": then you run it in `5_Locus` and in `5_Locus\locus-os` before the demo.
