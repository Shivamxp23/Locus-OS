"""
SPEC §27.2 / §03 / §23 / 10-security.md / F-0060 / US-16: Obsidian LiveSync and CouchDB Security Tests.
Tests:
- CouchDB loopback-only binding in docker-compose.yml and CORS origin constraints in local.ini (S-2).
- Credential loading from .env and strict rejection of default/missing passwords.
- Deterministic conflict resolution preserving both revisions without conflict markers in note markdown.
- Clean 3-way text merge for non-overlapping note edits.
- Modular off-switch, provider swap, and health check behaviors.
"""
from __future__ import annotations

import os
from pathlib import Path
import tempfile
import time
from typing import Any, Dict, Optional
import pytest
import yaml

from sidecar import config
from sidecar.providers.vault_sync import BaseVaultSyncProvider
from sidecar.registry import ProviderRegistry, get_registry
from sidecar.vault.livesync_bridge import (
    CouchDBLiveSyncProvider,
    FORBIDDEN_DEFAULT_PASSWORD,
    diff3_merge,
    sha256_bytes,
)


class MockCouchHttpClient:
    """Mock HTTP client simulating CouchDB document endpoints."""

    def __init__(self) -> None:
        self.docs: Dict[str, Dict[str, Any]] = {}

    def get(self, url: str) -> Optional[Dict[str, Any]]:
        return self.docs.get(url)

    def put(self, url: str, json: Dict[str, Any]) -> Dict[str, Any]:
        rev = f"1-{sha256_bytes(str(json).encode())[:16]}"
        stored = dict(json)
        stored["_rev"] = rev
        self.docs[url] = stored
        return {"ok": True, "id": json.get("_id"), "rev": rev}


def test_livesync_couchdb_loopback_and_security():
    """SPEC 10-security.md line 31: "Every database and service port binds to loopback: 127.0.0.1:5984:5984"."""
    repo_root = Path(__file__).resolve().parents[2]
    compose_file = repo_root / "docker-compose.yml"
    assert compose_file.is_file(), f"docker-compose.yml missing at {compose_file}"

    compose_text = compose_file.read_text(encoding="utf-8")
    compose_yaml = yaml.safe_load(compose_text)

    # 1. Assert CouchDB port binding is loopback-only
    couch_svc = compose_yaml["services"]["couchdb"]
    ports = [str(p) for p in couch_svc.get("ports", [])]
    assert any(p == "127.0.0.1:5984:5984" for p in ports), f"CouchDB port not bound to loopback: {ports}"
    assert not any("0.0.0.0" in p for p in ports), "CouchDB must never bind to 0.0.0.0"

    # 2. Assert local.ini CORS restrictions
    ini_file = repo_root / "data" / "couchdb" / "local.ini"
    assert ini_file.is_file(), f"local.ini missing at {ini_file}"
    ini_text = ini_file.read_text(encoding="utf-8")
    assert "enable_cors = true" in ini_text
    assert "app://obsidian.md" in ini_text
    assert "capacitor://localhost" in ini_text
    assert "http://localhost" in ini_text


def test_livesync_credential_validation_and_rejection_of_default(monkeypatch, tmp_path: Path):
    """SPEC §23 / 10-security.md line 29: "docker-compose.yml uses ${COUCHDB_PASSWORD:?set it in .locus/.env} and no default"."""
    locus_home = tmp_path / ".locus"
    locus_home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("LOCUS_HOME", str(locus_home))
    monkeypatch.delenv("COUCHDB_PASSWORD", raising=False)

    # Case 1: Password completely missing -> ValueError
    (locus_home / ".env").write_text("COUCHDB_USER=admin\n", encoding="utf-8")
    with pytest.raises(ValueError) as excinfo:
        CouchDBLiveSyncProvider(validate=True)
    assert "CouchDB password not configured" in str(excinfo.value)

    # Case 2: Forbidden default password -> ValueError
    (locus_home / ".env").write_text(f"COUCHDB_PASSWORD={FORBIDDEN_DEFAULT_PASSWORD}\n", encoding="utf-8")
    with pytest.raises(ValueError) as excinfo:
        CouchDBLiveSyncProvider(validate=True)
    assert "forbidden default" in str(excinfo.value)

    # Case 3: Valid non-default password -> success
    (locus_home / ".env").write_text("COUCHDB_PASSWORD=secret_random_token_98765\n", encoding="utf-8")
    provider = CouchDBLiveSyncProvider(validate=True)
    assert provider.password == "secret_random_token_98765"


