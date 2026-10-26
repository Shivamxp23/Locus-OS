# US-62 Spec Trace — §8.1-8.10: CLI Commands, Multi-Surface Management, Telegram Settings & Headless VM Topology

Feature: F-0031 | Verdict: AUGMENT | Author model: Claude Opus 4.6

| # | Spec sentence (verbatim) | Verdict | File:line | Test |
|---|---|---|---|---|
| 1 | `FUNCTION locus_cli_entrypoint(argv):` | AUGMENT | locus_cli/main.py:117-215 | test_locus_cli_entrypoint_run_and_subcommands |
| 2 | `parser = create_locus_argparser()` | AUGMENT | locus_cli/main.py:43-114 | test_create_locus_argparser_subcommands |
| 3 | `IF argv.length == 0 OR argv[0] == "run": RETURN exec_pi_tui(args=argv, extension="locus-extension")` | AUGMENT | locus_cli/main.py:27-40, 123-126 | test_locus_cli_entrypoint_run_and_subcommands |
| 4 | `CASE "setup": IF parser.has_flag("--non-interactive"): RETURN run_headless_setup(env_file=parser.get("--env-file")) ELSE: RETURN run_locus_onboarding_wizard(environment="cli")` | AUGMENT | locus_cli/main.py:130-142 | test_create_locus_argparser_subcommands |
| 5 | `CASE "config": action = parser.get("action") // get, set, check, export` | AUGMENT | locus_cli/main.py:144-160, locus_cli/config.py:12-32 | test_config_get_set_export_operations |
| 6 | `CASE "doctor": probe_results = run_full_diagnostics(verbose=parser.has_flag("--full")) IF parser.has_flag("--json"): RETURN print_json(probe_results) ELSE: RETURN render_cli_doctor_table(probe_results)` | AUGMENT | locus_cli/main.py:162-186, locus_cli/doctor.py:300-367 | test_create_locus_argparser_subcommands, test_cli_doctor_diagnostics_provider |
| 7 | `CASE "gateway": cmd = parser.get("cmd") // run, start, stop, restart, status` | AUGMENT | locus_cli/main.py:188-204, locus_cli/gateway_service.py:12-50 | test_gateway_service_manager_lifecycle |
| 8 | `CASE "cron": cmd = parser.get("cmd") // list, trigger, pause, resume` | AUGMENT | locus_cli/main.py:206-209 | test_create_locus_argparser_subcommands |
| 9 | `CASE "life": cmd = parser.get("cmd") // dcs, mode, factions` | AUGMENT | locus_cli/main.py:211-218 | test_locus_cli_entrypoint_run_and_subcommands |
| 10 | `// Notify Python sidecar to hot-reload provider: sidecar_client.post("/system/reload", { "subsystem": subsystem })` | AUGMENT | sidecar/service.py:4785-4799, sidecar/providers/cli_doctor_diagnostics.py:65-74 | test_service_system_reload_and_config |
| 11 | `IF data == "locus:cmd:doctor": results = sidecar_client.get("/system/doctor")` | AUGMENT | sidecar/service.py:4770-4783, sidecar/providers/cli_doctor_diagnostics.py:44-63 | test_service_system_doctor |
| 12 | `Provider Interface: MultiSurfaceCLI / Off-switch: locus.cli_doctor_diagnostics.enabled returning 503` | AUGMENT | sidecar/providers/cli_doctor_diagnostics.py:40-42, sidecar/service.py:4746-4830 | test_cli_doctor_diagnostics_provider_off_switch, test_service_system_off_switch_503 |

## Scope check
`git diff main...HEAD --stat` files:
- `locus_cli/main.py` — §8.1-8.10 CLI subcommands parser and entry point
- `locus_cli/config.py` — §8.1-8.10 persistent configuration and secret helpers
- `locus_cli/gateway_service.py` — §8.1-8.10 gateway daemon manager
- `sidecar/providers/cli_doctor_diagnostics.py` — Base and Default CLIDoctorDiagnosticsProvider
- `sidecar/providers/__init__.py` — providers package re-exports
- `sidecar/service.py` — REST endpoints (`/system/doctor`, `/system/reload`, `/system/config`) with 503 off-switch
- `tests/unit/test_cli_doctor_diagnostics.py` — unit tests for rows 1-9, 12
- `tests/integration/test_cli_doctor_diagnostics_service.py` — integration tests for rows 10-12
- `tracker/features.yaml` — updated evidence for F-0031

No file or behaviour outside the spec trace.
