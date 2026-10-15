"""tests/test_livesync_bridge.py - Unit & Integration tests for Obsidian LiveSync & CouchDB.

Tests for US-16 / F-0060:
- docker-compose.yml CouchDB loopback binding and password enforcement (S-2).
- data/couchdb/local.ini CORS origin whitelist.
- S-2 transport validation: loopback / HTTPS allowed, unencrypted public HTTP rejected.
- Deterministic conflict resolution: (mtime, hash) comparison with conflict sidecar notes.
- Integration: LiveSync push and pull against mock CouchDB server over loopback.
"""

from __future__ import annotations

import http.server
import json
from pathlib import Path
import threading
import time
import pytest
import yaml

from sidecar.vault.livesync_bridge import (
    LiveSyncBridge,
    resolve_concurrent_conflict,
    validate_transport_security,
)


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def test_unit_docker_compose_couchdb_loopback(repo_root: Path):
    """Verify docker-compose.yml binds CouchDB strictly to loopback and requires password (S-2)."""
    compose_file = repo_root / "docker-compose.yml"
    assert compose_file.is_file()

    content = compose_file.read_text(encoding="utf-8")
    data = yaml.safe_load(content)
    couch_svc = data["services"]["locus-couchdb"]

    # Must bind strictly to 127.0.0.1:5984:5984
    ports = couch_svc["ports"]
    assert "127.0.0.1:5984:5984" in ports

    # Must require COUCHDB_PASSWORD from .env
    env = couch_svc["environment"]
    env_str = str(env)
    assert "COUCHDB_PASSWORD" in env_str
    assert "set it in .locus/.env" in env_str


def test_unit_couchdb_local_ini_cors(repo_root: Path):
    """Verify data/couchdb/local.ini restricts CORS origins per spec and S-2."""
    ini_file = repo_root / "data" / "couchdb" / "local.ini"
    assert ini_file.is_file()

    content = ini_file.read_text(encoding="utf-8")
    assert "enable_cors = true" in content
    assert "app://obsidian.md" in content
    assert "capacitor://localhost" in content
    assert "http://localhost" in content
    # Ensure wildcard * is NOT present in origins
    for line in content.splitlines():
        if line.strip().startswith("origins"):
            assert "*" not in line


def test_unit_transport_security_validation():
    """Verify Security Law S-2: Refuses unencrypted public HTTP, accepts loopback & HTTPS."""
    # Loopback HTTP is permitted
    assert validate_transport_security("http://127.0.0.1:5984") is True
    assert validate_transport_security("http://localhost:5984") is True

    # Remote HTTPS is permitted (reverse proxy / TLS overlay)
    assert validate_transport_security("https://couch.example.com") is True
    assert validate_transport_security("https://140.238.245.25:5984") is True

    # Remote unencrypted HTTP is strictly forbidden
    with pytest.raises(ValueError) as exc:
        validate_transport_security("http://140.238.245.25:5984")
    assert "Security Law S-2 violation" in str(exc.value)

    with pytest.raises(ValueError) as exc2:
        validate_transport_security("http://0.0.0.0:5984")
    assert "Security Law S-2 violation" in str(exc2.value)


def test_unit_concurrent_conflict_resolution(tmp_path: Path):
    """Verify deterministic conflict resolution creates sidecar conflict notes."""
    note_path = tmp_path / "Note.md"
    note_path.write_text("# Local Canonical Content\n", encoding="utf-8")

    # Case 1: Exact match -> no conflict note
    local_bytes = note_path.read_bytes()
    won, conflict = resolve_concurrent_conflict(note_path, local_bytes, int(time.time() * 1000))
    assert won is True
    assert conflict is None

    # Case 2: Divergent content, remote is newer
    remote_bytes = b"# Remote Winner Content\n"
    future_mtime = int((time.time() + 1000) * 1000)
    won2, conflict2 = resolve_concurrent_conflict(note_path, remote_bytes, future_mtime)

    assert won2 is False
    assert conflict2 is not None
    assert conflict2.is_file()
    assert ".conflict-" in conflict2.name
    # Remote content applied to canonical note
    assert note_path.read_text(encoding="utf-8") == "# Remote Winner Content\n"
    # Local content preserved in conflict file
    assert conflict2.read_text(encoding="utf-8") == "# Local Canonical Content\n"


class _MockCouchDBServer(http.server.BaseHTTPRequestHandler):
    """Mock HTTP handler for CouchDB document store."""
    docs: dict[str, dict] = {}

    def do_GET(self):
        doc_id = self.path.split("/")[-1]
        if doc_id in self.docs:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(self.docs[doc_id]).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_PUT(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode("utf-8"))
        doc_id = self.path.split("/")[-1]
        body["_rev"] = f"1-{hash(str(body))}"
        self.docs[doc_id] = body

        self.send_response(201)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"ok": True, "id": doc_id, "rev": body["_rev"]}).encode("utf-8"))

    def log_message(self, format, *args):
        pass


def test_integration_couchdb_push_pull(tmp_path: Path):
    """Integration test: LiveSyncBridge push and pull over loopback."""
    server = http.server.HTTPServer(("127.0.0.1", 0), _MockCouchDBServer)
    assigned_port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        bridge = LiveSyncBridge(
            vault_root=tmp_path,
            couchdb_url=f"http://127.0.0.1:{assigned_port}",
            database="locus-vault",
        )

        # 1. Push note
        res = bridge.push("01-Projects/Locus/Plan.md", "# Project Plan\nBody text")
        assert res["status"] == "success"
        assert res["rev"] is not None

        # 2. Pull note
        doc = bridge.pull("01-Projects/Locus/Plan.md")
        assert doc is not None
        assert doc["path"] == "01-Projects/Locus/Plan.md"
        assert doc["eden"]["content"] == "# Project Plan\nBody text"
    finally:
        server.shutdown()
        server.server_close()
