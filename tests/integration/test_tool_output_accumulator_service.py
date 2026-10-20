"""
SPEC §3.10 / F-0102 / US-43: Integration Tests for Tool Output Accumulator Service.
Asserts FastAPI routes `/tools/accumulator/create`, `/tools/accumulator/{id}/append`,
`/tools/accumulator/{id}/snapshot`, `/tools/accumulator/{id}/finish`, `/tools/accumulator/{id}/full`,
and the modular 503 off-switch on locus.tool_output_accumulator.enabled.
"""
import pytest
from fastapi.testclient import TestClient

import sidecar.config as config
from sidecar.service import create_app


@pytest.fixture
def client():
    config._CONFIG_CACHE = None
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    config._CONFIG_CACHE = None


def test_accumulator_service_full_lifecycle(client):
    """SPEC §3.10 line 2700: "Scope: Built-in truncation. Inherited unchanged." """
    # 1. Create accumulator
    resp_create = client.post(
        "/tools/accumulator/create",
        json={"max_lines": 5, "max_bytes": 100},
    )
    assert resp_create.status_code == 200
    acc_id = resp_create.json()["accumulator_id"]
    assert acc_id

    # 2. Append chunks
    for i in range(10):
        resp_append = client.post(
            f"/tools/accumulator/{acc_id}/append",
            json={"data": f"Line {i} output content\n"},
        )
        assert resp_append.status_code == 200

    # 3. Snapshot
    resp_snap = client.get(f"/tools/accumulator/{acc_id}/snapshot")
    assert resp_snap.status_code == 200
    snap_data = resp_snap.json()["snapshot"]
    assert snap_data["truncated"] is True
    assert snap_data["total_lines"] == 10

    # 4. Finish
    resp_finish = client.post(f"/tools/accumulator/{acc_id}/finish")
    assert resp_finish.status_code == 200

    # 5. Full output
    resp_full = client.get(f"/tools/accumulator/{acc_id}/full?max_bytes=60")
    assert resp_full.status_code == 200
    full_data = resp_full.json()["full_output"]
    assert full_data["truncated"] is True
    assert "omitted" in full_data["content"]

    # 6. Delete
    resp_del = client.delete(f"/tools/accumulator/{acc_id}")
    assert resp_del.status_code == 200

    # 7. Post-delete check
    resp_post_del = client.get(f"/tools/accumulator/{acc_id}/snapshot")
    assert resp_post_del.status_code == 404


def test_accumulator_service_404_not_found(client):
    """SPEC §3.10 line 2700: "Scope: Built-in truncation. Inherited unchanged." """
    resp = client.post(
        "/tools/accumulator/non-existent-id/append",
        json={"data": "test"},
    )
    assert resp.status_code == 404


def test_accumulator_service_config(client):
    """SPEC §3.10 line 2699: "Off state: N/A (core Pi infrastructure)" """
    resp = client.get("/tools/accumulator/config")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["enabled"] is True
    assert data["provider"] == "ToolOutputAccumulatorProvider"
    assert "config" in data


def test_accumulator_service_off_switch_503(client, monkeypatch):
    """SPEC §3.10 line 2699: "Off state: N/A (core Pi infrastructure)" """
    original_get = config.get

    def fake_get(key: str, default=None):
        if key == "locus.tool_output_accumulator.enabled":
            return False
        return original_get(key, default)

    monkeypatch.setattr(config, "get", fake_get)

    # 1. POST create returns 503
    resp_create = client.post("/tools/accumulator/create", json={})
    assert resp_create.status_code == 503
    assert resp_create.json()["disabled"] == "locus.tool_output_accumulator.enabled"

    # 2. GET config returns 503
    resp_config = client.get("/tools/accumulator/config")
    assert resp_config.status_code == 503
    assert resp_config.json()["disabled"] == "locus.tool_output_accumulator.enabled"
