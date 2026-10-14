# P0 - Audit the existing code and propose what to discard (READ-ONLY)

When: Sprint 0, slot 2 (RUNBOOK), right after the guardrails are installed. Run it TWICE at the same time in two fresh sessions, one
per model (both are read-only, so they cannot collide); the owner compares the two reports. Paste everything below the line as the first message.

---
You are an auditor, not a builder. You may not edit, move, or delete anything. The only file you may create is
`tracker/handoff/P0-audit-<your model name>.md`.

Context: this repo is Locus, a modular headless personal-intelligence framework built ON TOP of the Pi coding agent. Earlier AI sessions
changed the code and then reported it as finished. Assume nothing in any older report, in `tracker/legacy/`, or in a code comment is true
until you have run or read the code yourself. Rules are in AGENTS.md; read docs/agent/01-vision.md, 02-architecture-lock.md,
07-tracker-evidence.md and 09-spec-errata.md before you start.

Do these in order:
1. Run `python tools/guard/check.py --full --all` and `python tools/tracker/verify.py --static`. Paste the summary lines verbatim.
2. For every top-level folder, and every Python or TypeScript file under `sidecar/`, `locus-extension/`, `locus_cli/`, scripts, and the
   install files, give a verdict: KEEP, FIX, DISCARD, or UNKNOWN. Each verdict carries one line of evidence: a spec section, an AGENTS.md
   law, a guard id, or a command you ran. No evidence means UNKNOWN, never KEEP.
3. Every DISCARD gets: path, reason (law or spec line), what replaces it, and every file that imports it (show the grep you ran).
4. List every place where two files do the same job: duplicate modules, copies of `pi_bridge`, shims, parallel config systems,
   two installers, two copies of the same prompt or doc.
5. From `tracker/legacy/legacy_claims.json`, list the 30 rows with the highest claimed percentage for which you found NO code or test, with
   the code path you searched.
6. List security findings against 10-security.md S-0 to S-3, each with file and line. A real key in any file is the first line of your report.
7. List what Locus does today that the spec says it must not (for example a bespoke agent loop, Git or Syncthing sync, an edit under `packages/`).

Write the report with exactly these headings: Summary (10 lines), Guard output, Verdict table, Discard table, Duplicates, Unbacked claims,
Security, Questions for the owner, Not checked.

Style rules: do not soften findings and do not praise. If something works, say which command proved it. If you could not check
something, write NOT CHECKED and why. End with the number of files you actually opened.
