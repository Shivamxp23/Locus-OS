"""
Integration tests for Post-Turn Background Review FastAPI endpoints (SPEC §1.7 & §10.1, F-0007 / US-26).
Asserts POST /review/post-turn dispatch, GET /review/tools/allowed whitelist,
GET /review/skills/preferences hierarchy, GET /review/result/{review_id},
and the 503 off-switch when locus.post_turn_review.enabled is False.
"""
import pytest
from fastapi.testclient import TestClient

import sidecar.config as config
from sidecar.service import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_post_turn_review_dispatch_endpoint(client):
    """SPEC §1.7 line 2855: "// CRITICAL: This runs on a DAEMON THREAD, never blocks the main loop"."""
    messages = [
        {"role": "user", "content": "Always remember to use snake_case for Python variables."},
        {"role": "assistant", "content": "Acknowledged."},
    ]
    res = client.post(
        "/review/post-turn",
        json={"messages": messages, "session_id": "integration-sess-1", "sync": True},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    result = data["result"]
    assert result["session_id"] == "integration-sess-1"
    assert result["status"] == "completed"
    assert len(result["memory_insights"]) >= 1


def test_allowed_review_tools_endpoint(client):
    """SPEC §1.7 line 2861: "tool_whitelist = [\"memory\", \"skill_manage\"],  // ONLY these tools allowed"."""
    res = client.get("/review/tools/allowed")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "memory" in data["allowed_tools"]
    assert "skill_manage" in data["allowed_tools"]
    assert "bash" not in data["allowed_tools"]
    assert "write_file" not in data["allowed_tools"]


def test_skill_preferences_endpoint(client):
    """SPEC §1.7 line 2890: "1. UPDATE A CURRENTLY-LOADED SKILL (the one in play this session)"."""
    res = client.get("/review/skills/preferences")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    prefs = data["preferences"]
    assert len(prefs) == 4
    assert prefs[0] == "update_currently_loaded"
    assert prefs[1] == "update_existing_umbrella"
    assert prefs[2] == "add_support_file"
    assert prefs[3] == "create_new_umbrella"


def test_get_review_result_endpoint(client):
    """SPEC §1.7 line 2877: "// Thread runs in background. Main conversation continues immediately."."""
    # First dispatch a review sync
    messages = [{"role": "user", "content": "Remember to save my draft template."}]
    disp_res = client.post("/review/post-turn", json={"messages": messages, "sync": True})
    assert disp_res.status_code == 200
    review_id = disp_res.json()["result"]["review_id"]

    # Now retrieve by ID
    get_res = client.get(f"/review/result/{review_id}")
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data["status"] == "ok"
    assert get_data["result"]["review_id"] == review_id

    # 404 for missing
    missing_res = client.get("/review/result/non-existent-review-id")
    assert missing_res.status_code == 404


def test_post_turn_review_off_switch_503(monkeypatch):
    """SPEC §1.7 line 2887: "// This prevents the review agent from side-effecting the filesystem"."""
    monkeypatch.setattr(config, "get", lambda key, default=None: False if "post_turn_review" in key else default)
    monkeypatch.setattr(config, "is_enabled", lambda key: False if "post_turn_review" in key else True)
    app = create_app()
    client = TestClient(app)

    r1 = client.post("/review/post-turn", json={"messages": []})
    assert r1.status_code == 503
    assert r1.json() == {"disabled": "locus.post_turn_review.enabled"}

    r2 = client.get("/review/tools/allowed")
    assert r2.status_code == 503
    assert r2.json() == {"disabled": "locus.post_turn_review.enabled"}

    r3 = client.get("/review/skills/preferences")
    assert r3.status_code == 503
    assert r3.json() == {"disabled": "locus.post_turn_review.enabled"}

    r4 = client.get("/review/result/rev-1234")
    assert r4.status_code == 503
    assert r4.json() == {"disabled": "locus.post_turn_review.enabled"}
