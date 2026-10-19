# 08 - Task protocol (one story, one model, one branch, one handoff)

Why: two models on one codebase invented two layouts (`sidecar/` and `core/`) and one overwrote the other. The fix is not a better
prompt. It is a protocol where each story has exactly one author, a written definition of done, and a check by a different model.
The sprint around it is in 11-agile-workflow.md. The board (`python tools/tracker/backlog.py`) names the story and the step.

## Lifecycle (every step, in order)
1. **Pick.** The board names ONE planned story, e.g. US-03 (feature F-0083). The owner runs `backlog.py --start US-03`: it creates
   `task/US-03-<slug>` from a clean `main` and writes your prompt. Anything else: refuse and ask.
2. **Branch.** Already created by `--start`. Never commit on `main`.
3. **Read.** `python tools/tracker/show.py F-0083 --spec`, then only the segments AGENTS.md maps to this story.
4. **Grill.** List what you cannot answer from the spec, the errata, and the code. Run `/grill-me`: ONE question at a time, each with
   your recommended answer and why. If an answer is "not decided", stop and name the errata row. No code before the answers.
5. **Plan.** In `tracker/handoff/US-03.md` under "Plan": every file you will create or change (full paths), the tests, the config
   keys. A path outside the layout (02-architecture-lock.md) means stop here.
6. **Build** in small commits. Format `<type>(US-03): <what>`, type in feat, fix, test, refactor, docs, discard, chore.
   A `discard:` commit removes only the files in the handoff's discard table.
7. **Prove.** Tests per 07-tracker-evidence.md and 03-modularity.md; run them; add the evidence to `tracker/features.yaml`.
8. **Check.** `python tools/guard/check.py --full` shows 0 FAIL; `python tools/tracker/verify.py --only F-0083`; quote both lines.
   Then `python tools/tracker/verify.py` (full run; `--only` does not write anything) and `python tools/tracker/export_xlsx.py`: the
   owner's standing rule "update the tracker xlsx" is exactly these two commands.
9. **Handoff and stop.** Fill the template below. Do not start the next story. Do not tidy code outside the plan.
After step 9 a fresh session of a DIFFERENT model runs prompt P2 and writes `tracker/handoff/US-03-verify.md`; the owner merges, and
accepts at the Sprint Review (11-agile-workflow.md, Definition of Done).

## Stop conditions (stop, write what you know in the handoff, ask)
- The story needs a change in `packages/`, a new top-level folder, a new port, a new dependency, or a human-owned file.
- The spec is silent or contradicts itself, or the story touches an OPEN row of 09-spec-errata.md.
- A test needs the owner's real keys, VM, or accounts.
- The guard fails for a reason outside your change. Report it; never "fix" the guard.
- You have changed more than about 10 files for one story: stop, say the story is too big, and ask for it to be split.
- You catch yourself writing "should work", "probably", or "for now". That sentence is a stub: mark it `STUB(F-xxxx)` or stop.
- You find a secret or a vulnerability: say so in your first sentence (10-security.md).

## Discard protocol (the owner: "whatever is not good, discard it")
Never delete on a hunch. Every file marked DISCARD (by the Sprint 0 audit, prompt P0, or by you) gets a row: path, why (law or spec
line), what replaces it, who imports it. Only after the owner answers "discard rows 1-5" does an agent run `git rm` on exactly those
rows, in one `discard(US-nn): ...` commit. Git history and the Sprint 0 backup (RUNBOOK) keep everything recoverable.
A junction or symlink (for example `core`) is removed with `cmd /c rmdir <path>`, which removes the link and never the target.
Never use `Remove-Item -Recurse`, `rm -rf`, `git clean`, or `git rm -r` on one.

## One model per story
The author is never the verifier. After the handoff, a fresh session of a DIFFERENT model runs prompt P2, read-only. The board accepts
a verdict only if its first line is `VERDICT: ACCEPT` and its `Verifier:` line names a different model family than the handoff's first
line. REJECT or ACCEPT-WITH-FIXES sends the story back to the author (state REWORK). If the verifier and `verify.py` disagree, the
verifier's evidence stands until the owner decides. Never two models on one branch; never swap models mid-story.

## Handoff template: `tracker/handoff/US-03.md` (all nine headings need content; the board checks)
~~~
# US-03 handoff - <model>, <date>
## Plan (written before coding)
## Files changed (every path, one line each)
## Spec sentences implemented (quote + spec line) / NOT implemented and why
## Config keys and defaults added
## Commands run, with real output (guard, verify line, tests)
## Open questions / errata rows touched
## Discard table (path | why | replaced by | imported by)
## Security (anything found, even if outside this story)
## Not done (be specific; "nothing" is almost never true)
~~~
