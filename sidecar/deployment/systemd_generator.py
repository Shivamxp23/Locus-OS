"""
SPEC §23.1-23.5 lines 8440-8490: Systemd Unit Generator.
Generates hardened systemd service unit files for headless Linux VM operation.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("locus.deployment.systemd")


@dataclass
class SystemdUnitConfig:
    service_name: str
    description: str
    exec_start: str
    working_dir: str = "/home/locus/locus-os"
    user: str = "locus"
    env_file: str = "/home/locus/.locus/.env"
    restart: str = "on-failure"
    restart_sec: int = 5


class SystemdGenerator:
    """
    Generates hardened Linux systemd unit definitions for Locus background services.
    Enforces security isolation directives (NoNewPrivileges, PrivateTmp, ProtectSystem).
    """

    def generate_unit(self, config: SystemdUnitConfig) -> str:
        """Render systemd service file string."""
        return f"""[Unit]
Description={config.description}
After=network.target local-fs.target docker.service
Wants=network-online.target

[Service]
Type=simple
User={config.user}
WorkingDirectory={config.working_dir}
EnvironmentFile=-{config.env_file}
ExecStart={config.exec_start}
Restart={config.restart}
RestartSec={config.restart_sec}s

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=read-only
ReadWritePaths={config.working_dir}

[Install]
WantedBy=multi-user.target
"""

    def generate_sidecar_unit(
        self,
        working_dir: str = "/opt/locus/locus-os",
        user: str = "locus",
        env_file: str = "/opt/locus/.locus/.env",
    ) -> str:
        """Preconfigured systemd unit for Locus FastAPI sidecar service."""
        cfg = SystemdUnitConfig(
            service_name="locus-sidecar",
            description="Locus Personal Intelligence Sidecar Service",
            exec_start="/opt/locus/locus-os/.venv/bin/python -m uvicorn sidecar.service:app --host 127.0.0.1 --port 8420",
            working_dir=working_dir,
            user=user,
            env_file=env_file,
        )
        return self.generate_unit(cfg)

    def generate_agent_unit(
        self,
        working_dir: str = "/opt/locus/locus-os",
        user: str = "locus",
        env_file: str = "/opt/locus/.locus/.env",
    ) -> str:
        """Preconfigured systemd unit for Locus Pi coding agent / supervisor."""
        cfg = SystemdUnitConfig(
            service_name="locus-agent",
            description="Locus Supervisor & Autonomous Agent Engine",
            exec_start="/usr/bin/node /opt/locus/locus-os/packages/coding-agent/dist/cli.js --headless",
            working_dir=working_dir,
            user=user,
            env_file=env_file,
        )
        return self.generate_unit(cfg)
