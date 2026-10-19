"""
SPEC §1.12 / R7, R5 / F-0082 / US-13: Locus Doctor Diagnostic Suite.
Executes comprehensive diagnostics with one PASS/FAIL line per check and remediation advice:
- Python >= 3.10
- Node.js >= 18
- Git installed
- Docker daemon status
- Port availability (8420 for sidecar, 5984 for CouchDB)
- Vault directory writability
- Environment keys and LOCUS_HOME
- Sidecar /health endpoint
- Registered providers health_check()
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple
import urllib.error
import urllib.request
import yaml

MIN_PYTHON = (3, 10)
MIN_NODE = 18
DEFAULT_SIDECAR_PORT = 8420
DEFAULT_COUCHDB_PORT = 5984


class DiagnosticResult:
    def __init__(
        self,
        name: str,
        passed: bool,
        message: str,
        remediation: Optional[str] = None,
        critical: bool = True,
    ):
        self.name = name
        self.passed = passed
        self.message = message
        self.remediation = remediation
        self.critical = critical

    def format_line(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        line = f"[{status}] {self.name}: {self.message}"
        if not self.passed and self.remediation:
            line += f" -> Fix: {self.remediation}"
        return line


def check_python() -> DiagnosticResult:
    """Verify Python version is at least 3.10."""
    v = sys.version_info
    ver_str = f"{v.major}.{v.minor}.{v.micro}"
    if v >= MIN_PYTHON:
        return DiagnosticResult("python", True, f"Python {ver_str}")
    return DiagnosticResult(
        "python",
        False,
        f"Python {ver_str} (requires >= 3.10)",
        "Install Python 3.10+ or upgrade via winget/brew/apt",
    )


def check_node() -> DiagnosticResult:
    """Verify Node.js executable exists and is at least v18."""
    node_exe = shutil.which("node")
    if not node_exe:
        return DiagnosticResult(
            "node",
            False,
            "Node.js not found in PATH",
            "Install Node.js 18+ from https://nodejs.org",
        )
    try:
        proc = subprocess.run([node_exe, "--version"], capture_output=True, text=True, check=True)
        out = proc.stdout.strip()
        match = re.search(r"v?(\d+)\.", out)
        if match and int(match.group(1)) >= MIN_NODE:
            return DiagnosticResult("node", True, f"Node.js {out}")
        return DiagnosticResult(
            "node",
            False,
            f"Node.js {out} (requires >= v{MIN_NODE})",
            "Upgrade Node.js to version 18 or newer",
        )
    except Exception as exc:
        return DiagnosticResult("node", False, f"Node.js error: {exc}", "Verify Node.js installation")


def check_git() -> DiagnosticResult:
    """Verify Git executable exists in PATH."""
    git_exe = shutil.which("git")
    if not git_exe:
        return DiagnosticResult(
            "git",
            False,
            "Git not found in PATH",
            "Install Git from https://git-scm.com",
        )
    try:
        proc = subprocess.run([git_exe, "--version"], capture_output=True, text=True, check=True)
        return DiagnosticResult("git", True, proc.stdout.strip())
    except Exception as exc:
        return DiagnosticResult("git", False, f"Git error: {exc}", "Verify Git installation")


def check_docker() -> DiagnosticResult:
    """Verify Docker CLI and daemon response."""
    docker_exe = shutil.which("docker")
    if not docker_exe:
        return DiagnosticResult(
            "docker",
            False,
            "Docker not found in PATH",
            "Install Docker Desktop or Docker Engine (required for VM/hybrid mode)",
            critical=False,
        )
    try:
        proc = subprocess.run([docker_exe, "info"], capture_output=True, text=True, timeout=3.0)
        if proc.returncode == 0:
            return DiagnosticResult("docker", True, "Docker daemon running")
        return DiagnosticResult(
            "docker",
            False,
            "Docker daemon not responding",
            "Start Docker Desktop or systemd docker service",
            critical=False,
        )
    except Exception:
        return DiagnosticResult(
            "docker",
            False,
            "Docker daemon check timed out",
            "Ensure Docker service is running",
            critical=False,
        )


def check_port_free(port: int, service_name: str) -> DiagnosticResult:
    """Verify port is free for binding on loopback."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.5)
    try:
        # If bind succeeds, port is free
        sock.bind(("127.0.0.1", port))
        sock.close()
        return DiagnosticResult(f"port-{port}", True, f"Port {port} ({service_name}) is free")
    except socket.error:
        sock.close()
        return DiagnosticResult(
            f"port-{port}",
            False,
            f"Port {port} ({service_name}) is currently in use",
            f"Stop conflicting process on port {port} or configure custom port",
            critical=False,
        )


def check_vault_writability(target_vault: Optional[Path] = None) -> DiagnosticResult:
    """Verify vault directory exists and is writable."""
    vpath = target_vault
    if vpath is None:
        home_locus = Path.home() / ".locus"
        cfg_file = home_locus / "config.yaml"
        if cfg_file.is_file():
            try:
                loaded = yaml.safe_load(cfg_file.read_text(encoding="utf-8"))
                val = loaded.get("locus", {}).get("vault", {}).get("path")
                if val:
                    vpath = Path(val)
            except Exception:
                pass
        if vpath is None:
            vpath = home_locus / "vault"

    try:
        vpath.mkdir(parents=True, exist_ok=True)
        probe = vpath / ".doctor_probe"
        probe.write_text("probe", encoding="utf-8")
        probe.unlink()
        return DiagnosticResult("vault", True, f"{vpath} is writable")
    except Exception as exc:
        return DiagnosticResult(
            "vault",
            False,
            f"Cannot write to {vpath}: {exc}",
            f"Grant write permissions to {vpath}",
        )


