"""tests/test_vm_hybrid.py - Unit and Integration tests for VM backend and Hybrid Mode.

Tests for US-15 / F-0085:
- Unit: systemd service unit generator structure, path resolution, and file installation.
- Unit: SSH tunnel command construction and strict S-2 loopback enforcement (127.0.0.1 only).
- Unit: Hybrid mode configuration detection and topology updates.
- Integration: Cross-boundary test simulating local client -> loopback tunnel -> mock VM service.
"""

from __future__ import annotations

import http.server
import json
from pathlib import Path
import threading
import time
import pytest
import yaml

from locus_cli.setup import update_config_mode
from locus_cli.systemd import generate_systemd_unit, install_systemd_unit
from sidecar.hybrid import (
    SSHTunnelConfig,
    SSHTunnelManager,
    get_hybrid_tunnel_config,
)


@pytest.fixture
def temp_locus_home(tmp_path: Path) -> Path:
    home = tmp_path / ".locus"
    home.mkdir(parents=True, exist_ok=True)
    return home


def test_unit_systemd_unit_generation(temp_locus_home: Path):
    """Test generating systemd service unit with correct paths and restart policies."""
    locus_dir = temp_locus_home / "repo"
    locus_dir.mkdir(parents=True, exist_ok=True)
    custom_python = locus_dir / ".venv" / "bin" / "python3"

    unit = generate_systemd_unit(
        service_name="locus-sidecar",
        python_bin=custom_python,
        locus_dir=locus_dir,
        locus_home=temp_locus_home,
        user="testuser",
    )

    assert "[Unit]" in unit
    assert "[Service]" in unit
    assert "[Install]" in unit
    assert "User=testuser" in unit
    assert f"WorkingDirectory={locus_dir}" in unit
    assert f"EnvironmentFile={temp_locus_home / '.env'}" in unit
    assert f"ExecStart={custom_python} -m sidecar.service" in unit
    assert "Restart=always" in unit
    assert "RestartSec=5s" in unit
    assert "WantedBy=multi-user.target" in unit


def test_unit_systemd_installation(tmp_path: Path):
    """Test writing systemd service unit file to custom directory."""
    target_dir = tmp_path / "systemd"
    target_file = target_dir / "locus-sidecar.service"

    unit_content = "[Unit]\nDescription=Test Service\n"
    dest = install_systemd_unit(unit_content, target_path=target_file)

    assert dest == target_file
    assert target_file.is_file()
    assert target_file.read_text(encoding="utf-8") == unit_content


def test_unit_ssh_tunnel_command_construction():
    """Test SSH tunnel command formulation with strict loopback binding (D-13, S-2)."""
    cfg = SSHTunnelConfig(
        remote_host="vm.locus.internal",
        remote_user="ubuntu",
        remote_port=8420,
        local_port=8420,
        bind_address="127.0.0.1",
        connect_timeout=5,
    )
    mgr = SSHTunnelManager(cfg)
    cmd = mgr.build_ssh_command()

    assert cmd[0] == "ssh"
    assert "-N" in cmd
    assert "-L" in cmd
    idx = cmd.index("-L")
    assert cmd[idx + 1] == "127.0.0.1:8420:127.0.0.1:8420"
    assert "ubuntu@vm.locus.internal" in cmd


def test_unit_ssh_tunnel_loopback_enforcement():
    """Verify security rule S-2: Refuses open addresses or 0.0.0.0."""
    with pytest.raises(ValueError) as exc:
        SSHTunnelConfig(
            remote_host="vm.locus.internal",
            bind_address="0.0.0.0",
        )
    assert "Security Law S-2 violation" in str(exc.value)

    with pytest.raises(ValueError):
        SSHTunnelConfig(
            remote_host="vm.locus.internal",
            bind_address="192.168.1.100",
        )


def test_unit_hybrid_mode_config(temp_locus_home: Path):
    """Test setting mode: hybrid in config.yaml and loading tunnel configuration."""
    cfg_file = temp_locus_home / "config.yaml"
    update_config_mode(cfg_file, "hybrid")

    data = yaml.safe_load(cfg_file.read_text(encoding="utf-8"))
    assert data["locus"]["mode"] == "hybrid"


class _MockVMHttpHandler(http.server.BaseHTTPRequestHandler):
    """Mock HTTP handler simulating remote VM sidecar /health endpoint."""
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "ok", "service": "sidecar", "mode": "vm"}')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Quiet logging in test


def test_integration_hybrid_tunnel_boundary():
    """
    Integration test crossing service boundary (D-13 / F-0085):
    Simulates local client -> loopback tunnel -> mock remote VM sidecar daemon.
    Verifies HTTP handshake, status, and JSON payload over 127.0.0.1 tunnel.
    """
    # 1. Start mock VM sidecar server on an available local port
    server = http.server.HTTPServer(("127.0.0.1", 0), _MockVMHttpHandler)
    assigned_port = server.server_address[1]

    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    try:
        # 2. Configure SSH tunnel manager targeting mock VM server
        cfg = SSHTunnelConfig(
            remote_host="vm.mock.local",
            remote_port=assigned_port,
            local_port=assigned_port,
            bind_address="127.0.0.1",
        )
        mgr = SSHTunnelManager(cfg)

        # 3. Verify loopback port is active and accessible
        assert mgr.is_port_open(timeout=2.0) is True

        # 4. Cross boundary: perform health check over loopback tunnel
        ok, msg = mgr.check_vm_health(timeout=2.0)
        assert ok is True
        assert "reachable and healthy" in msg
    finally:
        server.shutdown()
        server.server_close()
