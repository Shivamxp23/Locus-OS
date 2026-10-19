"""
SPEC §27.2 / §03 / F-0060 / US-16: Integration tests for Vault LiveSync Service Boundary.
Asserts:
- FastAPI sidecar service /vault/sync/status and /vault/sync/push cross-boundary invocation.
- Off-switch returns 503 when sync is disabled.
"""
from __future__ import annotations

from pathlib import Path
import pytest
from starlette.testclient import TestClient

from sidecar import config
from sidecar.registry import ProviderRegistry
from sidecar.service import create_app
from sidecar.vault.livesync_bridge import CouchDBLiveSyncProvider


def test_livesync_service_cross_boundary_endpoints(monkeypatch, tmp_path: Path):
    """SPEC §27.2 line 45: "Dispatch push notification to Sidecar Bridge... /vault/sync/push"."""
    locus_home = tmp_path / ".locus"
    vault_dir = locus_home / "vault"
    vault_dir.mkdir(parents=True, exist_ok=True)
    (locus_home / ".env").write_text("COUCHDB_PASSWORD=integration_secret_test_key\n", encoding="utf-8")
    monkeypatch.setenv("LOCUS_HOME", str(locus_home))

    registry = ProviderRegistry()
    registry.register("vault_sync", "couchdb_livesync", CouchDBLiveSyncProvider)

    app = create_app(registry=registry)
    client = TestClient(app)

    # 1. GET /vault/sync/status
    res_status = client.get("/vault/sync/status")
    assert res_status.status_code == 200
    data = res_status.json()
    assert data["status"] == "ok"
    assert data["sync"]["connected"] is True
    assert data["sync"]["sync_engine"] == "couchdb_livesync"

    # 2. POST /vault/sync/push with existing note
    test_note = vault_dir / "01-Projects" / "LocusPlan.md"
    test_note.parent.mkdir(parents=True, exist_ok=True)
    test_note.write_text("# Locus Plan\nExecution details\n", encoding="utf-8")

    res_push = client.post("/vault/sync/push", json={"path": "01-Projects/LocusPlan.md"})
    assert res_push.status_code == 200
    push_data = res_push.json()
    assert push_data["status"] == "ok"
    assert push_data["result"]["path"] == "01-Projects/LocusPlan.md"
    assert push_data["result"]["status"] == "pushed"


def test_livesync_service_off_switch_returns_503(monkeypatch, tmp_path: Path):
    """SPEC §03 line 35: "a disabled feature's HTTP routes answer 503 with {'disabled': '<config key>'}"."""
    locus_home = tmp_path / ".locus"
    locus_home.mkdir(parents=True, exist_ok=True)
    (locus_home / ".env").write_text("COUCHDB_PASSWORD=integration_secret_test_key\n", encoding="utf-8")
    monkeypatch.setenv("LOCUS_HOME", str(locus_home))

    # Disable sync
    monkeypatch.setattr(config, "get", lambda k, d=None: False if k == "locus.vault.sync.enabled" else d)

    registry = ProviderRegistry()
    registry.register("vault_sync", "couchdb_livesync", CouchDBLiveSyncProvider)

    app = create_app(registry=registry)
    client = TestClient(app)

    res_status = client.get("/vault/sync/status")
    assert res_status.status_code == 503
    assert res_status.json() == {"disabled": "locus.vault.sync.enabled"}

    res_push = client.post("/vault/sync/push", json={"path": "01-Projects/test.md"})
    assert res_push.status_code == 503
    assert res_push.json() == {"disabled": "locus.vault.sync.enabled"}
