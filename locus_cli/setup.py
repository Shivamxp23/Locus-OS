"""locus_cli.setup - Interactive and non-interactive setup wizard for Locus OS.

Collects topology mode (R2), prompts for API keys with live authentication check (R3),
persists secrets strictly into LOCUS_HOME/.env with 0600 permissions (S-0),
and guarantees safe re-runs without clobbering existing configs (R8).
"""

from __future__ import annotations

import getpass
import json
import logging
import os
from pathlib import Path
import sys
from typing import Any, Callable
import urllib.error
import urllib.request

import yaml

from locus_cli.main import init_locus_home

logger = logging.getLogger("locus_cli.setup")

SUPPORTED_MODES = ["local", "vm", "hybrid"]

PROVIDER_ENV_VARS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "google": "GEMINI_API_KEY",
    "telegram": "TELEGRAM_BOT_TOKEN",
}


def _set_posix_permissions(path: Path, mode: int) -> None:
    """Set filesystem permissions on POSIX systems (no-op on Windows)."""
    if sys.platform != "win32":
        try:
            os.chmod(path, mode)
        except OSError as e:
            logger.debug("Failed to set permissions %o on %s: %s", mode, path, e)


def validate_key(
    provider: str,
    api_key: str,
    custom_validator: Callable[[str, str], tuple[bool, str]] | None = None,
) -> tuple[bool, str]:
    """Perform a lightweight live authentication check for an API key.

    Supports custom_validator for offline/mock testing without live network calls.
    """
    key = api_key.strip()
    if not key:
        return False, "API key cannot be empty"

    if custom_validator is not None:
        return custom_validator(provider, key)

    # Built-in lightweight live checks
    try:
        if provider == "anthropic":
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/models",
                headers={
                    "x-api-key": key,
                    "anthropic-version": "2023-06-01",
                    "User-Agent": "Locus-Installer/1.0",
                },
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    return True, "Anthropic API key verified"
        elif provider == "openai":
            req = urllib.request.Request(
                "https://api.openai.com/v1/models",
                headers={
                    "Authorization": f"Bearer {key}",
                    "User-Agent": "Locus-Installer/1.0",
                },
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    return True, "OpenAI API key verified"
        elif provider == "telegram":
            url = f"https://api.telegram.org/bot{key}/getMe"
            req = urllib.request.Request(url, headers={"User-Agent": "Locus-Installer/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    if data.get("ok"):
                        username = data.get("result", {}).get("username", "bot")
                        return True, f"Telegram bot @{username} verified"
        elif provider == "google":
            url = f"https://generativelanguage.googleapis.com/v1/models?key={key}"
            req = urllib.request.Request(url, headers={"User-Agent": "Locus-Installer/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    return True, "Google Gemini API key verified"
        else:
            return True, f"Unknown provider {provider}, accepted without live check"
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            return False, f"Authentication failed: invalid {provider} API key (HTTP {e.code})"
        return False, f"API returned error: HTTP {e.code}"
    except Exception as e:
        return False, f"Network/connection error while checking {provider}: {e}"

    return False, f"Could not verify {provider} API key"


def load_secret_env(locus_home: Path) -> dict[str, str]:
    """Parse existing KEY=VALUE pairs from LOCUS_HOME/.env."""
    env_file = locus_home / ".env"
    if not env_file.is_file():
        return {}

    secrets: dict[str, str] = {}
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip()
            if len(v) >= 2 and ((v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'"))):
                quote = v[0]
                v = v[1:-1]
                if quote == '"':
                    v = v.replace('\\"', '"').replace('\\\\', '\\')
            if k:
                secrets[k] = v
    return secrets


def save_secret_env(locus_home: Path, new_secrets: dict[str, str]) -> Path:
    """Safely update LOCUS_HOME/.env with new secrets, enforcing mode 0600."""
    env_file = locus_home / ".env"
    existing = load_secret_env(locus_home)
    existing.update(new_secrets)

    lines = [
        "# Locus Environment Secrets (permissions 0600)",
        "# Real API keys and credentials live here and are never committed to git.",
    ]
    for k in sorted(existing.keys()):
        val = existing[k]
        # Quote values containing special characters
        if any(ch in val for ch in " #$'\"\\"):
            val_escaped = val.replace('"', '\\"')
            lines.append(f'{k}="{val_escaped}"')
        else:
            lines.append(f"{k}={val}")

    lines.append("")  # trailing newline
    env_file.write_text("\n".join(lines), encoding="utf-8")
    _set_posix_permissions(env_file, 0o600)
    return env_file


def update_config_mode(config_file: Path, mode: str) -> None:
    """Update locus.mode in config.yaml safely while preserving other keys."""
    if not config_file.is_file():
        data: dict[str, Any] = {"locus": {"version": "0.1.0", "mode": mode}}
    else:
        try:
            data = yaml.safe_load(config_file.read_text(encoding="utf-8")) or {}
        except Exception:
            data = {}

    if "locus" not in data or not isinstance(data["locus"], dict):
        data["locus"] = {}
    data["locus"]["mode"] = mode

    config_file.write_text(yaml.dump(data, sort_keys=False), encoding="utf-8")


def run_setup_wizard(
    locus_home: Path,
    vault_root: Path | None = None,
    non_interactive: bool = False,
    answers: dict[str, Any] | None = None,
    input_fn: Callable[[str], str] | None = None,
    prompt_password_fn: Callable[[str], str] | None = None,
    custom_validator: Callable[[str, str], tuple[bool, str]] | None = None,
) -> dict[str, Any]:
    """Execute the Locus setup wizard."""
    _input = input_fn or input
    _prompt_password = prompt_password_fn or getpass.getpass
    answers = answers or {}

    # 1. Initialize directory layout and baseline files
    init_res = init_locus_home(
        locus_home=locus_home,
        vault_root=vault_root,
        custom_answers=answers,
    )
    config_file = Path(init_res["config_file"])

    # Load existing secrets and config
    existing_secrets = load_secret_env(locus_home)
    existing_config: dict[str, Any] = {}
    if config_file.is_file():
        try:
            existing_config = yaml.safe_load(config_file.read_text(encoding="utf-8")) or {}
        except Exception:
            pass

    current_mode = existing_config.get("locus", {}).get("mode", "local")

    # 2. Topology mode selection (R2)
    selected_mode = answers.get("mode")
    if not selected_mode:
        if non_interactive:
            selected_mode = current_mode
        else:
            print("\n--- [Locus Topology Mode] ---")
            print("1. local  - Sidecar, Pi, and vault run locally on this machine")
            print("2. vm     - Sidecar and background jobs run on remote VM")
            print("3. hybrid - Background services run on VM, TUI runs locally")
            prompt_str = f"Select topology mode [local/vm/hybrid] (default: {current_mode}): "
            resp = _input(prompt_str).strip().lower()
            if resp in SUPPORTED_MODES:
                selected_mode = resp
            elif not resp:
                selected_mode = current_mode
            else:
                print(f"Unknown mode '{resp}', using default '{current_mode}'")
                selected_mode = current_mode

    update_config_mode(config_file, selected_mode)
    print(f"[PASS] Topology mode set to: {selected_mode}")

    # 3. Key collection and live verification (R3)
    new_secrets: dict[str, str] = {}
    print("\n--- [API Keys and Credentials] ---")

    for provider, env_var in PROVIDER_ENV_VARS.items():
        provided_key = answers.get(env_var) or answers.get(f"{provider}_key")
        already_has_key = env_var in existing_secrets and bool(existing_secrets[env_var])

        if provided_key:
            # Key passed in answers
            ok, msg = validate_key(provider, provided_key, custom_validator=custom_validator)
            if ok:
                new_secrets[env_var] = provided_key
                print(f"[PASS] {env_var}: {msg}")
            else:
                print(f"[WARN] {env_var}: validation failed ({msg})")
        elif not non_interactive:
            status_indicator = " (already configured, press Enter to keep)" if already_has_key else ""
            prompt_str = f"Enter {provider.capitalize()} API key{status_indicator}: "
            entered = _prompt_password(prompt_str).strip()
            if entered:
                ok, msg = validate_key(provider, entered, custom_validator=custom_validator)
                if ok:
                    new_secrets[env_var] = entered
                    print(f"[PASS] {msg}")
                else:
                    print(f"[WARN] Validation failed: {msg}")
                    # Allow user to save anyway if confirmed
                    keep_resp = _input("Save this key anyway? [y/N]: ").strip().lower()
                    if keep_resp == "y":
                        new_secrets[env_var] = entered

    # Save newly collected secrets
    if new_secrets:
        save_secret_env(locus_home, new_secrets)
        print(f"[PASS] Saved {len(new_secrets)} secret(s) to {locus_home / '.env'} (mode 0600)")
    else:
        print(f"[PASS] Existing secrets preserved in {locus_home / '.env'}")

    return {
        "locus_home": str(locus_home),
        "mode": selected_mode,
        "config_file": str(config_file),
        "secrets_updated": list(new_secrets.keys()),
    }


def main() -> None:
    """Entry point for python -m locus_cli.setup."""
    home_path = (
        Path(os.environ["LOCUS_HOME"])
        if "LOCUS_HOME" in os.environ and os.environ["LOCUS_HOME"].strip()
        else Path.home() / ".locus"
    )

    print("=== Locus OS Setup Wizard ===")
    run_setup_wizard(locus_home=home_path)


if __name__ == "__main__":
    main()
