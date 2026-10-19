# US-13 Spec Trace

| spec line / source | the sentence quoted word for word | verdict | mechanism / file:line | test name |
|---|---|---|---|---|
| User requirement R7 | "locus doctor at the end and on demand. One PASS/FAIL line each, with the fix: Node and Python versions, Docker, free ports, Neo4j / Postgres / CouchDB reachable, sidecar /health, Pi bridge flags present, vault writable, keys present, Telegram getMe, and every registered provider's health_check()." | LOCUS-NEW | locus_cli/doctor.py:36-320 | tests/unit/test_doctor.py::test_doctor_diagnostics_formatting_and_checks, test_doctor_vault_and_env_checks, test_doctor_exit_codes_and_criticality |
| User requirement R5 | "Pi's own TUI setup and login are kept and keep working. Locus's wizard is additional and never replaces or hides Pi's." | LOCUS-NEW | locus.bat:18-36, locus.cmd:18-36 | tests/unit/test_doctor.py::test_launcher_doctor_dispatch_and_pi_passthrough |
| User requirement R7 / demo | "Run py -3 -m locus_cli.doctor: prints diagnostic lines with [PASS]/[FAIL] status for Python, Node, Git, and vault writability, exiting 0." | LOCUS-NEW | locus_cli/doctor.py:323-371 | tests/unit/test_doctor.py::test_doctor_cli_run |
