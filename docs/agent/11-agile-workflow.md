# 11 - Agile workflow (Scrum-shaped: the owner is the Product Owner, the models are the team)

Why: the owner builds in fixed evening slots, models forget between sessions, and "phases" let work drift. A sprint gives a time box,
the backlog gives ONE priority order, and the board script derives status from evidence and prints the next action, so nothing is
decided in the moment. Run `python tools/tracker/backlog.py` at the start of every slot and do exactly its NEXT ACTION.

## Roles
| Role | Who | Does |
|---|---|---|
| Product Owner | Shivam | orders the backlog, decides errata rows, watches demos, accepts, signs off 100% |
| Developers | Claude writes, Gemini verifies | one story at a time; the author never verifies or accepts its own work |
| Scrum Master | `tools/tracker/backlog.py` | derives status, enforces Ready, WIP and review, prints NEXT ACTION |

## Files
| File | Holds | Written by |
|---|---|---|
| `tracker/backlog.yaml` | epics, stories IN PRIORITY ORDER, sprint config (slots, capacity) | owner, in a P5 session |
| `tracker/sprints.jsonl` | append-only events `planned`, `accepted`, `closed` (velocity) | owner, through `backlog.py` |
| `tracker/retro/S1.md` | the retrospective of each sprint | owner |
| `tracker/handoff/US-nn.md` and `US-nn-verify.md` | the author's report, the verifier's verdict | the agents |
| `tracker/handoff/US-nn-questions.md` | autopilot only: what the author could not answer, with `Q1:`, `Recommended:`, `Answer:` | the author asks, the owner fills in `Answer:` |
| `tracker/status.json` | computed level of every feature | `verify.py` |
Nobody types a status anywhere. A story's state is derived from git and these files.

## The sprint: 14 days, 6 slots (Mon, Tue, Fri 19:30; change `slot_days` in the backlog config if your evenings change)
| Slot | First (time-boxed) | Then |
|---|---|---|
| 1 | PLANNING 30 min: `--plan`, then `--plan --write` | story work |
| 2, 3, 4 | the board, 2 min (the Daily Scrum) | story work |
| 5 | REFINEMENT 30 min: `--refine` | story work |
| 6 | REVIEW 30 min (demos, `--accept`) and RETRO 15 min, then `--close-sprint` | nothing |
`python tools/tracker/backlog.py --calendar` prints every date.

## Definition of Ready (a story enters a sprint only if)
1 to 3 points; one feature; a slug; checkable `accept` criteria; a `demo` the owner can watch; target level 2, 3 or 4; no OPEN row in
`requires_decisions`; every `depends_on` story merged. `--refine` lists what is missing and writes the prompt that fixes it (P3, P5).

## Definition of Done (all six, or the story is not DONE)
1. Guard `--full` shows 0 FAIL. 2. `verify.py` computes the feature at or above the story's target level. 3. The handoff has all nine
headings. 4. A verdict `ACCEPT` from a DIFFERENT model family (P2). 5. Merged to `main` with `--ff-only`. 6. The owner watched the demo and
ran `backlog.py --accept`. The board checks 3 to 6; the verifier checks 1 and 2. A story with `completes_feature: true` also needs
`record_proof.py` and a sign-off in `tracker/signoff.yaml`: that is what makes the feature 100%.

## Story states (derived; never typed)
| State | Meaning | Next |
|---|---|---|
| TODO | no branch, no files | `--start US-nn` |
| DOING | branch exists, handoff missing or incomplete | author finishes |
| VERIFY | handoff complete, no valid verdict from another model | P2 in the other model |
| REWORK | verdict REJECT or ACCEPT-WITH-FIXES | author fixes, verify again |
| MERGE | verdict ACCEPT on the branch | the merge commands the board prints (first the commit of the verdict file, when it is not committed yet) |
| REVIEW | merged to `main`, not yet accepted | demo at the Review slot |
| DONE | accepted | counts toward velocity |
| ANOMALY | files on `main` without a valid handoff and verdict | the board prints the fix |

## Rules
- WIP limit 1: one unmerged `task/US-nn-<slug>` branch at a time (AGENTS.md law 12). `--start` refuses a second one.
- Capacity: 4 points until three sprints have closed; then the average velocity of the last three, rounded down, between 2 and 8.
- Planning takes Ready stories strictly in priority order and stops at the first one that does not fit. Unfinished stories carry over first.
- Nothing enters a running sprint. A new finding goes into the backlog and is planned next sprint. A leaked secret is not a story:
  rotate it now (10-security.md S-0).
