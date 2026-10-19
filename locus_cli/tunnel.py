"""
SPEC §04 / D-13 Option a / F-0085 / US-15: SSH Tunnel Manager for Hybrid and VM Modes.
Provides helper commands ('locus tunnel', 'locus connect') to establish a secure SSH port-forwarding
tunnel between the local machine and the remote VM's loopback sidecar service:
    ssh -N -L <local_port>:127.0.0.1:<remote_port> <user>@<host> -p <ssh_port> -i <ssh_key>

Enforces:
1. Sidecar on the VM is never exposed to plain public HTTP on 0.0.0.0 (10-security.md).
2. Local TUI/CLI connects over loopback 127.0.0.1:<local_port> through the encrypted SSH tunnel.
3. Configurable host, user, port, and key path from config.yaml or CLI parameters.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any, Callable, Dict, List, Optional

from sidecar import config


class SSHTunnelManager:
    """Manages an SSH tunnel forwarding local loopback port to remote VM loopback sidecar."""

    DEFAULT_LOCAL_PORT: int = 8420
    DEFAULT_REMOTE_PORT: int = 8420
    DEFAULT_SSH_PORT: int = 22

    def __init__(
        self,
        host: str,
        user: str,
        local_port: int = DEFAULT_LOCAL_PORT,
        remote_port: int = DEFAULT_REMOTE_PORT,
        ssh_port: int = DEFAULT_SSH_PORT,
        ssh_key: Optional[Path] = None,
    ) -> None:
        if not host or not str(host).strip():
            raise ValueError("VM host address cannot be empty")
        if not user or not str(user).strip():
            raise ValueError("SSH username cannot be empty")

        self.host = str(host).strip()
        self.user = str(user).strip()
        self.local_port = int(local_port)
        self.remote_port = int(remote_port)
        self.ssh_port = int(ssh_port)
        self.ssh_key = Path(ssh_key).resolve() if ssh_key else None
        self._proc: Optional[subprocess.Popen] = None

    def build_command(self) -> List[str]:
        """Construct the ssh port-forwarding command list."""
        ssh_bin = shutil.which("ssh") or "ssh"
        cmd = [
            ssh_bin,
            "-N",
            "-L",
            f"{self.local_port}:127.0.0.1:{self.remote_port}",
            f"{self.user}@{self.host}",
            "-p",
            str(self.ssh_port),
            "-o",
            "ExitOnForwardFailure=yes",
            "-o",
            "ServerAliveInterval=30",
            "-o",
            "ServerAliveCountMax=3",
        ]
        if self.ssh_key:
            cmd.extend(["-i", str(self.ssh_key)])
        return cmd

    def start_tunnel(
        self,
        runner: Optional[Callable[[List[str]], Any]] = None,
    ) -> Any:
        """
        Start the SSH tunnel.
        Accepts custom runner for testing/mocking.
        """
        cmd = self.build_command()
        if runner is not None:
            self._proc = runner(cmd)
            return self._proc

        self._proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return self._proc

    def is_alive(self) -> bool:
        """Return True if the tunnel process is currently running."""
        if self._proc is None:
            return False
        if hasattr(self._proc, "poll"):
            return self._proc.poll() is None
        return True

    def stop_tunnel(self) -> None:
        """Terminate the running SSH tunnel process cleanly."""
        if self._proc is not None:
            try:
                if hasattr(self._proc, "terminate"):
                    self._proc.terminate()
                if hasattr(self._proc, "wait"):
                    self._proc.wait(timeout=2.0)
            except Exception:
                try:
                    if hasattr(self._proc, "kill"):
                        self._proc.kill()
                except Exception:
                    pass
            finally:
                self._proc = None

    @classmethod
    def from_config(cls, cfg: Optional[Dict[str, Any]] = None) -> SSHTunnelManager:
        """Create SSHTunnelManager from configuration keys under locus.vm."""
        cfg_source = cfg or {}
        vm_sec = cfg_source.get("locus", {}).get("vm", {})
        if not vm_sec and not cfg_source:
            # Query global config accessor
            val = config.get("locus.vm")
            if isinstance(val, dict):
                vm_sec = val

        host = vm_sec.get("host") or config.get_env("LOCUS_VM_HOST") or "127.0.0.1"
        user = vm_sec.get("user") or config.get_env("LOCUS_VM_USER") or "ubuntu"
        ssh_port = int(vm_sec.get("ssh_port", cls.DEFAULT_SSH_PORT))
        local_port = int(vm_sec.get("local_port", cls.DEFAULT_LOCAL_PORT))
        remote_port = int(vm_sec.get("sidecar_port", cls.DEFAULT_REMOTE_PORT))
        key_val = vm_sec.get("ssh_key") or config.get_env("LOCUS_VM_SSH_KEY")
        ssh_key = Path(key_val) if key_val else None

        return cls(
            host=host,
            user=user,
            local_port=local_port,
            remote_port=remote_port,
            ssh_port=ssh_port,
            ssh_key=ssh_key,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Locus SSH Tunnel / Connect Helper (D-13)")
    parser.add_argument("--host", type=str, help="Remote VM host address or IP")
    parser.add_argument("--user", type=str, help="SSH username on remote VM")
    parser.add_argument("--port", type=int, default=22, help="Remote SSH port (default 22)")
    parser.add_argument("--local-port", type=int, default=8420, help="Local port to forward (default 8420)")
    parser.add_argument("--remote-port", type=int, default=8420, help="Remote sidecar port on VM (default 8420)")
    parser.add_argument("--key", type=str, help="Path to private SSH key file")
    parser.add_argument("--dry-run", action="store_true", help="Print SSH command without executing")

    args = parser.parse_args()

    # If arguments not provided, resolve from config
    host = args.host
    user = args.user
    if not host or not user:
        try:
            mgr = SSHTunnelManager.from_config()
            if not host:
                host = mgr.host
            if not user:
                user = mgr.user
        except Exception:
            host = host or "127.0.0.1"
            user = user or "ubuntu"

    key_path = Path(args.key) if args.key else None
    tunnel = SSHTunnelManager(
        host=host,
        user=user,
        local_port=args.local_port,
        remote_port=args.remote_port,
        ssh_port=args.port,
        ssh_key=key_path,
    )

    cmd = tunnel.build_command()
    cmd_str = " ".join(cmd)
    if args.dry_run:
        print(f"SSH Tunnel Command:\n  {cmd_str}")
        return

    print("=" * 60)
    print("LOCUS HYBRID MODE SSH TUNNEL")
    print(f"Forwarding 127.0.0.1:{args.local_port} -> {user}@{host}:{args.remote_port}")
    print(f"Command: {cmd_str}")
    print("=" * 60)

    try:
        tunnel.start_tunnel()
        print("[OK] Tunnel established. Press Ctrl+C to terminate.")
        while tunnel.is_alive():
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\nStopping SSH tunnel...")
    finally:
        tunnel.stop_tunnel()
        print("Tunnel closed.")


if __name__ == "__main__":
    main()
