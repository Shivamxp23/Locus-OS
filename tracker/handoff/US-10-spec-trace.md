# US-10 Spec Trace

| spec line / source | the sentence quoted word for word | verdict | mechanism / file:line | test name |
|---|---|---|---|---|
| SPEC §12.1-12.5 line 4217 / §02 / US-10 | "sidecar/service.py or CLI daemon command starts the FastAPI sidecar, Pi bridge, and scheduler in a single headless process." | LOCUS-NEW | sidecar/service.py:90-155 | tests/integration/test_service_restart.py::test_headless_service_starts_fastapi_and_scheduler |
| SPEC §12.1-12.5 / US-10 | "Job definitions and schedules persist in SQLite under LOCUS_HOME; on service restart, existing jobs are reloaded and pending jobs still trigger." | LOCUS-NEW | sidecar/scheduler.py:99-245 | tests/integration/test_service_restart.py::test_job_store_persists_in_sqlite_across_service_restart |
| SPEC §12.1-12.5 / US-10 | "Graceful shutdown flushes in-flight state and stops workers cleanly." | LOCUS-NEW | sidecar/service.py:126-133, sidecar/scheduler.py:270-272 | tests/integration/test_service_restart.py::test_headless_service_starts_fastapi_and_scheduler |
| SPEC §12.1-12.5 / US-10 | "A restart test stops and restarts the scheduler process, verifying job retention and next execution time." | LOCUS-NEW | sidecar/scheduler.py:170-220 | tests/integration/test_service_restart.py::test_job_store_persists_in_sqlite_across_service_restart |