- Velocity = points of ACCEPTED stories (the `closed` event). Unaccepted work counts for nothing, however finished it looks.
- The retrospective `tracker/retro/S1.md` needs Worked, Did not work, and exactly ONE line under "One change". `--close-sprint` refuses without it.
- Decisions are just in time: `requires_decisions` blocks a story until its errata row is not OPEN, and P3 settles only the rows the next stories need.
- Only the owner runs `--plan --write`, `--accept`, `--retro` and `--close-sprint` (they need `LOCUS_ALLOW_GUARD_EDIT=1`). Agents never do.
- `python tools/tracker/backlog.py --check` runs in CI: a typed-in acceptance, a second story in progress, or a story over 3 points fails it.

## Autopilot (optional: from Sprint 2, only with the hooks on, never before)
`py -3 tools\tracker\autopilot.py --author-model <slug> --verifier-model <slug>` does what the board's NEXT ACTION tells the owner to do, with a
fresh headless Google Antigravity session (`agy -p`) for each model step and plain git and tool commands for the rest, and it stops at the first thing
that needs the owner. It adds no authority: same prompts (P1 + P6 for the author, P2 + P7 for the verifier), same guard, same states, same rules.
It cannot make a feature or the project "100%": that needs the owner's sign-off (Definition of Done 6, `record_proof.py`, `tracker/signoff.yaml`).
| State the board derives | What the autopilot does |
|---|---|
| TODO | `backlog.py --start US-nn`, then the author (model A) |
| DOING | the author again, in a new session |
| VERIFY | the verifier (another model family), in a new session on the same branch |
| REWORK | the author fixes exactly the numbered findings, then the verifier checks again; at most 2 rounds per story |
| MERGE | commit the verdict file, `check.py --full`, `git switch main`, `git merge --ff-only`, `git branch -d`, `verify.py`, `export_xlsx.py`, `git add tracker`, commit |
| REVIEW, DONE | nothing: the demo, `--accept`, the retro and `--close-sprint` are the owner's |

It stops with exit 0 at an owner gate: no sprint planned; the sprint ended (Review and Retro); nothing left to start; a story marked `autopilot: false`;
questions without an answer; the step budget (default 6) or the time budget (default 180 minutes); the file `tracker/.cache/STOP`.
It stops with exit 1 on anything unexpected: an agent that fails, times out, or replies without the Locus canary; no progress twice; a red guard before a merge;
a refused board command; a story rejected after 2 rework rounds; a feature that went DOWN after a merge.
It refuses to start (exit 2) unless the commit hooks are on, the guard shows 0 FAIL, the two models are different families, `LOCUS_ALLOW_GUARD_EDIT` is not set,
and a one-line smoke question to each model returns the canary within 3 minutes (`agy -p` has hung without a terminal on some versions and machines).

What keeps it inside the process:
- One fresh session per step. No session remembers anything; the state is git and `tracker/`, derived again before every step.
- Nobody can be asked a question, so `/grill-me` becomes a file: the author writes `Q1:`, `Recommended:`, `Answer:` into `tracker/handoff/US-nn-questions.md` and stops;
  the owner fills in each `Answer:`; the next run follows the answers. A story that cannot be built without a key, the VM, Telegram, Docker or the network ends the same way.
- The verifier is another model family and may write only `tracker/handoff/US-nn-verify.md`. A check it cannot run counts as MISSING, which blocks ACCEPT.
- The driver never plans, accepts, runs a retro, closes a sprint, pushes, sets the owner variable, or passes an environment variable that looks like a key
  (TOKEN, SECRET, PASSWORD, API_KEY) to an agent. Agents are told the same in P6 and P7.
- `autopilot: false` on a story in `tracker/backlog.yaml` keeps it for the owner at the keyboard: deleting folders, a real key, a VM, a bot, starting other programs.
- Never `--dangerously-skip-permissions`. Shell commands are allowed one by one in the Antigravity CLI settings (RUNBOOK, "AUTOPILOT"); a refused command stops the story.
- Every step is appended to `tracker/.cache/autopilot.log`. `New-Item tracker\.cache\STOP` ends the run after the current step.
Limits: an agent allowed to run `py` can run any code as the owner, so this narrows and checks what it does; it is not a sandbox. The owner still watches every demo.
