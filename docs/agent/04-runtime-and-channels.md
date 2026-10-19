# 04 - Headless runtime, cron, and channels (most of the product is NOT the terminal)

## What the owner asked for
- The backend lives on an always-on machine, normally a VM. The owner reaches it from Telegram (main channel), Discord, WhatsApp,
  or a TUI/CLI on their own computer.
- The ultimate goal: cron jobs on the VM research and write WITHOUT being prompted, then tell the owner.
- Users bring their own LLM API keys and their own VM. Nothing is wired to the owner's accounts.

## Three topologies (the installer asks which one; 05-installer-onboarding.md)
| Mode | Where it runs | Front doors |
|---|---|---|
| local | everything on the owner's computer | TUI/CLI, optional Telegram |
| vm | sidecar, databases, Pi bridge, cron, gateway on the VM | Telegram, Discord, WhatsApp, optional SSH |
| hybrid | backend on the VM, TUI on the owner's computer | TUI through a tunnel to the VM sidecar (errata D-13), plus channels |
The same code runs in all three; only config differs. Never write `if on_vm:` in feature code.

## Rules for every unattended turn (cron, channel message, conductor)
1. Start Pi only through `sidecar/pi_bridge.py::run_pi_turn`, always with `--approve --no-context-files` (AGENTS.md law 9).
2. Session ids: cron `cron_<job_id>`; Telegram one per chat (table `telegram_sessions` maps chat id to Pi session id), so a restart resumes.
3. A job never blocks the scheduler: hard timeout, output captured, failure written to the audit trail, the next run unaffected.
4. Autonomy follows `locus.security.autonomy_tier` (`readonly` | `supervised` | `full`; default `supervised`; spec 13.4). In
   `supervised` a write needs approval: the owner gets Approve/Reject buttons, no answer in 10 minutes means rejected (spec 13.5).
   So an unattended job must finish without waiting for a person: read-only work, or a result queued for approval.
5. Budget first: skip the cycle when today's LLM cost has reached 80% of the daily cap (spec 26.1 step 1, spec 28 cost model).
6. Deliver: a note in the vault (`04-Captures/`), a Telegram message, and a run record in the audit trail
   (06-vault-memory-audit.md). A job that found nothing says so; it never stays silent.
7. Never fatal: mirroring, notification, and logging failures are logged and swallowed (spec 17.x); they must not stop the loop.

## Scheduling (spec 12.1-12.5, 26.1, 28; tracker F-0056, F-0058)
- SchedulerProvider default = node-cron + APScheduler. The job store survives a restart (SQLite under `LOCUS_HOME`).
- Scheduler gate policy: aggressive (server: run flat out), normal, throttled, paused. A VM runs `aggressive`.
- Inner loop: every 90 minutes inside the active window (default 07:00-00:00), the 10 steps of spec 26.1 in order.
  `locus.brain.inner_loop.enabled=false` -> Locus only reacts. Check-ins 07:30, 13:00, 18:00, 22:00. Chat archiver 23:45.
  Timezone and times come from config; the spec's "IST" is the owner's default, not a constant in code (errata D-14).
- Owner-defined research jobs (the "ultimate goal"): a job = name, schedule, prompt, tier, allowed paths, budget, destination.
  The spec has NO section for the job format (errata D-15): the first task is a `/grill-me` (prompt P3), not code.

## Channels (spec 17.1-17.11; tracker F-0046)
- `ChannelProvider`: `name`, `initialize(config)`, `send_message(recipient, text, keyboard?)`, `send_file`, `receive_messages()` (async
  iterator), `is_connected()`, `shutdown()`; optional `send_inline_keyboard`, `send_voice`, `edit_message`.
- One registry entry per channel (`PlatformEntry`: name, label, adapter_factory, check_fn, validate_config, is_connected,
  required_env, install_hint, setup_fn, source builtin|plugin). Adding Discord or WhatsApp = one adapter + one entry, no other edits.
- Telegram is primary. Polling by default; webhook mode only with `TELEGRAM_WEBHOOK_SECRET` set (without it the webhook is open to
  anyone). Connect with up to 8 retries and exponential backoff capped at 15 s. One bot instance per token (platform lock).
  Message cap 4096 characters. Notification mode `important` by default.
- Who may talk to the bot is a security rule: 10-security.md S-1. No channel obeys an unpaired sender.
- TUI and Telegram share one session history (spec 28.1): both write the same session file.

## "Headless works" means all five, on a machine with no terminal attached
1. The sidecar and the Pi bridge start from a service (systemd or Docker), not from a person's shell.
2. A scheduled job fires on time after the whole stack is restarted.
3. Its result is in the vault and in Telegram.
4. At tier `supervised` it does not hang waiting for an approval.
5. The run is in the audit trail.
Put the commands and their real output in `tracker/handoff/F-xxxx.md`. An earlier guide (`HEADLESS_VM_AND_CRON_SETUP_GUIDE.md`)
exists in the repo; treat it as unverified until these five pass.
