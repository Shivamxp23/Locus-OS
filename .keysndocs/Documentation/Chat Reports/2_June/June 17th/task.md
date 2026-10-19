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
