# P4 - Extra rules for installer, Telegram and security stories (appended to P1 automatically)

A story with `addendum: [P4]` in tracker/backlog.yaml gets this text appended to its author prompt by `backlog.py --start` and
`backlog.py --prompt P1`. Nobody pastes it by hand. The requirement texts are S-1 to S-3 in docs/agent/10-security.md and R1 to R10 in
docs/agent/05-installer-onboarding.md; the story's acceptance criteria say which ones this story covers.

---
Extra rules for this story (security and installer work):
- Never use a real key, token, password, or the owner's VM. Tests use fake values and a stub for the Telegram API.
- If you meet a real secret anywhere, stop and say so in your first sentence (10-security.md S-0).
- Any change touching Telegram must include all six pairing tests listed in 10-security.md S-1.
- Any change touching `docker-compose.yml` must pass `docker compose config` with a complete `.env` and must FAIL with a clear message when
  `COUCHDB_PASSWORD` is missing. Show both outputs. Every published port is bound to 127.0.0.1.
- Installer code lives in `locus_cli/`; `install.ps1` and `install.sh` stay thin launchers. Paths use `pathlib`. Run the installer twice
  and show both outputs; the second run must change nothing.
- The last live check (real Telegram, real VM) is the owner's: finish the handoff with the exact commands the owner must run for the
  demo and the PASS lines to expect.
