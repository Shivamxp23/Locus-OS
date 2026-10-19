# P3 - Settle open spec questions with the owner (the owner decides; you only ask and record)

You never fill this in by hand. At Refinement, `py -3 tools\tracker\backlog.py --refine` lists the OPEN decision rows the next stories
need and writes this prompt, with those rows filled in, to `tracker\.cache\prompt-P3.md`. Decisions are made just in time: only the
rows the next stories need, never all of them at once. The owner answers by typing; the owner commits the result.

---
Goal: turn these OPEN rows of docs/agent/09-spec-errata.md into DECIDED, one at a time, in this exact order: {{ROWS}}
Do not ask about any other row, and do not invent new ones unless you find a contradiction in the spec that blocks one of these rows
(then list it as a new row, ask about it, and say why).

For each row, one at a time:
1. State the question in two sentences, using the row's evidence (spec line numbers). Do not paraphrase the evidence away.
2. Give the options with the consequence of each, and ONE recommendation with the reason. For D-1, remind the owner that
   `LOCUS_SYSTEM_v1.md` sections 3.2 and 10 are the cited authority and must be opened to settle it.
3. Wait for the owner's answer. "Whatever you think" means: restate the recommendation and ask for a plain yes or no.
4. Write the answer into that row only: status DECIDED, today's date, the owner's words in quotes, and the exact rule an agent must follow.
   Update the row's line in the section A index table too (the board reads that table). This session is the one allowed exception to
   AGENTS.md law 11, for that single file; the owner commits it with `LOCUS_ALLOW_GUARD_EDIT=1`.
5. Say which backlog stories become unblocked (the owner will confirm with `python tools/tracker/backlog.py --refine`), then ask the next question.

Never decide for the owner, never merge two questions, never edit anything but `docs/agent/09-spec-errata.md`, never touch the spec.
When all listed rows are done, print the table of those rows with their final status and stop.
