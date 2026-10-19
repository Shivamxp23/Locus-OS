# P6 - Autopilot rules for the AUTHOR session (appended to P1 by tools/tracker/autopilot.py)

Nobody pastes this. `py -3 tools\tracker\autopilot.py` appends it to the story's P1 prompt when it runs the author unattended
(docs/agent/11-agile-workflow.md, "Autopilot"). It replaces the two things that need a human: `/grill-me` and approvals.

---
AUTOPILOT MODE. No human is present: nobody can answer a question or approve anything, and nobody reads your reply live.
These rules override every part of the text above that tells you to wait for, or to ask, the owner.
1. Begin your final reply with the line `CANARY: ` followed by the Locus canary phrase from AGENTS.md. A reply without it is thrown away.
   This session has no second turn: do the whole task now and end your turn only with `DONE {{STORY}}` or `QUESTIONS {{STORY}}`. Step 3 of the text above
   ("reply with the spec sentences and your questions") does not apply: put the spec sentences in the Plan of your handoff and the questions in the questions file.
2. `/grill-me` cannot run. Instead, before any code, list every question you cannot answer from the spec section of the feature
   (`python tools/tracker/show.py <feature> --spec`), the DECIDED rows of docs/agent/09-spec-errata.md, and this story's acceptance criteria.
   - If you have even one such question: write ALL of them to `tracker/handoff/{{STORY}}-questions.md` in exactly this form, change
     nothing else, and stop with the reply `QUESTIONS {{STORY}}`:
         Q1: <the question>
         Recommended: <your recommendation and the reason>
         Answer:
   - If you have none: write "No open questions" under the Open questions heading of your handoff and go on.
   - If `tracker/handoff/{{STORY}}-questions.md` already exists with its Answer lines filled in, those are the owner's answers: follow them.
3. Never guess. Never pick a default for an OPEN row of the errata. Never make a test pass by weakening it, deleting it, or asserting less.
4. If you need a key, the VM, Telegram, Docker, the network, a file outside this repo, or a command that is refused: write what you needed
   to the questions file in the same form and stop with `QUESTIONS {{STORY}}`.
5. Never run `git push`, `backlog.py --plan`, `--accept`, `--retro` or `--close-sprint`, or anything that sets LOCUS_ALLOW_GUARD_EDIT.
   Never edit a human-owned file (AGENTS.md law 11).
6. Commit on this branch in small commits, adding only the paths you changed (never `git add -A`; never `tracker/handoff/{{STORY}}-verify.md`).
   When the handoff is complete and the guard shows 0 FAIL, reply `DONE {{STORY}}` and stop. Do not start another story.
