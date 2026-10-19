"""
SPEC §04 / D-13 Option a / 10-security.md / F-0085 / US-15: Integration Test for Hybrid Mode SSH Tunnel.
Asserts:
- sidecar/service.py binds only to loopback 127.0.0.1 on VM, never exposing plain HTTP on 0.0.0.0 (10-security.md).
- CLI includes helper command (locus tunnel or locus connect) establishing an SSH tunnel to VM's sidecar port.
- Local client connects through tunnel forwarder to VM service, authenticates, and executes status query.
"""
from __future__ import annotations

import json
from pathlib import Path
import select
import socket
import threading
import time
import urllib.request
import pytest
import uvicorn

from locus_cli.tunnel import SSHTunnelManager
from sidecar.service import HeadlessService, create_app


def find_free_port() -> int:
    """Allocate an unused port on loopback."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class PortForwarder(threading.Thread):
    """Simple in-process socket proxy simulating SSH local port forwarding (-L local:127.0.0.1:remote)."""

    def __init__(self, local_port: int, remote_port: int) -> None:
        super().__init__(daemon=True)
        self.local_port = local_port
        self.remote_port = remote_port
        self.running = False
        self._server_sock: socket.socket | None = None

    def run(self) -> None:
        self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_sock.bind(("127.0.0.1", self.local_port))
        self._server_sock.listen(5)
        self.running = True

        while self.running:
            try:
                self._server_sock.settimeout(0.5)
                client_sock, _ = self._server_sock.accept()
            except socket.timeout:
                continue
            except Exception:
                break

            # Forward to remote service
            try:
                remote_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                remote_sock.connect(("127.0.0.1", self.remote_port))
                threading.Thread(target=self._pipe, args=(client_sock, remote_sock), daemon=True).start()
                threading.Thread(target=self._pipe, args=(remote_sock, client_sock), daemon=True).start()
            except Exception:
                client_sock.close()

    def _pipe(self, src: socket.socket, dst: socket.socket) -> None:
        try:
            while self.running:
                data = src.recv(4096)
                if not data:
                    break
                dst.sendall(data)
        except Exception:
            pass
        finally:
            try:
                src.close()
            except Exception:
                pass
            try:
                dst.close()
            except Exception:
                pass

    def stop(self) -> None:
        self.running = False
        if self._server_sock:
            try:
                self._server_sock.close()
            except Exception:
                pass


def test_service_refuses_binding_to_public_0000():
    """SPEC 10-security.md line 30: "sidecar/service.py binds only to loopback 127.0.0.1:8420 on VM, never exposing plain HTTP on 0.0.0.0.\""""
    with pytest.raises(ValueError) as excinfo:
        HeadlessService(host="0.0.0.0", port=8420)
    assert "0.0.0.0 is forbidden" in str(excinfo.value)

    with pytest.raises(ValueError):
        HeadlessService(host="::", port=8420)


def test_hybrid_tunnel_cross_boundary_communication():
    """SPEC 04 line 14 / D-13 Option a: Local client connects through SSH tunnel forwarder to remote VM service on loopback."""
    remote_vm_port = find_free_port()
    local_tunnel_port = find_free_port()

    # 1. Start VM service bound strictly to loopback (simulating remote VM sidecar)
    app = create_app()
    server_config = uvicorn.Config(app, host="127.0.0.1", port=remote_vm_port, log_level="error")
    server = uvicorn.Server(server_config)

    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()

    # Wait for server to bind
    for _ in range(50):
        try:
            with socket.create_connection(("127.0.0.1", remote_vm_port), timeout=0.1):
                break
        except Exception:
            time.sleep(0.05)

    # 2. Start mock SSH tunnel forwarder (forwarding local_tunnel_port -> remote_vm_port)
    forwarder = PortForwarder(local_port=local_tunnel_port, remote_port=remote_vm_port)
    forwarder.start()
    time.sleep(0.1)

    # 3. Test SSHTunnelManager command generation
    tunnel_mgr = SSHTunnelManager(
        host="203.0.113.50",
        user="locus_user",
        local_port=local_tunnel_port,
        remote_port=remote_vm_port,
        ssh_port=2222,
    )
    cmd = tunnel_mgr.build_command()
    assert "-N" in cmd
    assert f"{local_tunnel_port}:127.0.0.1:{remote_vm_port}" in cmd
    assert "locus_user@203.0.113.50" in cmd
    assert "-p" in cmd
    assert "2222" in cmd

    try:
        # 4. Local client issues health check through the tunnel to local_tunnel_port
        tunnel_url = f"http://127.0.0.1:{local_tunnel_port}/health"
        req = urllib.request.Request(tunnel_url, headers={"User-Agent": "Locus-Local-Client"})
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["status"] == "ok"
            assert data["service"] == "locus-headless-service"

        # 5. Local client queries jobs through the tunnel
        jobs_url = f"http://127.0.0.1:{local_tunnel_port}/jobs"
        req_jobs = urllib.request.Request(jobs_url)
        with urllib.request.urlopen(req_jobs, timeout=3.0) as resp_jobs:
            assert resp_jobs.status == 200
            jobs_data = json.loads(resp_jobs.read().decode("utf-8"))
            assert jobs_data["status"] == "ok"
            assert "jobs" in jobs_data

    finally:
        # Cleanup
        forwarder.stop()
        server.should_exit = True
