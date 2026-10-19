# Locus Gateway & Setup — Implementation Walkthrough

## Summary

Ported the messaging gateway setup wizard from `hermes-agent` into `locus-os`. This is Locus's **first source code** — the repo previously contained only documentation.

## What Was Built

### 12 New Files Across 2 Packages

```
locus-os/
├── pyproject.toml                      # Package metadata + CLI entry point
├── locus_cli/
│   ├── __init__.py                     # Package init (v0.1.0)
│   ├── main.py                         # CLI: locus setup | config | version
│   ├── config.py                       # ~/.locus/ directory, config.yaml, .env management
│   ├── colors.py                       # ANSI colors + Windows UTF-8 fix
│   ├── cli_output.py                   # print_info/success/warning/error + prompts
│   ├── secret_prompt.py                # Masked password input (Windows + POSIX)
│   ├── curses_ui.py                    # Arrow-key menus with text fallback
│   ├── setup.py                        # Full setup wizard orchestrator
│   └── setup_gateway.py               # Platform setup (5 platforms, interactive config)
└── gateway/
    ├── __init__.py
    ├── platform_registry.py            # Plugin-style platform registration
    └── config.py                       # Platform/GatewayConfig dataclasses
```

### What Was Ported from Hermes

| Locus Module | Hermes Source | What Changed |
|---|---|---|
| [colors.py](file:///c:/Users/soni8/Desktop/everything/University 2.0/Project(s)/5_Locus/locus-os/locus_cli/colors.py) | `hermes_cli/colors.py` | Added Windows UTF-8 reconfiguration |
| [cli_output.py](file:///c:/Users/soni8/Desktop/everything/University 2.0/Project(s)/5_Locus/locus-os/locus_cli/cli_output.py) | `hermes_cli/cli_output.py` | Removed `hermes_cli.secret_prompt` dep → local |
| [secret_prompt.py](file:///c:/Users/soni8/Desktop/everything/University 2.0/Project(s)/5_Locus/locus-os/locus_cli/secret_prompt.py) | `hermes_cli/secret_prompt.py` | Direct port — no changes needed |
| [curses_ui.py](file:///c:/Users/soni8/Desktop/everything/University 2.0/Project(s)/5_Locus/locus-os/locus_cli/curses_ui.py) | `hermes_cli/curses_ui.py` | Removed `hermes_cli.colors` import → local |
| [config.py](file:///c:/Users/soni8/Desktop/everything/University 2.0/Project(s)/5_Locus/locus-os/locus_cli/config.py) | `hermes_cli/config.py` (5752-5948) | Stripped from 6500 lines to ~320. Removed managed mode, sanitization, env cache complexity |
| [setup_gateway.py](file:///c:/Users/soni8/Desktop/everything/University 2.0/Project(s)/5_Locus/locus-os/locus_cli/setup_gateway.py) | `hermes_cli/gateway.py` (3966-5960) | Removed service management, Telegram auto-setup, DM pairing. Kept core platform defs + setup flow |
| [platform_registry.py](file:///c:/Users/soni8/Desktop/everything/University 2.0/Project(s)/5_Locus/locus-os/gateway/platform_registry.py) | `gateway/platform_registry.py` | Simplified — removed adapter lifecycle, focused on registration |

### What Was NOT Ported

- Gateway runtime daemon (`gateway/run.py`)
- systemd/launchd/schtasks service management
- Telegram managed bot auto-setup
- DM pairing / open access security model
- Agent/LLM pipeline
- 10+ platform adapters (only metadata for 5 platforms)

## Verified

| Test | Result |
|---|---|
| `python -m locus_cli.main version` | ✅ `Locus v0.1.0` |
| `python -m locus_cli.main config` | ✅ Shows paths + platform status |
| `python -m locus_cli.main setup` | ✅ Full wizard with banner |
| `python -m locus_cli.main setup gateway` | ✅ Direct to platform menu |
| `pip install -e .` | ✅ `locus.exe` installed to Scripts |
| Box-drawing on Windows | ✅ Fixed with UTF-8 reconfigure |

## Architecture

The setup flow works like this:

```
locus setup
  → setup.py::run_setup()
    → Prints LOCUS banner
    → Creates ~/.locus/
    → setup_gateway.py::setup_gateway()
      → _all_platforms() merges _PLATFORMS + plugin registry
      → Curses menu: "Select a platform to configure"
      → _configure_platform(selected)
        → _setup_standard_platform(): prompts for each env var
        → Saves values to ~/.locus/.env
    → Prints summary + next steps
```

The platform registry (`gateway/platform_registry.py`) allows future plugins to register new platforms without modifying core code.
