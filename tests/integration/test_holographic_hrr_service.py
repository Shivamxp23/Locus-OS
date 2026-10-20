"""
tests/integration/test_holographic_hrr_service.py
Integration tests for Holographic HRR FastAPI service endpoints per SPEC §4.10 / F-0022.
"""
from __future__ import annotations

import tempfile
from pathlib import Path
import pytest
from starlette.testclient import TestClient

import sidecar.config as config
from sidecar.service import create_app


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch):
    tmp = tempfile.NamedTemporaryFile(suffix=".npz", delete=False)
    tmp.close()

    orig_get = config.get

    def _cfg_get(key: str, default=None):
        if key == "locus.memory.hrr.codebook_path":
            return tmp.name
        if key == "locus.memory.hrr.dimension":
            return 512
        return orig_get(key, default)

    monkeypatch.setattr(config, "get", _cfg_get)
    config._CONFIG_CACHE = None
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    config._CONFIG_CACHE = None
    try:
        Path(tmp.name).unlink(missing_ok=True)
    except Exception:
        pass


def test_service_hrr_config(client: TestClient) -> None:
    """
    SPEC §4.10 line 1240: "codebook cache persisted at .locus/memory/hrr_codebook.bin."
    Asserts config endpoint returns status ok and enabled configuration.
    """
    res = client.get("/memory/hrr/config")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["config"]["enabled"] is True
    assert data["config"]["dimension"] == 512


def test_service_symbol_creation_and_retrieval(client: TestClient) -> None:
    """
    SPEC §4.10 line 1189: "Codebook: symbols: Dict[string -> HRRVector]"
    Asserts codebook symbol generation, listing, and single symbol retrieval.
    """
    post_res = client.post("/memory/hrr/codebook/symbol", json={"symbol": "ROLE:TASK"})
    assert post_res.status_code == 200
    vec_data = post_res.json()["vector"]
    assert vec_data["dimension"] == 512
    assert len(vec_data["values"]) == 512

    list_res = client.get("/memory/hrr/codebook/symbols")
    assert list_res.status_code == 200
    symbols = list_res.json()["symbols"]
    assert "ROLE:TASK" in symbols

    get_res = client.get("/memory/hrr/codebook/symbols/ROLE:TASK")
    assert get_res.status_code == 200
    assert get_res.json()["symbol"] == "ROLE:TASK"

    missing_res = client.get("/memory/hrr/codebook/symbols/NON_EXISTENT")
    assert missing_res.status_code == 404


def test_service_bind_and_unbind(client: TestClient) -> None:
    """
    SPEC §4.10 line 1195: "FUNCTION bind(a: HRRVector, b: HRRVector) -> HRRVector:"
    SPEC §4.10 line 1204: "FUNCTION unbind(c: HRRVector, b: HRRVector) -> HRRVector:"
    Asserts HTTP endpoints perform circular convolution and unbinding.
    """
    sym_a = client.post("/memory/hrr/codebook/symbol", json={"symbol": "KEY:X"}).json()["vector"]
    sym_b = client.post("/memory/hrr/codebook/symbol", json={"symbol": "VAL:Y"}).json()["vector"]

    bind_res = client.post("/memory/hrr/bind", json={"a": sym_a, "b": sym_b})
    assert bind_res.status_code == 200
    bound = bind_res.json()["vector"]
    assert bound["dimension"] == 512

    unbind_res = client.post("/memory/hrr/unbind", json={"c": bound, "b": sym_a})
    assert unbind_res.status_code == 200
    unbound = unbind_res.json()["vector"]

    # Verify cleanup on unbound vector returns VAL:Y
    clean_res = client.post("/memory/hrr/cleanup", json={"vector": unbound, "threshold": 0.70})
    assert clean_res.status_code == 200
    assert clean_res.json()["symbol"] == "VAL:Y"
    assert clean_res.json()["similarity"] > 0.85


def test_service_bundle_and_encode_state(client: TestClient) -> None:
    """
    SPEC §4.10 line 1210: "FUNCTION bundle(vectors: List[HRRVector]) -> HRRVector:"
    SPEC §4.10 line 1226: "FUNCTION encode_ephemeral_state(current_task, active_mode, stress_level) -> HRRVector:"
    Asserts superposition bundling and fast ephemeral state encoding endpoints.
    """
    v1 = client.post("/memory/hrr/codebook/symbol", json={"symbol": "SYM:1"}).json()["vector"]
    v2 = client.post("/memory/hrr/codebook/symbol", json={"symbol": "SYM:2"}).json()["vector"]

    bundle_res = client.post("/memory/hrr/bundle", json={"vectors": [v1, v2]})
    assert bundle_res.status_code == 200
    bundled = bundle_res.json()["vector"]
    assert bundled["dimension"] == 512

    # State encoding endpoint
    state_res = client.post(
        "/memory/hrr/encode_state",
        json={
            "current_task": {"id": "feat_hrr"},
            "active_mode": {"name": "DEEP_WORK"},
            "stress_level": {"category": "NOMINAL"},
        },
    )
    assert state_res.status_code == 200
    state_vec = state_res.json()["vector"]
    assert state_vec["dimension"] == 512


def test_service_off_switch_503(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    SPEC §4.10 line 1241: "Swappable / off state: locus.memory.hrr.enabled. Off -> Locus skips holographic state bundling; uses standard JSON key-value store in Redis."
    Asserts endpoints return 503 when off switch is disabled.
    """
    orig_get = config.get

    def _disabled_get(key: str, default=None):
        if key in ("locus.holographic_hrr.enabled", "locus.memory.hrr.enabled"):
            return False
        return orig_get(key, default)

    monkeypatch.setattr(config, "get", _disabled_get)
    config._CONFIG_CACHE = None
    app = create_app()
    with TestClient(app) as test_client:
        res = test_client.get("/memory/hrr/config")
        assert res.status_code == 503
        assert res.json() == {"disabled": "locus.holographic_hrr.enabled"}

        post_res = test_client.post("/memory/hrr/bind", json={"a": {}, "b": {}})
        assert post_res.status_code == 503
        assert post_res.json() == {"disabled": "locus.holographic_hrr.enabled"}