def test_livesync_deterministic_conflict_resolution(monkeypatch, tmp_path: Path):
    """SPEC §27.2 line 125: "Determine winner based on (mtime, hash) tuple. If winner is local: local preserved, remote saved as conflict note. Else: remote applied, local saved as conflict note." """
    locus_home = tmp_path / ".locus"
    vault_dir = locus_home / "vault"
    vault_dir.mkdir(parents=True, exist_ok=True)
    (locus_home / ".env").write_text("COUCHDB_PASSWORD=valid_secret_key_12345\n", encoding="utf-8")
    monkeypatch.setattr(config, "get_locus_home", lambda: locus_home)

    provider = CouchDBLiveSyncProvider()
    provider.initialize()

    test_note = vault_dir / "01-Projects" / "ProjectX.md"
    test_note.parent.mkdir(parents=True, exist_ok=True)

    # Scenario A: Local has higher timestamp than remote
    local_content = b"# Local Title\nLocal content from this workstation.\n"
    remote_content = b"# Remote Title\nConflicting edits from mobile device.\n"
    test_note.write_bytes(local_content)

    # Set local mtime explicitly
    local_time = 1700000200.0
    os.utime(test_note, (local_time, local_time))

    remote_doc = {
        "_id": "note:01-projects/projectx.md",
        "mtime": 1700000100000,  # Older remote
        "eden": {"content": remote_content.decode("utf-8")},
    }

    result = provider.resolve_conflicts(test_note, remote_doc, remote_content)
    assert result["resolved"] is True
    assert result["winner"] == "local"
    assert result["action"] == "local_won_remote_sidecar"

    # Canonical file keeps local content
    assert test_note.read_bytes() == local_content

    # Sidecar file holds remote content
    sidecar_path = Path(result["conflict_sidecar"])
    assert sidecar_path.is_file()
    assert "conflict" in sidecar_path.name
    assert sidecar_path.read_bytes() == remote_content

    # Neither note must have conflict markers
    assert b"<<<<<<<" not in test_note.read_bytes()
    assert b"<<<<<<<" not in sidecar_path.read_bytes()

    # Scenario B: Remote has higher timestamp than local
    test_note.write_bytes(local_content)
    os.utime(test_note, (local_time, local_time))

    newer_remote_doc = {
        "_id": "note:01-projects/projectx.md",
        "mtime": 1700000300000,  # Newer remote
        "eden": {"content": remote_content.decode("utf-8")},
    }

    result_b = provider.resolve_conflicts(test_note, newer_remote_doc, remote_content)
    assert result_b["resolved"] is True
    assert result_b["winner"] == "remote"
    assert result_b["action"] == "remote_won_local_sidecar"

    # Canonical file now holds remote content
    assert test_note.read_bytes() == remote_content
    # Sidecar file holds local content
    sidecar_b_path = Path(result_b["conflict_sidecar"])
    assert sidecar_b_path.is_file()
    assert sidecar_b_path.read_bytes() == local_content


def test_livesync_3way_text_merge(monkeypatch, tmp_path: Path):
    """SPEC §27.2 line 112: "Text-based 3-Way Merge for Markdown... If not has_conflicts: clean 3-way merge succeeded automatically." """
    locus_home = tmp_path / ".locus"
    vault_dir = locus_home / "vault"
    vault_dir.mkdir(parents=True, exist_ok=True)
    (locus_home / ".env").write_text("COUCHDB_PASSWORD=valid_secret_key_12345\n", encoding="utf-8")
    monkeypatch.setattr(config, "get_locus_home", lambda: locus_home)

    provider = CouchDBLiveSyncProvider()
    provider.initialize()

    note_path = vault_dir / "05-Daily" / "Journal.md"
    note_path.parent.mkdir(parents=True, exist_ok=True)

    base = "# Daily Log\n\n- Task 1: Started\n"
    local = "# Daily Log\n\n- Task 1: Started\n- Task 2: Local edit\n"
    remote = "# Daily Log\n\n- Task 1: Started\n- Task 3: Remote edit\n"

    note_path.write_text(local, encoding="utf-8")

    remote_doc = {
        "_id": "note:05-daily/journal.md",
        "mtime": int(time.time() * 1000),
        "base_content": base,
        "eden": {"content": remote},
    }

    result = provider.resolve_conflicts(note_path, remote_doc, remote.encode("utf-8"))
    assert result["resolved"] is True
    assert result["action"] == "3way_merged"
    merged = note_path.read_text(encoding="utf-8")
    assert "- Task 2: Local edit" in merged
    assert "- Task 3: Remote edit" in merged
    assert result["conflict_sidecar"] is None


