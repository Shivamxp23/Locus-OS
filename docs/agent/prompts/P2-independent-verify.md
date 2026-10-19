# P2 - Independent verification (READ-ONLY, by a DIFFERENT model than the author)

You never fill this in by hand. When the board says VERIFY, run `py -3 tools\tracker\backlog.py --prompt P2 US-nn`; it writes
`tracker\.cache\prompt-US-nn-P2.md`. Open a NEW session of the OTHER model (author Claude: verifier Gemini) on the SAME branch, send the
canary question first, then paste that file. The verifier may run commands but may not edit any file except `tracker/handoff/US-nn-verify.md`.

---
You verify branch `{{BRANCH}}` for story {{STORY}} ({{TITLE}}), tracker feature {{FEATURE}}. You did not write it: the author was
{{AUTHOR}}. The author's handoff is `tracker/handoff/{{STORY}}.md`. Treat every sentence in it as a claim to test, not as a fact.
You do not fix anything; you report.

Acceptance criteria you must check one by one:
{{ACCEPT}}

1. `git diff main...HEAD --stat` and `git diff main...HEAD --name-only`. Flag: any file outside the handoff's plan, any change under
   `packages/`, any human-owned file (AGENTS.md law 11), a new top-level entry, a junction or symlink, a shim or alias.
2. Run `python tools/guard/check.py --full` and `python tools/tracker/verify.py --only {{FEATURE}}` (the full run, not `--static`).
   Paste both outputs. The computed level must be at least {{TARGET}}; if it is lower the verdict cannot be ACCEPT.
3. Run `python tools/tracker/show.py {{FEATURE}} --spec`. For each acceptance criterion above, find the code AND the test that
   satisfy it (file and line) or write MISSING. For each spec sentence the handoff says was NOT implemented, say whether the reason is acceptable.
4. Open every test the handoff cites. Does it assert the behaviour named in the criteria? Then prove it can fail: create a scratch copy
   with `git worktree add ../verify-tmp`, break the feature there on purpose, run the test, confirm it FAILS, remove the worktree.
   Never use `git stash` or edit the branch itself.
5. Modularity (docs/agent/03-modularity.md): do the off test, the swap test, and the health test exist, and do they pass?
6. Search the diff for: TODO, pass, "for now", fake or mock data in shipped code, hard-wired hosts, ports, paths, models, or timezones,
   `os.environ` or `process.env` outside the config accessor, any secret-shaped string, any port bound to 0.0.0.0.
7. Can the owner do this demo with what you saw? {{DEMO}}

8. Pi first (AGENTS.md law 14): open every file:line in the handoff's Pi table and confirm it exists and does what the table says. Search the diff and the new files for anything that re-implements what Pi already provides (agent loop, model or provider layer, session store, tool runner, compaction, TUI, keybindings, settings) and for any change that ignores the feature's verdict (KEEP-PI means no code). Any such finding makes the verdict REJECT. Also check that every test docstring starts with a `SPEC <section> line <n>:` quote and that the quoted sentence is really in the spec and is what the test asserts.

Write `tracker/handoff/{{STORY}}-verify.md`. Its FIRST line must be exactly one of:
`VERDICT: ACCEPT` (every criterion has code and a test that can fail, nothing is left to fix),
`VERDICT: ACCEPT-WITH-FIXES` (small numbered fixes remain), or `VERDICT: REJECT`.
Its SECOND line must be `Verifier: <your model name>`. Then the headings: Guard output, Verify line, Criteria table, Test attack result,
Findings (a numbered list: file, line, why), Not checked. "Looks good" is not a finding. If something could not be checked, write
NOT CHECKED and why. The board refuses a verdict whose Verifier line names the same model family as the author.
