"""locus_cli.main - Locus OS CLI and installer entry point.

Handles non-interactive and interactive setup, directory hierarchy bootstrapping,
and configuration generation across Windows, Linux, and macOS.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
import sys
from typing import Any

import yaml

logger = logging.getLogger("locus_cli")

CANONICAL_VAULT_DIRS: list[str] = [
    "00-System",
    "01-Projects",
    "02-Areas",
    "03-Resources",
    "04-Captures",
    "05-Daily",
    "06-Content",
    "07-Archives",
]

DEFAULT_CONFIG_TEMPLATE = """# Locus OS Configuration
locus:
  version: "0.1.0"
  mode: {mode}
  timezone: "{timezone}"
  scheduler:
    enabled: true
    provider: "apscheduler"
  channel:
    telegram:
      enabled: false
  vault:
    path: "{vault_path}"
"""


def _set_posix_permissions(path: Path, mode: int) -> None:
    """Set filesystem permissions on POSIX systems (no-op on Windows)."""
    if sys.platform != "win32":
        try:
            os.chmod(path, mode)
        except OSError as e:
            logger.debug("Failed to set permissions %o on %s: %s", mode, path, e)


def load_answers(answers_path: Path) -> dict[str, Any]:
    """Load configuration answers from a JSON or YAML file."""
    if not answers_path.is_file():
        raise FileNotFoundError(f"Answers file not found: {answers_path}")

    content = answers_path.read_text(encoding="utf-8")
    suffix = answers_path.suffix.lower()

    if suffix in (".json",):
        return json.loads(content)
    try:
        data = yaml.safe_load(content)
        return data if isinstance(data, dict) else {}
    except yaml.YAMLError:
        return json.loads(content)


def init_locus_home(
    locus_home: Path,
    vault_root: Path | None = None,
    mode: str = "local",
    custom_answers: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Bootstrap LOCUS_HOME directory, vault folders, jobs/, and config.yaml.

    Safe to re-run: existing files, jobs, and configs are strictly preserved (R8).
    """
    answers = custom_answers or {}
    mode = answers.get("mode", mode)
    timezone = answers.get("timezone", "Asia/Kolkata")

    # 1. Initialize LOCUS_HOME
    locus_home = locus_home.expanduser().resolve()
    locus_home.mkdir(parents=True, exist_ok=True)
    _set_posix_permissions(locus_home, 0o700)

    # 2. Initialize jobs directory
    jobs_dir = locus_home / "jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)

    # 3. Initialize vault root and canonical directories
    if vault_root is None:
        custom_vault = answers.get("vault_path")
        if custom_vault:
            vault_root = Path(custom_vault).expanduser().resolve()
        else:
            vault_root = locus_home / "vault"
    else:
        vault_root = vault_root.expanduser().resolve()

    vault_root.mkdir(parents=True, exist_ok=True)
    created_vault_dirs: list[str] = []
    for d in CANONICAL_VAULT_DIRS:
        sub = vault_root / d
        if not sub.exists():
            sub.mkdir(parents=True, exist_ok=True)
            created_vault_dirs.append(d)

    # 4. Initialize config.yaml if missing
    config_file = locus_home / "config.yaml"
    config_created = False
    if not config_file.exists():
        vault_path_str = str(vault_root).replace("\\", "/")
        config_text = DEFAULT_CONFIG_TEMPLATE.format(
            mode=mode,
            timezone=timezone,
            vault_path=vault_path_str,
        )
        config_file.write_text(config_text, encoding="utf-8")
        config_created = True

    # 5. Initialize .env if missing (mode 0600)
    env_file = locus_home / ".env"
    env_created = False
    if not env_file.exists():
        env_file.write_text(
            "# Locus Environment Secrets (permissions 0600)\n"
            "# Real API keys and credentials live here and are never committed to git.\n",
            encoding="utf-8",
        )
        _set_posix_permissions(env_file, 0o600)
        env_created = True

    return {
        "locus_home": str(locus_home),
        "vault_root": str(vault_root),
        "jobs_dir": str(jobs_dir),
        "config_file": str(config_file),
        "config_created": config_created,
        "env_file": str(env_file),
        "env_created": env_created,
        "created_vault_dirs": created_vault_dirs,
    }