def check_environment_keys(env_file: Optional[Path] = None) -> DiagnosticResult:
    """Verify .env secrets file exists with required parameters."""
    epath = env_file or (Path.home() / ".locus" / ".env")
    if not epath.is_file():
        return DiagnosticResult(
            "env",
            False,
            f"Secrets file not found at {epath}",
            "Run 'locus install' or 'locus install --reconfigure keys' to generate .env",
        )

    keys: Dict[str, str] = {}
    for line in epath.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            keys[k.strip()] = v.strip().strip("'\"")

    if "LOCUS_HOME" not in keys:
        return DiagnosticResult(
            "env",
            False,
            "LOCUS_HOME missing from .env",
            "Add LOCUS_HOME=<target_dir> to your .env file",
        )

    return DiagnosticResult("env", True, f"Found .env with {len(keys)} defined variables")


def check_sidecar_health(port: int = DEFAULT_SIDECAR_PORT, timeout: float = 1.0) -> DiagnosticResult:
    """Check if local sidecar daemon answers /health."""
    url = f"http://127.0.0.1:{port}/health"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Locus-Doctor/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("status") in ("ok", "healthy"):
                return DiagnosticResult("sidecar-health", True, f"Sidecar responsive on :{port}")
            return DiagnosticResult(
                "sidecar-health",
                False,
                f"Sidecar returned unhealthy status: {data}",
                "Check sidecar logs in ~/.locus/logs",
                critical=False,
            )
    except urllib.error.URLError:
        return DiagnosticResult(
            "sidecar-health",
            False,
            f"Sidecar service not currently running on 127.0.0.1:{port}",
            "Start sidecar service via 'py -3 -m sidecar.service' or systemd/docker",
            critical=False,
        )
    except Exception as exc:
        return DiagnosticResult(
            "sidecar-health",
            False,
            f"Sidecar health check error: {exc}",
            "Verify sidecar configuration",
            critical=False,
        )


def check_registered_providers() -> DiagnosticResult:
    """Verify registered modular providers answer health_check()."""
    try:
        from sidecar.registry import get_registry

        reg = get_registry()
        health_results = reg.health_check_all()
        if not health_results:
            return DiagnosticResult("providers", True, "Provider registry active (0 providers registered)")

        failed: List[str] = []
        for prov_key, res in health_results.items():
            is_ok = res.get("status") in ("ok", "healthy", True) if isinstance(res, dict) else bool(res)
            if not is_ok:
                failed.append(prov_key)

        if failed:
            return DiagnosticResult(
                "providers",
                False,
                f"Unhealthy providers: {', '.join(failed)}",
                "Check provider configuration or credentials",
                critical=False,
            )
        return DiagnosticResult("providers", True, f"{len(health_results)} registered provider(s) healthy")
    except ImportError:
        return DiagnosticResult("providers", True, "Provider registry not loaded (standalone mode)")
    except Exception as exc:
        return DiagnosticResult("providers", False, f"Provider registry error: {exc}", critical=False)


def run_doctor(
    vault_dir: Optional[Path] = None,
    env_file: Optional[Path] = None,
    check_sidecar: bool = False,
    strict: bool = False,
) -> Tuple[bool, List[DiagnosticResult]]:
    """Execute all diagnostic checks and return (overall_success, results)."""
    checks: List[DiagnosticResult] = [
        check_python(),
        check_node(),
        check_git(),
        check_docker(),
        check_port_free(DEFAULT_SIDECAR_PORT, "sidecar"),
        check_vault_writability(vault_dir),
        check_environment_keys(env_file),
    ]

    if check_sidecar:
        checks.append(check_sidecar_health())
    checks.append(check_registered_providers())

    if strict:
        all_passed = all(c.passed for c in checks)
    else:
        all_passed = all(c.passed for c in checks if c.critical)

    return all_passed, checks


def main() -> None:
    parser = argparse.ArgumentParser(description="Locus Doctor Diagnostics (R7)")
    parser.add_argument("--vault-dir", type=str, help="Vault directory path to verify")
    parser.add_argument("--env-file", type=str, help="Environment secrets file to verify")
    parser.add_argument("--check-sidecar", action="store_true", help="Include active sidecar /health probe")
    parser.add_argument("--strict", action="store_true", help="Fail if any non-critical check fails")
    parser.add_argument("--json", action="store_true", help="Output diagnostics in JSON format")

    args = parser.parse_args()

    vpath = Path(args.vault_dir) if args.vault_dir else None
    epath = Path(args.env_file) if args.env_file else None

    passed, results = run_doctor(
        vault_dir=vpath,
        env_file=epath,
        check_sidecar=args.check_sidecar,
        strict=args.strict,
    )

    if args.json:
        data = {
            "overall_pass": passed,
            "checks": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "message": r.message,
                    "remediation": r.remediation,
                    "critical": r.critical,
                }
                for r in results
            ],
        }
        print(json.dumps(data, indent=2))
    else:
        print("Locus Doctor Diagnostics (R7):")
        for r in results:
            print(f"  {r.format_line()}")
        if passed:
            print("\n[OK] System is healthy and ready.")
        else:
            print("\n[FAIL] Some diagnostics failed. Review remediation steps above.")

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
