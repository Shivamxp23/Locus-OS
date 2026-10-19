# US-09 Spec Trace

| spec line / source | the sentence quoted word for word | verdict | mechanism / file:line | test name |
|---|---|---|---|---|
| SPEC §17.1-17.11 / §12.1-12.5 / backlog US-09 | "A finished job sends its result and its run record to the paired owner on Telegram" | AUGMENT | sidecar/scheduler.py:247, 259-293 | tests/integration/test_job_telegram_delivery.py::test_job_completion_delivers_summary_to_paired_owner_on_telegram |
| SPEC §17.1-17.11 line 3975 | "MAX_MESSAGE_LENGTH = 4096 // Telegram limit" | AUGMENT | sidecar/scheduler.py:270-276 | tests/integration/test_job_telegram_delivery.py::test_long_job_summary_truncates_under_4096_and_cites_vault_note |
| SPEC 04 line 27 | "Never fatal: mirroring, notification, and logging failures are logged and swallowed" | AUGMENT | sidecar/scheduler.py:289-291 | tests/integration/test_job_telegram_delivery.py::test_telegram_delivery_failure_is_never_fatal_to_scheduler |
