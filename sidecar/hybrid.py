"""sidecar/hybrid.py - Hybrid mode SSH loopback tunnel manager.

Implements Decision D-13 and Security Law S-2:
- Hybrid mode: services run on VM, TUI runs locally.
- Local TUI and cron runner communicate with remote VM sidecar via an SSH loopback tunnel.
- STRICT loopback binding enforcement: local port binds exclusively to 127.0.0.1.
- No public ports or unauthenticated proxies opened on the VM.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Any, Callable, List, Optional, Tuple
import urllib.error
import urllib.request

logger = logging.getLogger("sidecar.hybrid")

DEFAULT_SIDECAR_PORT = 8420
LOOPBACK_ADDRESS = "127.0.0.1"


@dataclass
class SSHTunnelConfig:
    """Configuration for an SSH loopback tunnel to a remote VM."""
    remote_host: str
    remote_user: str = "ubuntu"
    remote_port: int = DEFAULT_SIDECAR_PORT
    local_port: int = DEFAULT_SIDECAR_PORT
    bind_address: str = LOOPBACK_ADDRESS
    ssh_key_path: Optional[Path] = None
    connect_timeout: int = 10

    def __post_init__(self) -> None:
        # Enforce S-2: loopback only
        if self.bind_address not in ("127.0.0.1", "localhost"):
            raise ValueError(
                f"Security Law S-2 violation: SSH tunnel must bind strictly to loopback (127.0.0.1), got '{self.bind_address}'"
            )


class SSHTunnelManager:
    """Manages the lifecycle of an SSH port-forwarding tunnel to a remote Locus VM."""

    def __init__(self, config: SSHTunnelConfig):
        self.config = config
        self._process: Optional[subprocess.Popen[Any]] = None
        self._mock_runner: Optional[Callable[[], bool]] = None

    @property
    def local_endpoint(self) -> str:
        return f"http://{self.config.bind_address}:{self.config.local_port}"

    def build_ssh_command(self) -> List[str]:
        """Construct the SSH command with strict loopback forwarding flags."""
        cmd = [
            "ssh",
            "-N",  # Do not execute remote commands
            "-L",
            f"{self.config.bind_address}:{self.config.local_port}:127.0.0.1:{self.config.remote_port}",
            f"{self.config.remote_user}@{self.config.remote_host}",
            "-o",
            f"ConnectTimeout={self.config.connect_timeout}",
            "-o",
            "ExitOnForwardFailure=yes",
            "-o",
            "ServerAliveInterval=30",
            "-o",
            "ServerAliveCountMax=3",
        ]
        if self.config.ssh_key_path:
            cmd.extend(["-i", str(Path(self.config.ssh_key_path).resolve())])

        return cmd

    def is_port_open(self, timeout: float = 1.0) -> bool:
        """Check if local loopback port is responding to TCP connections."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            try:
                res = sock.connect_ex((self.config.bind_address, self.config.local_port))
                return res == 0
            except OSError:
                return False

    def start_tunnel(
        self,
        mock_runner: Optional[Callable[[], bool]] = None,
        wait_seconds: float = 0.5,
    ) -> bool:
        """Start the background SSH tunnel process (or invoke mock_runner for testing)."""
        if mock_runner is not None:
            self._mock_runner = mock_runner
            return mock_runner()

        if self.is_port_open():
            logger.info("Tunnel port %d is already active.", self.config.local_port)
            return True

        cmd = self.build_ssh_command()
        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
            time.sleep(wait_seconds)
            if self._process.poll() is not None:
                _, err = self._process.communicate()
                logger.error("SSH tunnel process exited immediately: %s", err)
                return False
            return True
        except Exception as e:
            logger.error("Failed to launch SSH tunnel: %s", e)
            return False

    def stop_tunnel(self) -> None:
        """Terminate active SSH tunnel process."""
        if self._process is not None:
            try:
                self._process.terminate()
                self._process.wait(timeout=2.0)
            except Exception:
                try:
                    self._process.kill()
                except Exception:
                    pass
            finally:
                self._process = None

    def check_vm_health(self, timeout: float = 3.0) -> Tuple[bool, str]:
        """Perform a health check through the tunnel to the VM sidecar endpoint."""
        url = f"{self.local_endpoint}/health"
        req = urllib.request.Request(url, headers={"User-Agent": "Locus-HybridClient/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    return True, "VM sidecar reachable and healthy over loopback tunnel"
                return False, f"VM sidecar responded with status code: {resp.status}"
        except urllib.error.URLError as e:
            return False, f"Failed to reach VM sidecar: {e}"
        except Exception as e:
            return False, f"Tunnel communication error: {e}"


def get_hybrid_tunnel_config() -> Optional[SSHTunnelConfig]:
    """Load hybrid mode SSH tunnel configuration from config.yaml."""
    from sidecar.config import get, is_enabled

    mode = get("locus.mode", "local")
    if mode != "hybrid":
        return None

    vm_host = get("locus.hybrid.vm_host")
    if not vm_host:
        return None

    remote_user = get("locus.hybrid.ssh_user", "ubuntu")
    remote_port = int(get("locus.hybrid.sidecar_port", DEFAULT_SIDECAR_PORT))
    local_port = int(get("locus.hybrid.local_port", DEFAULT_SIDECAR_PORT))
    key_path = get("locus.hybrid.ssh_key_path")

    return SSHTunnelConfig(
        remote_host=str(vm_host),
        remote_user=str(remote_user),
        remote_port=remote_port,
        local_port=local_port,
        ssh_key_path=Path(key_path) if key_path else None,
    )
