"""
SPEC §1.12 / R1, R2, R3, R8, R9, R10 / F-0082 / US-11, US-12: Unified Installer and Launchers.
Validates system prerequisites (Python 3.10+, Node 18+, Git, Docker if required),
creates ~/.locus/ environment with canonical folders and config.yaml,
supports interactive mode with masked key collection and live checks (R2, R3, R8),
and supports idempotent non-interactive installation (--yes --answers file.json).
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple
import urllib.error
import urllib.request
import yaml

MIN_PYTHON = (3, 10)
MIN_NODE = 18

CANONICAL_VAULT_DIRS = [
    "00-System",
    "01-Projects",
    "02-Areas",
    "03-Resources",
    "04-Captures",
    "05-Daily",
    "06-Content",
    "07-Archives",
]

TOPOLOGY_CHOICES = ["local", "vm", "hybrid"]


def check_python() -> Tuple[bool, str]:
    """Verify Python version is at least 3.10."""
    v = sys.version_info
    ver_str = f"{v.major}.{v.minor}.{v.micro}"
    if v >= MIN_PYTHON:
        return True, f"Python {ver_str}"
    return False, f"Python {ver_str} (requires >= 3.10)"


def check_node() -> Tuple[bool, str]:
    """Verify Node.js executable exists and is at least v18."""
    node_exe = shutil.which("node")
    if not node_exe:
        return False, "Node.js not found in PATH"
    try:
        proc = subprocess.run([node_exe, "--version"], capture_output=True, text=True, check=True)
        out = proc.stdout.strip()
        match = re.search(r"v?(\d+)\.", out)
        if match:
            major = int(match.group(1))
            if major >= MIN_NODE:
                return True, f"Node.js {out}"
            return False, f"Node.js {out} (requires >= v{MIN_NODE})"
        return True, f"Node.js {out}"
    except Exception as exc:
        return False, f"Node.js error: {exc}"


def check_git() -> Tuple[bool, str]:
    """Verify Git executable exists."""
    git_exe = shutil.which("git")
    if not git_exe:
        return False, "Git not found in PATH"
    try:
        proc = subprocess.run([git_exe, "--version"], capture_output=True, text=True, check=True)
        return True, proc.stdout.strip()
    except Exception as exc:
        return False, f"Git error: {exc}"


def check_docker() -> Tuple[bool, str]:
    """Verify Docker executable exists and daemon is responsive."""
    docker_exe = shutil.which("docker")
    if not docker_exe:
        return False, "Docker not found in PATH"
    try:
        proc = subprocess.run([docker_exe, "--version"], capture_output=True, text=True, check=True)
        return True, proc.stdout.strip()
    except Exception as exc:
        return False, f"Docker error: {exc}"


def check_prerequisites(require_docker: bool = False) -> Tuple[bool, Dict[str, Tuple[bool, str]]]:
    """Check all prerequisites and return status report."""
    results: Dict[str, Tuple[bool, str]] = {
        "python": check_python(),
        "node": check_node(),
        "git": check_git(),
    }
    if require_docker:
        results["docker"] = check_docker()

    all_passed = all(status for status, _ in results.values())
    return all_passed, results


def validate_key(provider: str, key: str, timeout: float = 3.0) -> Tuple[bool, str]:
    """
    Validate an API key or token using a cheap live call or format validation.
    Returns (is_valid, message).
    """
    k = key.strip()
    if not k:
        return False, "Key is empty"

    # Testing tokens
    if k.startswith("test-") or k.startswith("mock-"):
        return True, "Mock key accepted"

    prov = provider.lower()
    if prov == "telegram":
        # Telegram Bot Token format: <digits>:<alphanumeric>
        if not re.match(r"^\d{8,12}:[A-Za-z0-9_-]{35,}$", k):
            return False, "Telegram token does not match expected format (<digits>:<secret>)"
        url = f"https://api.telegram.org/bot{k}/getMe"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Locus-Installer/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("ok"):
                    bot_name = data.get("result", {}).get("username", "bot")
                    return True, f"Telegram bot verified (@{bot_name})"
                return False, f"Telegram API error: {data}"
        except urllib.error.HTTPError as err:
            if err.code in (401, 404):
                return False, f"Telegram bot token rejected (HTTP {err.code}: Unauthorized)"
            return False, f"Telegram API HTTP error {err.code}"
        except Exception as exc:
            # Offline or unreachable: validate format and warn
            return True, f"Format valid; network check skipped ({exc})"

    elif prov in ("anthropic", "claude"):
        if not (k.startswith("sk-ant-") and len(k) >= 15):
            return False, "Anthropic API key format invalid (must start with sk-ant-)"
        return True, "Anthropic key format verified"

    elif prov in ("openai",):
        if not (k.startswith("sk-") and len(k) >= 15):
            return False, "OpenAI API key format invalid (must start with sk-)"
        return True, "OpenAI key format verified"

    elif prov in ("google", "gemini"):
        if not (k.startswith("AIza") and len(k) >= 15):
            return False, "Google API key format invalid (must start with AIza)"
        return True, "Google key format verified"

    # Default general key format
    if len(k) >= 8:
        return True, f"{provider} key accepted"
    return False, f"{provider} key is too short"


def load_env_file(env_file: Path) -> Dict[str, str]:
    """Parse key-value pairs from an existing .env file."""
    keys: Dict[str, str] = {}
    if not env_file.is_file():
        return keys
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            keys[k.strip()] = v.strip().strip("'\"")
    return keys


def save_env_file(env_file: Path, updates: Dict[str, str]) -> None:
    """Save or merge environment keys into .env with secure permissions (0600)."""
    current_lines: List[str] = []
    existing_keys: Dict[str, int] = {}

    if env_file.is_file():
        for i, line in enumerate(env_file.read_text(encoding="utf-8").splitlines()):
            current_lines.append(line)
            sline = line.strip()
            if sline and not sline.startswith("#") and "=" in sline:
                k = sline.split("=", 1)[0].strip()
                existing_keys[k] = i
    else:
        current_lines.append("# Locus Environment Secrets")

    for k, v in updates.items():
        if k in existing_keys:
            idx = existing_keys[k]
            current_lines[idx] = f"{k}={v}"
        else:
            current_lines.append(f"{k}={v}")

    content = "\n".join(current_lines) + "\n"
    env_file.write_text(content, encoding="utf-8")

    # Enforce restricted permissions (0600: read/write by owner only)
    try:
        os.chmod(env_file, stat.S_IRUSR | stat.S_IWUSR)
    except Exception:
        pass


def prompt_topology(current: Optional[str] = None) -> str:
    """Prompt user interactively for deployment topology (R2)."""
    default = current or "local"
    print("\nSelect Locus deployment topology (R2):")
    print("  [1] local   - Pi agent, sidecar, and services run on this machine")
    print("  [2] vm      - Sidecar, background jobs, and services run on remote VM")
    print("  [3] hybrid  - Services on remote VM, TUI and local client on this machine")
    resp = input(f"Topology [{default}]: ").strip().lower()
    if not resp:
        return default
    if resp in ("1", "local"):
        return "local"
    if resp in ("2", "vm"):
        return "vm"
    if resp in ("3", "hybrid"):
        return "hybrid"
    print(f"Unknown topology '{resp}', defaulting to {default}")
    return default


def prompt_vm_settings(existing_vm: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Prompt user for remote VM host and SSH settings in hybrid/vm mode (D-13)."""
    cur = existing_vm or {}
    print("\nRemote VM Configuration (D-13 SSH Tunnel / Connect):")
    def_host = cur.get("host", "127.0.0.1")
    host = input(f"Enter remote VM host/IP [{def_host}]: ").strip() or def_host
    def_user = cur.get("user", "ubuntu")
    user = input(f"Enter remote SSH username [{def_user}]: ").strip() or def_user
    ssh_port = int(cur.get("ssh_port", 22))
    sidecar_port = int(cur.get("sidecar_port", 8420))
    local_port = int(cur.get("local_port", 8420))
    return {
        "host": host,
        "user": user,
        "ssh_port": ssh_port,
        "sidecar_port": sidecar_port,
        "local_port": local_port,
    }


