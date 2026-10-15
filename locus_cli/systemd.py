"""locus_cli.systemd - Systemd service unit generator and installer for Locus OS.

Supports deploying Locus background services (sidecar daemon, cron runner)
on Linux VMs and servers per Epic E4 (US-15 / F-0085).
"""

from __future__ import annotations

import getpass
import logging
import os
from pathlib import Path
import sys
from typing import Optional

logger = logging.getLogger("locus_cli.systemd")

DEFAULT_SERVICE_NAME = "locus-sidecar"
SYSTEMD_SYSTEM_DIR = Path("/etc/systemd/system")
SYSTEMD_USER_DIR = Path("~/.config/systemd/user")


def generate_systemd_unit(
    service_name: str = DEFAULT_SERVICE_NAME,
    python_bin: Optional[Path] = None,
    locus_dir: Optional[Path] = None,
    locus_home: Optional[Path] = None,
    user: Optional[str] = None,
) -> str:
    """Generate a clean, robust systemd service unit definition for Locus OS."""
    # Resolve Python binary
    py_executable = Path(python_bin or sys.executable).resolve()

    # Resolve Locus repository directory
    if locus_dir is None:
        locus_dir = Path(__file__).resolve().parent.parent
    else:
        locus_dir = Path(locus_dir).resolve()

    # Resolve LOCUS_HOME directory
    if locus_home is None:
        locus_home = Path.home() / ".locus"
    else:
        locus_home = Path(locus_home).expanduser().resolve()

    env_file = locus_home / ".env"
    run_user = user or getpass.getuser()

    unit_content = f"""[Unit]
Description=Locus OS Headless Sidecar Daemon ({service_name})
After=network.target couchdb.service
Documentation=https://github.com/Shivamxp23/Locus-OS

[Service]
Type=simple
User={run_user}
WorkingDirectory={locus_dir}
EnvironmentFile={env_file}
ExecStart={py_executable} -m sidecar.service
Restart=always
RestartSec=5s
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
"""
    return unit_content


def install_systemd_unit(
    unit_content: str,
    target_path: Optional[Path] = None,
    service_name: str = DEFAULT_SERVICE_NAME,
    user_mode: bool = False,
) -> Path:
    """Write the systemd service unit file to disk."""
    if target_path is not None:
        dest = Path(target_path).resolve()
    elif user_mode:
        dest = SYSTEMD_USER_DIR.expanduser() / f"{service_name}.service"
    else:
        dest = SYSTEMD_SYSTEM_DIR / f"{service_name}.service"

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(unit_content, encoding="utf-8")

    # Set 0644 permissions on POSIX systems
    if sys.platform != "win32":
        try:
            os.chmod(dest, 0o644)
        except OSError as e:
            logger.debug("Failed to set 0644 mode on %s: %s", dest, e)

    return dest


def main() -> None:
    """CLI generator utility."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate systemd unit files for Locus OS")
    parser.add_argument("--name", default=DEFAULT_SERVICE_NAME, help="Service name")
    parser.add_argument("--output", type=Path, default=None, help="Output file path")
    parser.add_argument("--user-mode", action="store_true", help="Generate for user systemd")

    args = parser.parse_args()
    content = generate_systemd_unit(service_name=args.name)

    if args.output:
        dest = install_systemd_unit(content, target_path=args.output, user_mode=args.user_mode)
        print(f"[PASS] Installed systemd service unit to: {dest}")
    else:
        print(content)


if __name__ == "__main__":
    main()
