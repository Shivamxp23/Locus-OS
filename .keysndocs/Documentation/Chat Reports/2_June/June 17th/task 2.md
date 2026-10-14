# Locus Gateway Setup — Task Tracker

## Component 1: Project Skeleton
- [x] `pyproject.toml`
- [x] `locus_cli/__init__.py`
- [x] `locus_cli/main.py` (CLI entry point)

## Component 2: Config & Environment Management
- [x] `locus_cli/config.py`

## Component 3: Terminal UI Helpers
- [x] `locus_cli/colors.py` (+ Windows UTF-8 fix)
- [x] `locus_cli/cli_output.py`
- [x] `locus_cli/secret_prompt.py` (masked password input)
- [x] `locus_cli/curses_ui.py`

## Component 4: Platform Registry & Gateway Config
- [x] `gateway/__init__.py`
- [x] `gateway/platform_registry.py`
- [x] `gateway/config.py`

## Component 5: Setup Wizard
- [x] `locus_cli/setup.py`

## Component 6: Gateway Platform Setup (All Platforms)
- [x] `locus_cli/setup_gateway.py`

## Verification
- [x] `pip install -e .` — successful
- [x] `locus version` → `Locus v0.1.0`
- [x] `locus config` → shows config paths + platform status
- [x] `locus setup` → full wizard with banner + gateway + summary
- [x] `locus setup gateway` → direct platform selection
- [x] Config files created in `~/.locus/`
- [x] Windows UTF-8 encoding fix for box-drawing characters

## Component 7: Gateway Service Management (Restart Logic)
- [x] `gateway/status.py` — PID file, runtime locks, terminate_pid, _pid_exists
- [x] `locus_cli/gateway_service.py` — run/start/stop/restart/status dispatcher
- [x] `locus_cli/main.py` — added `gateway` subcommand tree

## Component 8: Hermes CLI Command Catalog
- [x] Created holistic command reference (150+ commands across 20 categories)
- [x] Documented gateway restart backend architecture

## Verification (Gateway Lifecycle)
- [x] `locus gateway --help` → shows run/start/stop/restart/status/setup
- [x] `locus gateway status` → "✗ Gateway is not running"
- [x] `locus gateway run` → starts gateway with PID file + runtime lock
- [x] `locus gateway status` → "✓ Gateway is running (PID: XXXX)"
- [x] `locus gateway stop` → "✓ Gateway stopped" (SIGTERM + wait + cleanup)
- [x] `locus gateway status` → "✗ Gateway is not running" (verified clean stop)