def test_livesync_push_leaf_and_chunking(monkeypatch, tmp_path: Path):
    """SPEC §27.2 line 75: "Push local to CouchDB: If len(content_bytes) > CHUNK_THRESHOLD: Chunk large file... Else: leaf payload." """
    locus_home = tmp_path / ".locus"
    vault_dir = locus_home / "vault"
    vault_dir.mkdir(parents=True, exist_ok=True)
    (locus_home / ".env").write_text("COUCHDB_PASSWORD=valid_secret_key_12345\n", encoding="utf-8")
    monkeypatch.setattr(config, "get_locus_home", lambda: locus_home)

    mock_client = MockCouchHttpClient()
    provider = CouchDBLiveSyncProvider()
    provider.initialize(options={"http_client": mock_client})

    # 1. Leaf note (< 50KB)
    small_note = vault_dir / "03-Resources" / "Snippet.md"
    small_note.parent.mkdir(parents=True, exist_ok=True)
    small_note.write_text("# Small note content\n", encoding="utf-8", newline="\n")

    res_small = provider.push("03-Resources/Snippet.md")
    assert res_small["status"] == "pushed"
    assert res_small["doc_id"] == "note:03-resources/snippet.md"

    doc_url = f"{provider.couch_url}/{provider.database}/{res_small['doc_id']}"
    small_doc = mock_client.get(doc_url)
    assert small_doc is not None
    assert small_doc["type"] == "leaf"
    assert small_doc["eden"]["content"] == "# Small note content\n"

    # 2. Large note (> 50KB) chunks
    large_note = vault_dir / "03-Resources" / "BigFile.md"
    large_content = b"A" * 60000
    large_note.write_bytes(large_content)

    res_large = provider.push("03-Resources/BigFile.md")
    assert res_large["status"] == "pushed"

    large_doc_url = f"{provider.couch_url}/{provider.database}/{res_large['doc_id']}"
    large_doc = mock_client.get(large_doc_url)
    assert large_doc is not None
    assert large_doc["type"] == "chunks"
    assert len(large_doc["children"]) == 2  # 50000 + 10000


def test_livesync_off_switch(monkeypatch, tmp_path: Path):
    """SPEC §03 line 40: "enabled=false -> routes/tools/jobs absent, the rest of the system starts, the spec's 'Off ->' effect is visible." """
    locus_home = tmp_path / ".locus"
    vault_dir = locus_home / "vault"
    vault_dir.mkdir(parents=True, exist_ok=True)
    (locus_home / ".env").write_text("COUCHDB_PASSWORD=valid_secret_key_12345\n", encoding="utf-8")
    monkeypatch.setattr(config, "get_locus_home", lambda: locus_home)

    # Disable sync via config
    monkeypatch.setattr(config, "get", lambda k, d=None: "local_only" if k == "locus.vault.sync_engine" else d)

    provider = CouchDBLiveSyncProvider()
    provider.initialize()

    dummy_file = vault_dir / "00-System" / "test.md"
    dummy_file.parent.mkdir(parents=True, exist_ok=True)
    dummy_file.write_text("content", encoding="utf-8")

    push_res = provider.push("00-System/test.md")
    assert push_res["status"] == "skipped"
    assert push_res["reason"] == "sync_disabled"


def test_livesync_swap(monkeypatch, tmp_path: Path):
    """SPEC §03 line 41: "register a second fake provider under another name, set provider, assert the fake is called and the default is not." """
    reg = ProviderRegistry()

    class FakeSyncProvider(BaseVaultSyncProvider):
        def initialize(self, options=None): pass
        def shutdown(self): pass
        def health_check(self): return {"status": "fake_ok"}
        def status(self): return {"sync_engine": "fake_sync"}
        def push(self, rel_path, mtime=None): return {"status": "fake_pushed"}
        def pull(self, rel_path=None): return {"status": "fake_pulled"}
        def resolve_conflicts(self, disk_path, remote_doc, remote_bytes): return {"resolved": True}

    reg.register("vault_sync", "couchdb_livesync", CouchDBLiveSyncProvider)
    reg.register("vault_sync", "custom_sync", FakeSyncProvider)

    # Default resolves CouchDBLiveSyncProvider
    default_cls = reg.get_active_provider("vault_sync", default_name="couchdb_livesync")
    assert default_cls is CouchDBLiveSyncProvider

    # Swapped provider via config
    monkeypatch.setattr(config, "get", lambda k, d=None: "custom_sync" if "provider" in k else d)
    swapped_cls = reg.get_active_provider("vault_sync", default_name="couchdb_livesync")
    assert swapped_cls is FakeSyncProvider


def test_livesync_health(monkeypatch, tmp_path: Path):
    """SPEC §03 line 42: "health_check() returns status and latency, and reports a stopped dependency as not OK." """
    locus_home = tmp_path / ".locus"
    locus_home.mkdir(parents=True, exist_ok=True)
    (locus_home / ".env").write_text("COUCHDB_PASSWORD=valid_secret_key_12345\n", encoding="utf-8")
    monkeypatch.setenv("LOCUS_HOME", str(locus_home))

    provider = CouchDBLiveSyncProvider()
    uninit_health = provider.health_check()
    assert uninit_health["status"] == "degraded"

    provider.initialize()
    active_health = provider.health_check()
    assert active_health["status"] == "ok"
    assert active_health["latency_ms"] > 0
    assert active_health["couch_url"] == provider.couch_url
