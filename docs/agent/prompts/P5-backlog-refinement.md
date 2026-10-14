# P5 - Refine the backlog (the owner decides; you ask, draft, and write only tracker/backlog.yaml)

You never fill this in by hand. `py -3 tools\tracker\backlog.py --refine` (or `--prompt P5`) writes it, with the stories and problems
filled in, to `tracker\.cache\prompt-P5.md`. Use it in Sprint 0 (to turn the two audit reports into stories) and at every Refinement slot.
The owner commits the result with `LOCUS_ALLOW_GUARD_EDIT=1`.

---
Goal: make these stories Ready: {{TOP}}. Problems the board found:
{{PROBLEMS}}

What Ready means (python tools/tracker/backlog.py --check enforces it): points 1, 2 or 3 (a story that needs more than three evening
slots must be split); a feature id that exists; a slug; `accept` with observable criteria; `demo` (the exact live steps the owner will
watch and the result to expect); `target_level` 2, 3 or 4; every `requires_decisions` row not OPEN; every `depends_on` story ABOVE it.
A story is ONE slice of ONE tracker feature. Read docs/agent/11-agile-workflow.md first.

If `tracker/handoff/P0-audit-*.md` exist, also read their Discard table, Security, and Unbacked claims sections. For every finding no
story covers, add one story (group findings of the same feature), place security first, then layout and duplicates, then the rest.

For each story with a problem, one at a time:
1. Run `python tools/tracker/show.py <feature> --spec` and quote the spec sentences or owner requirement ids (R1-R10, S-1 to S-3)
   this slice covers.
2. Draft title, points, target_level, accept (each criterion checkable by a command or a visible behaviour; copy numbers and names from
   the spec), demo, requires_decisions, depends_on, slug.
3. Ask the owner, one question at a time, each with your recommended answer, only what you cannot take from the spec or the errata.
4. Size check out loud: "this is N points because ..." If it is more than 3, split it into two stories, in order.
5. Write it into `tracker/backlog.yaml`. This session is the one allowed exception to AGENTS.md law 11, for that single file. Keep the
   existing order unless the owner says otherwise. Never change a story's feature to hide a problem, never delete a story, never edit any
   other file.

At the end run `python tools/tracker/backlog.py --check`, paste its output (it must show 0 ERROR), and list the stories that are now Ready.
