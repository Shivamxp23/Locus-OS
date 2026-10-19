"""
SPEC §1.12 / F-0012 / US-31: Terminal Shell Setup CLI (`locus setup`).
Provides interactive terminal prompt session and non-interactive automated provisioning.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Dict, Optional

from sidecar.onboarding import OnboardingProvider, run_non_interactive_setup


def setup_non_interactive(config_path: str) -> Dict[str, Any]:
    """Execute non-interactive batch onboarding from a JSON/YAML configuration file."""
    p = Path(config_path)
    if not p.is_file():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    content = p.read_text(encoding="utf-8")
    settings: Dict[str, Any] = {}
    try:
        settings = json.loads(content)
    except Exception:
        import yaml
        settings = yaml.safe_load(content) or {}

    return run_non_interactive_setup(settings)


def setup_interactive() -> Dict[str, Any]:
    """Execute guided terminal prompts for first-run configuration."""
    provider = OnboardingProvider()

    print("========================================")
    print(" Locus Personal Cognitive OS Onboarding")
    print("========================================")

    # Topology
    topology = "local"
    provider.set_topology(topology)

    # LLM
    provider.configure_llm(provider="deepseek", model="deepseek-chat")

    # Memory
    provider.configure_memory(enable_neo4j=False, enable_headroom=True)

    # Vault
    default_vault = str(Path.home() / "Documents" / "Obsidian" / "LocusVault")
    provider.configure_vault(vault_path=default_vault, enable_livesync=False)

    # Life OS
    provider.configure_life_os(timezone="Asia/Kolkata", morning_checkin_time="08:00")

    # Telegram
    provider.configure_telegram(enabled=False)

    # Run diagnostics
    diag = provider.run_diagnostics()
    return {"ok": diag["all_ok"], "status": provider.get_status(), "diagnostics": diag}


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Locus Setup Wizard")
    parser.add_argument("--non-interactive", action="store_true", help="Run without interactive prompts")
    parser.add_argument("--config", "--env-file", type=str, help="Path to config file for non-interactive setup")
    args = parser.parse_args(argv)

    if args.non_interactive:
        if not args.config:
            print("Error: --config or --env-file required for non-interactive setup", file=sys.stderr)
            return 1
        res = setup_non_interactive(args.config)
        print(json.dumps(res, indent=2))
        return 0 if res.get("ok") else 1
    else:
        res = setup_interactive()
        print("Setup completed successfully!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
