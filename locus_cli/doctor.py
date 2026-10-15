"""locus_cli.doctor - Environment and prerequisite diagnostic suite (R7, R5).

Runs diagnostic checks printing exactly one PASS/FAIL line per check with remediation guidance,
and provides pass-through launching for the upstream Pi Agent TUI (R5).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any, Callable
import urllib.error
import urllib.request

import yaml

from sidecar.registry import get_registry

REPO_ROOT = Path(__file__).resolve().parent.parent


class CheckResult:
    def __init__(self, name: str, passed: bool, message: str = "", fix: str = "") -> None:
        self.name = name
        self.passed = passed
        self.message = message
        self.fix = fix

    def format_line(self) -> str:
        status = "[PASS]" if self.passed else "[FAIL]"
        line = f"{status} {self.name}"
        if self.message:
            line += f": {self.message}"
        if not self.passed and self.fix:
            line += f" (Fix: {self.fix})"
        return line


def check_python_version() -> CheckResult:
    """Verify Python version is >= 3.11."""
    major, minor = sys.version_info.major, sys.version_info.minor
    if major > 3 or (major == 3 and minor >= 11):
        return CheckResult("Python version", True, f"{major}.{minor}.{sys.version_info.micro} >= 3.11")
    return CheckResult(
        "Python version",
        False,
        f"{major}.{minor}.{sys.version_info.micro} is below minimum requirement 3.11",
        "Install Python 3.11 or higher from https://python.org",
    )


def check_nodejs_version(node_bin: str | None = None) -> CheckResult:
    """Verify Node.js version is >= 18."""
    node_cmd = node_bin or shutil.which("node")
    if not node_cmd or (node_bin and not shutil.which(node_bin) and not Path(node_bin).exists()):
        return CheckResult(
            "Node.js runtime",
            False,
            "Node.js executable 'node' not found in PATH",
            "Install Node.js 18+ from https://nodejs.org",
        )

    try:
        proc = subprocess.run(
            [node_cmd, "-v"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        ver_str = proc.stdout.strip().lstrip("v")
        major = int(ver_str.split(".")[0])
        if major >= 18:
            return CheckResult("Node.js version", True, f"v{ver_str} >= 18.0.0")
        return CheckResult(
            "Node.js version",
            False,
            f"v{ver_str} is below minimum requirement 18",
            "Upgrade Node.js to version 18 or higher",
        )
    except FileNotFoundError:
        return CheckResult(
            "Node.js runtime",
            False,
            "Node.js executable 'node' not found in PATH",
            "Install Node.js 18+ from https://nodejs.org",
        )
    except Exception as e:
        return CheckResult(
            "Node.js runtime",
            False,
            f"Failed to execute node -v: {e}",
            "Ensure Node.js is installed and accessible in PATH",
        )


def check_config_validity(locus_home: Path) -> CheckResult:
    """Verify LOCUS_HOME/config.yaml exists and contains valid locus configuration."""
    cfg_file = locus_home / "config.yaml"
    if not cfg_file.is_file():
        return CheckResult(
            "Configuration file",
            False,
            f"Config file not found at {cfg_file}",
            "Run python -m locus_cli.main --yes to generate default configuration",
        )

    try:
        data = yaml.safe_load(cfg_file.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "locus" not in data:
            return CheckResult(
                "Configuration file",
                False,
                "config.yaml missing root 'locus' mapping",
                "Re-generate config via python -m locus_cli.main --yes",
            )
        mode = data["locus"].get("mode", "local")
        return CheckResult("Configuration validity", True, f"Valid config.yaml (mode: {mode})")
    except Exception as e:
        return CheckResult(
            "Configuration validity",
            False,
            f"YAML parse error: {e}",
            "Fix syntax in config.yaml or re-generate",
        )


def check_vault_writable(vault_root: Path) -> CheckResult:
    """Verify canonical vault directory hierarchy exists and is writable."""
    canonical_dirs = [
        "00-System",
        "01-Projects",
        "02-Areas",
        "03-Resources",
        "04-Captures",
        "05-Daily",
        "06-Content",
        "07-Archives",
    ]
    if not vault_root.is_dir():
        return CheckResult(
            "Vault hierarchy",
            False,
            f"Vault root directory {vault_root} not found",
            "Run python -m locus_cli.main --yes to initialize canonical vault",
        )

    missing = [d for d in canonical_dirs if not (vault_root / d).is_dir()]
    if missing:
        return CheckResult(
            "Vault canonical folders",
            False,
            f"Missing canonical folders: {', '.join(missing)}",
            "Run python -m locus_cli.main --yes to create missing vault folders",
        )

    test_file = vault_root / "00-System" / ".doctor_probe.tmp"
    try:
        test_file.write_text("probe", encoding="utf-8")
        test_file.unlink()
        return CheckResult("Vault writability", True, "All 8 canonical folders present and writable")
    except Exception as e:
        return CheckResult(
            "Vault writability",
            False,
            f"Failed write probe into vault: {e}",
            f"Check write permissions on {vault_root}",
        )


def check_couchdb_loopback(port: int = 5984) -> CheckResult:
    """Verify CouchDB loopback connectivity."""
    url = f"http://127.0.0.1:{port}/"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Locus-Doctor/1.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                version = data.get("version", "unknown")
                return CheckResult("CouchDB connectivity", True, f"Reachable on loopback port {port} (v{version})")
    except urllib.error.HTTPError as e:
        if e.code == 401:
            # CouchDB requires auth, but server is actively listening!
            return CheckResult("CouchDB connectivity", True, f"Reachable on loopback port {port} (auth required)")
        return CheckResult(
            "CouchDB connectivity",
            False,
            f"HTTP error {e.code} on 127.0.0.1:{port}",
            "Check CouchDB credentials or container status",
        )
    except Exception as e:
        return CheckResult(
            "CouchDB connectivity",
            False,
            f"Connection failed on 127.0.0.1:{port}: {e}",
            "Run 'docker compose up -d couchdb' to start local CouchDB service",
        )

    return CheckResult(
        "CouchDB connectivity",
        False,
        f"Unable to connect to 127.0.0.1:{port}",
        "Run 'docker compose up -d couchdb' to start CouchDB",
    )


def check_sidecar_health(port: int = 8420) -> CheckResult:
    """Verify sidecar daemon health check endpoint."""
    url = f"http://127.0.0.1:{port}/health"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Locus-Doctor/1.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                return CheckResult("Sidecar service", True, f"Active on loopback port {port} (status: {data.get('status')})")
    except Exception as e:
        return CheckResult(
            "Sidecar service",
            False,
            f"Not reachable on 127.0.0.1:{port}/health ({e})",
            "Start sidecar service via 'python -m sidecar.service'",
        )

    return CheckResult(
        "Sidecar service",
        False,
        f"Inactive on 127.0.0.1:{port}",
        "Start sidecar service via 'python -m sidecar.service'",
    )


def check_provider_health() -> list[CheckResult]:
    """Verify health of all registered providers in ProviderRegistry."""
    results: list[CheckResult] = []
    registry = get_registry()
    if not registry._providers:
        results.append(CheckResult("Provider registry", True, "Registry initialized (no providers registered)"))
        return results

    for key, provider in registry._providers.items():
        name = f"Provider ({key[0]}:{key[1]})"
        try:
            if hasattr(provider, "health_check"):
                res = provider.health_check()
                status = res.get("status") if isinstance(res, dict) else "ok"
                if status == "ok":
                    results.append(CheckResult(name, True, "Health check ok"))
                else:
                    results.append(CheckResult(name, False, f"Reported status: {status}", "Check provider configuration"))
            else:
                results.append(CheckResult(name, True, "Registered"))
        except Exception as e:
            results.append(CheckResult(name, False, f"Health check failed: {e}", "Inspect provider logs"))
    return results


def run_doctor(
    locus_home: Path | None = None,
    vault_root: Path | None = None,
    couchdb_port: int = 5984,
    sidecar_port: int = 8420,
) -> int:
    """Run all diagnostic checks, print exactly one PASS/FAIL line each, and exit code 0 or 1."""
    if locus_home is None:
        locus_home = (
            Path(os.environ["LOCUS_HOME"])
            if "LOCUS_HOME" in os.environ and os.environ["LOCUS_HOME"].strip()
            else Path.home() / ".locus"
        )

    if vault_root is None:
        cfg_file = locus_home / "config.yaml"
        if cfg_file.is_file():
            try:
                data = yaml.safe_load(cfg_file.read_text(encoding="utf-8")) or {}
                vault_path = data.get("locus", {}).get("vault", {}).get("path")
                if vault_path:
                    vault_root = Path(vault_path)
            except Exception:
                pass
        if vault_root is None:
            vault_root = locus_home / "vault"

    checks: list[CheckResult] = []

    # Essential checks
    checks.append(check_python_version())
    checks.append(check_nodejs_version())
    checks.append(check_config_validity(locus_home))
    checks.append(check_vault_writable(vault_root))
    checks.append(check_couchdb_loopback(couchdb_port))
    checks.append(check_sidecar_health(sidecar_port))
    checks.extend(check_provider_health())

    all_passed = True
    print("=== Locus Doctor Diagnostics ===")
    for c in checks:
        print(c.format_line())
        if not c.passed:
            # Sidecar is considered a service warning if stopped, but couchdb/python/node/config are fatal
            if "Sidecar" not in c.name:
                all_passed = False

    return 0 if all_passed else 1


def run_pi_tui(args: list[str] | None = None) -> int:
    """Pass-through launcher for the upstream Pi Agent TUI (R5)."""
    node_cmd = shutil.which("node")
    if not node_cmd:
        sys.stderr.write("Node.js is required to launch Pi Agent TUI\n")
        return 1

    pi_entry = REPO_ROOT / "packages" / "coding-agent" / "dist" / "cli.js"
    if not pi_entry.is_file():
        # Fallback to source or index
        pi_entry = REPO_ROOT / "packages" / "coding-agent" / "index.js"

    cmd = [node_cmd, str(pi_entry)]
    if args:
        cmd.extend(args)

    return subprocess.run(cmd, cwd=REPO_ROOT).returncode


def main() -> None:
    """Entry point for python -m locus_cli.doctor."""
    sys.exit(run_doctor())


if __name__ == "__main__":
    main()