def run_installer(argv: list[str] | None = None) -> int:
    """Run Locus installer CLI with non-interactive and answers support."""
    parser = argparse.ArgumentParser(
        prog="locus-install",
        description="Locus OS installer and environment bootstrapper",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Non-interactive installation accepting defaults (R9)",
    )
    parser.add_argument(
        "--answers",
        type=Path,
        default=None,
        help="Path to JSON/YAML answers file for unattended installation (R9)",
    )
    parser.add_argument(
        "--locus-home",
        type=Path,
        default=None,
        help="Target LOCUS_HOME directory (default: ~/.locus or $LOCUS_HOME)",
    )
    parser.add_argument(
        "--vault-root",
        type=Path,
        default=None,
        help="Target vault root directory (default: <LOCUS_HOME>/vault)",
    )
    parser.add_argument(
        "--mode",
        choices=["local", "vm", "hybrid"],
        default="local",
        help="Installation topology mode (R2)",
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Run interactive or answers-driven setup wizard (modes and API keys)",
    )
    parser.add_argument(
        "--doctor",
        action="store_true",
        help="Run diagnostic checks on environment and dependencies (R7)",
    )
    parser.add_argument(
        "--setup-telegram",
        "--telegram-setup",
        action="store_true",
        dest="setup_telegram",
        help="Run Telegram pairing setup wizard (R6, S-1)",
    )

    args = parser.parse_args(argv)

    answers: dict[str, Any] = {}
    if args.answers:
        try:
            answers = load_answers(args.answers)
        except Exception as e:
            sys.stderr.write(f"Error loading answers file: {e}\n")
            return 1

    # Resolve locus_home
    if args.locus_home:
        home_path = args.locus_home
    elif "LOCUS_HOME" in os.environ and os.environ["LOCUS_HOME"].strip():
        home_path = Path(os.environ["LOCUS_HOME"])
    else:
        home_path = Path.home() / ".locus"

    vault_path = args.vault_root

    if getattr(args, "setup_telegram", False):
        from locus_cli.telegram_setup import run_telegram_setup

        try:
            run_telegram_setup(locus_home=home_path)
            return 0
        except Exception as e:
            sys.stderr.write(f"Telegram setup failed: {e}\n")
            return 1

    if args.doctor:
        from locus_cli.doctor import run_doctor

        return run_doctor(locus_home=home_path, vault_root=vault_path)

    if args.setup:
        from locus_cli.setup import run_setup_wizard

        try:
            run_setup_wizard(
                locus_home=home_path,
                vault_root=vault_path,
                non_interactive=args.yes,
                answers=answers,
            )
            return 0
        except Exception as e:
            sys.stderr.write(f"Setup failed: {e}\n")
            return 1

    # Execute initialization
    try:
        result = init_locus_home(
            locus_home=home_path,
            vault_root=vault_path,
            mode=args.mode,
            custom_answers=answers,
        )
    except Exception as e:
        sys.stderr.write(f"Installation failed: {e}\n")
        return 1

    print(f"[PASS] LOCUS_HOME initialized at: {result['locus_home']}")
    print(f"[PASS] Vault hierarchy initialized at: {result['vault_root']}")
    print(f"[PASS] Jobs directory ready at: {result['jobs_dir']}")
    if result["config_created"]:
        print(f"[PASS] Default config written: {result['config_file']}")
    else:
        print(f"[PASS] Existing config preserved: {result['config_file']}")

    if result["env_created"]:
        print(f"[PASS] Secrets environment file created: {result['env_file']}")
    else:
        print(f"[PASS] Existing secrets file preserved: {result['env_file']}")

    print("Locus OS installation completed successfully.")
    return 0


def main() -> None:
    """CLI entry point."""
    sys.exit(run_installer(sys.argv[1:]))


if __name__ == "__main__":
    main()
