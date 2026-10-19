# P7 - Autopilot rules for the VERIFIER session (appended to P2 by tools/tracker/autopilot.py)

Nobody pastes this. `py -3 tools\tracker\autopilot.py` appends it to the story's P2 prompt when it runs the verifier unattended
(docs/agent/11-agile-workflow.md, "Autopilot"). The verifier is always a different model family than the author.

---
AUTOPILOT MODE. No human is present: nobody can answer a question or approve anything, and nobody reads your reply live.
1. Begin your final reply with the line `CANARY: ` followed by the Locus canary phrase from AGENTS.md. A reply without it is thrown away.
2. You may write exactly one file: `tracker/handoff/{{STORY}}-verify.md`. Its first line is `VERDICT: ACCEPT`, `VERDICT: ACCEPT-WITH-FIXES`
   or `VERDICT: REJECT`; its second line is `Verifier: <your model name>`. Do not commit it and do not edit anything else.
3. A check you cannot run (the command is refused, a tool is missing, a test needs the owner's key or VM) counts as MISSING: the verdict
   cannot be ACCEPT. Name the check and the exact command the owner would have to run.
4. If you are the same model family as the author named above, write nothing and reply `SAME FAMILY`.
5. Reply `VERIFIED {{STORY}}: <verdict>` and stop.