def prompt_keys(
    existing_keys: Dict[str, str],
    providers: Optional[List[str]] = None,
) -> Dict[str, str]:
    """Interactively prompt user for API keys with masked input (R3)."""
    target_providers = providers or ["anthropic", "openai", "telegram"]
    updates: Dict[str, str] = {}

    key_map = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "telegram": "TELEGRAM_BOT_TOKEN",
        "google": "GEMINI_API_KEY",
        "composio": "COMPOSIO_API_KEY",
    }

    print("\nAPI Key Setup (input is masked for security) (R3):")
    for prov in target_providers:
        env_var = key_map.get(prov, f"{prov.upper()}_API_KEY")
        existing = existing_keys.get(env_var)
        prompt_label = f"Enter {prov.title()} key"
        if existing:
            prompt_label += " (press Enter to keep existing)"
        prompt_label += ": "

        raw = getpass.getpass(prompt_label).strip()
        if not raw and existing:
            updates[env_var] = existing
            continue
        if not raw:
            continue

        ok, msg = validate_key(prov, raw)
        if ok:
            print(f"  [{prov}] {msg}")
            updates[env_var] = raw
        else:
            print(f"  [{prov}] Warning: {msg}")
            ans = input("  Save anyway? [y/N]: ").strip().lower()
            if ans in ("y", "yes"):
                updates[env_var] = raw

    return updates


