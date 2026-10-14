# 05 - Installer, setup wizard, Telegram `/setup` (one command must do the whole setup)

Source: the owner's original instruction. The decomposition spec only has `locus setup` (first-run wizard, section 2.x), `locus doctor`
and `locus gateway install` (section 8.1-8.10); it contains no installer, no `/setup`, and no pairing. So R1-R10 are OWNER
requirements with no spec section: tracker F-0082 (install script), F-0083 (Telegram setup), F-0085 (VM backend), F-0086 (deployment).
Earlier AI reports called all of it done. Treat it as unverified.

## Requirements (numbered so the tracker and handoffs can cite them)
- **R1** One entry point per OS: `install.ps1` (Windows), `install.sh` (Linux, macOS, VM). It does the entire setup and ends by running
  `locus doctor`. The CLI is not the only interface, so nothing may be left for "later in the terminal".
- **R2** First question: mode `local`, `vm`, or `hybrid` (backend on a VM, TUI on this computer). The mode only changes config and
  which services start (04-runtime-and-channels.md).
- **R3** API keys: asks for each LLM provider key, the Telegram bot token, and any channel token. Validates each with one cheap live
  call before saving. Writes only to `LOCUS_HOME/.env` (file mode 0600). Never to the repo, a log, a prompt, or terminal history
  (input is masked).
- **R4** An LLM on the VM may be finished later from Telegram with `/setup`: the key travels through the secret-reference flow (spec
  section 18: opaque secret reference, 5-minute timeout, 15-minute cleanup, consumed on persist); the message that carried it is
  deleted; it is never echoed or logged.
- **R5** Pi's own TUI setup and login are kept and keep working. Locus's wizard is additional and never replaces or hides Pi's.
- **R6** Telegram setup includes SECURE pairing (10-security.md S-1): a one-time code shown on the machine, entered in the bot, valid
  10 minutes; the owner id is stored in `LOCUS_HOME`; nobody else is ever paired automatically.
- **R7** `locus doctor` at the end and on demand. One PASS/FAIL line each, with the fix: Node and Python versions, Docker, free ports,
  Neo4j / Postgres / CouchDB reachable, sidecar `/health`, Pi bridge flags present, vault writable, keys present, Telegram `getMe`,
  and every registered provider's `health_check()`.
- **R8** Re-running is safe: existing config and keys are kept; `--reconfigure <section>` changes one section; nothing is
  overwritten without a prompt.
- **R9** Non-interactive: `--yes --answers <file>` (or environment variables) runs with zero prompts, so a VM and CI can install unattended.
- **R10** Windows, Linux, and macOS all work. `pathlib` everywhere; no bash-only step on the Windows path; no drive letters or
  `/home/...` in code.

## How an agent builds an installer task
1. Run `/grill-me` first (AGENTS.md law 13). Always-open questions: supported VM images, systemd versus Docker for the services,
   where the answers file lives, which channels are in the first release.
2. Put the logic in Python (`locus_cli/`); `install.ps1` and `install.sh` only bootstrap Python and call it. One implementation, two
   thin launchers.
3. Evidence: a non-interactive install in a clean container or VM, the `locus doctor` output, a restart, then a second run of the
   installer. Real output in the handoff.
4. Never use the owner's real keys in a test. Tests use fake tokens against a stub Telegram API. The owner runs the last live check.

## Current state (2026-10-05, from earlier reports; NOT verified)
- Claimed done: install scripts, a 20-category Telegram `/setup`, "First-Touch Auto-Pairing", hybrid mode, systemd/Docker generation.
- Known wrong: first-touch pairing IS the vulnerability S-1 (the first stranger to message the bot becomes the owner); CouchDB is
  published with a default password (S-2). One tracker row even says "100%" in one column and "CRITICAL: No install scripts exist!"
  in another. Treat F-0082, F-0083, F-0085, F-0086 as level 0 until `verify.py` says otherwise.
