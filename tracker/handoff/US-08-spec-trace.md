# US-08 Spec Trace

| spec line / source | the sentence quoted word for word | verdict | mechanism / file:line | test name |
|---|---|---|---|---|
| SPEC §12.1-12.5 line 4217 | "SchedulerProvider default = node-cron + APScheduler" | LOCUS-NEW | sidecar/scheduler.py:48, 226 | tests/unit/test_scheduler.py::test_scheduler_registers_in_registry |
| SPEC D-15 errata | "Jobs are YAML definitions under LOCUS_HOME/jobs/<job_id>.yaml" | LOCUS-NEW | sidecar/scheduler.py:84-103 | tests/unit/test_scheduler.py::test_loads_research_jobs_from_yaml |
| SPEC §26.1 / D-15 | "unattended via run_pi_turn(prompt=job.prompt, session_id='cron_<job_id>')... saved to vault" | LOCUS-NEW | sidecar/scheduler.py:164-215 | tests/unit/test_scheduler.py::test_job_execution_invokes_pi_turn_and_writes_vault_file |
| SPEC 04 line 27 | "Never fatal: mirroring, notification, and logging failures are logged and swallowed" | LOCUS-NEW | sidecar/scheduler.py:186-198 | tests/unit/test_scheduler.py::test_job_failure_does_not_block_scheduler_and_records_audit |
| SPEC §03 / §08 F-0125 | "When a feature's enabled switch is false ... jobs are not scheduled" | LOCUS-NEW | sidecar/scheduler.py:108-112, 168-169 | tests/unit/test_scheduler.py::test_disabled_scheduler_suppresses_jobs |