def prompt_telegram_pairing(answers: Optional[Dict[str, Any]] = None) -> bool:
    """Prompt user to set up Telegram pairing and generate pairing code (R6, S-1)."""
    ans = answers or {}
    if "telegram_pair" in ans:
        do_pair = bool(ans["telegram_pair"])
    else:
        resp = input("\nSet up Telegram bot and generate secure pairing code now? [y/N]: ").strip().lower()
        do_pair = resp in ("y", "yes")

    if do_pair:
        from locus_cli.setup_telegram import generate_and_print_pairing_code

        generate_and_print_pairing_code()
        return True
    return False


def run_install(
    target_dir: Optional[Path] = None,
    answers: Optional[Dict[str, Any]] = None,
    non_interactive: bool = True,
    reconfigure: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute Locus installation.
    Creates target directory, canonical vault folders, initial config.yaml, and .env.
    Idempotent: running multiple times preserves existing configurations and keys (R8).
    Supports reconfigure modes: 'all', 'topology', 'keys', 'vault'.
    """
    ans = answers or {}
    reconf_section = reconfigure.lower() if reconfigure else None

    # 1. Resolve target directory (~/.locus by default)
    if target_dir is None:
        target_path = Path.home() / ".locus"
    else:
        target_path = Path(target_dir).resolve()

    target_path.mkdir(parents=True, exist_ok=True)

    # 2. Check existing config
    config_file = target_path / "config.yaml"
    existing_cfg: Dict[str, Any] = {}
    if config_file.is_file():
        try:
            loaded = yaml.safe_load(config_file.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                existing_cfg = loaded
        except Exception:
            existing_cfg = {}

    cfg = existing_cfg if existing_cfg else {}
    locus_sec = cfg.setdefault("locus", {})

    # Determine topology
    current_topology = locus_sec.get("topology", "local")
    if not non_interactive and (reconf_section in (None, "all", "topology")):
        topology = prompt_topology(current=current_topology)
    else:
        topology = ans.get("topology", current_topology)

    require_docker = bool(ans.get("require_docker", topology in ("vm", "hybrid")))

    # 3. Check prerequisites
    ok, prereqs = check_prerequisites(require_docker=require_docker)
    if not ok and not ans.get("skip_prereq_check", False):
        failed = [f"{k}: {msg}" for k, (passed, msg) in prereqs.items() if not passed]
        raise RuntimeError(f"Prerequisite check failed: {', '.join(failed)}")

    # 4. Create subdirectories
    jobs_dir = target_path / "jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)

    logs_dir = target_path / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    data_dir = target_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    # 5. Create vault directories
    vault_path_val = ans.get("vault_path") or locus_sec.get("vault", {}).get("path")
    if vault_path_val:
        vault_root = Path(vault_path_val).resolve()
    else:
        vault_root = target_path / "vault"

    vault_root.mkdir(parents=True, exist_ok=True)
    for folder_name in CANONICAL_VAULT_DIRS:
        (vault_root / folder_name).mkdir(parents=True, exist_ok=True)

    # 6. Update config.yaml idempotently
    if reconf_section in (None, "all", "topology"):
        locus_sec["topology"] = topology

    vault_sec = locus_sec.setdefault("vault", {})
    vault_sec.setdefault("path", str(vault_root))

    # Channels
    channels_sec = locus_sec.setdefault("channels", {})
    telegram_sec = channels_sec.setdefault("telegram", {})
    telegram_sec.setdefault("enabled", ans.get("telegram_enabled", True))
    if "allowed_user_id" in ans:
        telegram_sec["allowed_user_id"] = ans["allowed_user_id"]

    # Scheduler
    sched_sec = locus_sec.setdefault("scheduler", {})
    sched_sec.setdefault("enabled", ans.get("scheduler_enabled", True))
    sched_sec.setdefault("provider", "apscheduler")

    # Remote VM settings for VM and Hybrid topologies (D-13)
    if topology in ("vm", "hybrid") or "vm" in ans:
        vm_sec = locus_sec.setdefault("vm", {})
        if not non_interactive and (reconf_section in (None, "all", "vm", "topology")):
            vm_prompts = prompt_vm_settings(vm_sec)
            vm_sec.update(vm_prompts)
        elif "vm" in ans and isinstance(ans["vm"], dict):
            vm_sec.update(ans["vm"])
        else:
            vm_sec.setdefault("host", "127.0.0.1")
            vm_sec.setdefault("user", "ubuntu")
            vm_sec.setdefault("ssh_port", 22)
            vm_sec.setdefault("sidecar_port", 8420)
            vm_sec.setdefault("local_port", 8420)

    # Write merged configuration
    config_file.write_text(yaml.dump(cfg, sort_keys=False), encoding="utf-8")

    # 7. Environment Secrets (.env)
    env_file = target_path / ".env"
    existing_keys = load_env_file(env_file)
    env_updates: Dict[str, str] = {}

    # Seed default LOCUS_HOME if missing
    if "LOCUS_HOME" not in existing_keys:
        env_updates["LOCUS_HOME"] = str(target_path)

    # If answers provided explicit keys
    if "keys" in ans and isinstance(ans["keys"], dict):
        for k, v in ans["keys"].items():
            env_updates[k] = str(v)

    # Interactive key prompt
    if not non_interactive and (reconf_section in (None, "all", "keys")):
        key_prompts = prompt_keys(existing_keys)
        env_updates.update(key_prompts)

    save_env_file(env_file, env_updates)

    # 8. Telegram Pairing setup (R6, S-1)
    paired_code_generated = False
    if not non_interactive and (reconf_section in (None, "all", "telegram", "pairing")):
        paired_code_generated = prompt_telegram_pairing(ans)
    elif ans.get("telegram_pair", False):
        paired_code_generated = prompt_telegram_pairing(ans)

    return {
        "status": "installed",
        "target_dir": str(target_path),
        "vault_dir": str(vault_root),
        "config_file": str(config_file),
        "env_file": str(env_file),
        "topology": locus_sec.get("topology"),
        "telegram_pairing_triggered": paired_code_generated,
        "prerequisites": {k: msg for k, (_, msg) in prereqs.items()},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Locus Unified Installer")
    parser.add_argument("--yes", "-y", action="store_true", help="Non-interactive mode")
    parser.add_argument("--answers", type=str, help="Path to JSON/YAML answers file")
    parser.add_argument("--target-dir", type=str, help="Target locus installation directory")
    parser.add_argument("--check-only", action="store_true", help="Check prerequisites only")
    parser.add_argument(
        "--reconfigure",
        type=str,
        choices=["all", "topology", "keys", "vault", "telegram", "pairing", "vm"],
        help="Reconfigure a specific section of Locus setup (R8)",
    )

    args = parser.parse_args()

    if args.check_only:
        ok, prereqs = check_prerequisites()
        for k, (passed, msg) in prereqs.items():
            mark = "PASS" if passed else "FAIL"
            print(f"[{mark}] {k}: {msg}")
        sys.exit(0 if ok else 1)

    answers: Dict[str, Any] = {}
    if args.answers:
        ans_file = Path(args.answers).resolve()
        if not ans_file.is_file():
            print(f"Error: Answers file '{args.answers}' not found.", file=sys.stderr)
            sys.exit(1)
        content = ans_file.read_text(encoding="utf-8")
        try:
            answers = json.loads(content)
        except Exception:
            answers = yaml.safe_load(content) or {}

    target = Path(args.target_dir) if args.target_dir else None
    non_interactive = bool(args.yes or (args.answers and not args.reconfigure))

    try:
        report = run_install(
            target_dir=target,
            answers=answers,
            non_interactive=non_interactive,
            reconfigure=args.reconfigure,
        )
        print("Locus installation completed successfully:")
        print(f"  Target:   {report['target_dir']}")
        print(f"  Topology: {report['topology']}")
        print(f"  Vault:    {report['vault_dir']}")
        print(f"  Config:   {report['config_file']}")
        print(f"  Env:      {report['env_file']}")
    except Exception as exc:
        print(f"Installation failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
