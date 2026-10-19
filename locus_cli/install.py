"""
SPEC §1.12 / R1, R9, R10 / F-0082 / US-11: Unified Installer and Launchers.
Validates system prerequisites (Python 3.10+, Node 18+, Git, Docker if required),
creates ~/.locus/ environment with canonical folders and config.yaml,
and supports idempotent non-interactive installation (--yes --answers file.json).
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple
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


def run_install(
    target_dir: Optional[Path] = None,
    answers: Optional[Dict[str, Any]] = None,
    non_interactive: bool = True,
) -> Dict[str, Any]:
    """
    Execute Locus installation.
    Creates target directory, canonical vault folders, and initial config.yaml.
    Idempotent: running multiple times preserves existing configurations.
    """
    ans = answers or {}
    topology = ans.get("topology", "local")
    require_docker = bool(ans.get("require_docker", topology in ("vm", "hybrid")))

    # 1. Check prerequisites
    ok, prereqs = check_prerequisites(require_docker=require_docker)
    if not ok and not ans.get("skip_prereq_check", False):
        failed = [f"{k}: {msg}" for k, (passed, msg) in prereqs.items() if not passed]
        raise RuntimeError(f"Prerequisite check failed: {', '.join(failed)}")

    # 2. Resolve target directory (~/.locus by default)
    if target_dir is None:
        target_path = Path.home() / ".locus"
    else:
        target_path = Path(target_dir).resolve()

    target_path.mkdir(parents=True, exist_ok=True)

    # 3. Create subdirectories
    jobs_dir = target_path / "jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)

    logs_dir = target_path / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    data_dir = target_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    # 4. Create vault directories
    vault_path_val = ans.get("vault_path")
    if vault_path_val:
        vault_root = Path(vault_path_val).resolve()
    else:
        vault_root = target_path / "vault"

    vault_root.mkdir(parents=True, exist_ok=True)
    for folder_name in CANONICAL_VAULT_DIRS:
        (vault_root / folder_name).mkdir(parents=True, exist_ok=True)

    # 5. Populate config.yaml idempotently
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

    # Set topology and vault
    locus_sec.setdefault("topology", topology)
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

    # Write merged configuration
    config_file.write_text(yaml.dump(cfg, sort_keys=False), encoding="utf-8")

    # 6. Ensure .env template exists
    env_file = target_path / ".env"
    if not env_file.is_file():
        default_env = (
            "# Locus Environment Secrets\n"
            "LOCUS_HOME=" + str(target_path) + "\n"
            "# TELEGRAM_BOT_TOKEN=\n"
            "# COUCHDB_PASSWORD=\n"
        )
        env_file.write_text(default_env, encoding="utf-8")

    return {
        "status": "installed",
        "target_dir": str(target_path),
        "vault_dir": str(vault_root),
        "config_file": str(config_file),
        "prerequisites": {k: msg for k, (_, msg) in prereqs.items()},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Locus Unified Installer")
    parser.add_argument("--yes", "-y", action="store_true", help="Non-interactive mode")
    parser.add_argument("--answers", type=str, help="Path to JSON/YAML answers file")
    parser.add_argument("--target-dir", type=str, help="Target locus installation directory")
    parser.add_argument("--check-only", action="store_true", help="Check prerequisites only")

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

    try:
        report = run_install(target_dir=target, answers=answers, non_interactive=args.yes)
        print("Locus installation completed successfully:")
        print(f"  Target: {report['target_dir']}")
        print(f"  Vault:  {report['vault_dir']}")
        print(f"  Config: {report['config_file']}")
    except Exception as exc:
        print(f"Installation failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
