# P1 - Implement exactly one story (the author prompt)

You never fill this in by hand. `py -3 tools\tracker\backlog.py --start US-nn` creates the branch `task/US-nn-<slug>` from a clean
`main` and writes this prompt, with the story's text filled in, to `tracker\.cache\prompt-US-nn-P1.md`. You copy that file into a NEW
session of ONE model (Claude is the author) and send the Locus canary question first.

---
You are the only author of branch `{{BRANCH}}`. Your task is story {{STORY}} ({{POINTS}} points): {{TITLE}}
It is one slice of tracker feature {{FEATURE}}. When you are finished, `python tools/tracker/verify.py --only {{FEATURE}}` must compute
at least level {{TARGET}}. Nothing else is in scope.

Acceptance criteria (a verifier of a different model checks each one against your code and your tests):
{{ACCEPT}}

The owner will watch this live at the Sprint Review, so build toward it: {{DEMO}}
Decisions already settled for this story (rows of docs/agent/09-spec-errata.md): {{DECISIONS}}

Before anything else:
1. Answer "what is the Locus canary?" from AGENTS.md. If you cannot, say so and stop.
2. Run `python tools/tracker/show.py {{FEATURE}} --spec`. Read only the segments AGENTS.md maps to this story, in docs/agent/.
3. Reply with, and nothing more: (a) the spec sentences (or owner requirement ids such as R3 or S-1) this slice covers, quoted with their
   spec line; (b) every question you cannot answer from the spec, the errata, and the code, each with your recommended answer. Then run
   `/grill-me`: one question at a time, wait for my answer. Write no code until the questions are answered. If an answer depends on an
   OPEN row in docs/agent/09-spec-errata.md, stop and tell me which row.

Then follow docs/agent/08-task-protocol.md from step 5 (Plan) to step 9 (Handoff), exactly. In particular:
- Layout, imports, Pi bridge: docs/agent/02-architecture-lock.md. Never edit `packages/`, never create `core/` or any new top-level entry,
  never add a shim or alias, never touch a human-owned file (AGENTS.md law 11).
- Build it modular: interface, config switch, off behaviour, a swap test (docs/agent/03-modularity.md).
- Pi first (AGENTS.md law 14): write the Pi table under Plan before any code (need | Pi mechanism with file:line | what Locus adds | why Pi's is not enough). The first docstring line of every test is `SPEC <section> line <n>: "<spec sentence>"`.
- No stubs or fake data unless the line says `STUB({{FEATURE}})`. Never write "done" or "complete" or a percentage: the verifier computes status.
- Add evidence to `tracker/features.yaml` for {{FEATURE}} (add only). Tests must name what you built and assert behaviour.
- Commit messages: `<type>({{STORY}}): <what>`. Commit only the paths you changed (`git add <path> ...`), never `git add -A` or `git add .`.
  `tracker/handoff/{{STORY}}-verify.md` is the verifier's file: never add, edit or commit it.
- At the end run, and paste the real output of: `python tools/guard/check.py --full`, `python tools/tracker/verify.py --only {{FEATURE}}`,
  the tests, then `python tools/tracker/verify.py` and `python tools/tracker/export_xlsx.py`. Write `tracker/handoff/{{STORY}}.md` from the template in 08-task-protocol.md. Its FIRST line must be
  `# {{STORY}} handoff - <your model name>, <date>`; all nine headings need content. Then stop.
- Never run `backlog.py --accept`, `--plan --write`, `--retro` or `--close-sprint`, and never set LOCUS_ALLOW_GUARD_EDIT: those are the owner's.

If you change more than about 10 files, if the spec is silent or contradicts itself, or if you need my keys or accounts: stop and ask.
You are not allowed to start another story, refactor unrelated code, or "clean up" while you are here.
