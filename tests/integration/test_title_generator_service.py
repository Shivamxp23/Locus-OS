"""
Integration tests for Title Generation FastAPI endpoints (SPEC §1.11 / F-0011 / US-30).
Asserts title generation, artifact cleaning, prompt template assembly, and 503 off-switch.
"""
import pytest
from fastapi.testclient import TestClient

import sidecar.config as config
from sidecar.service import create_app
from sidecar.title_generator import TitleGeneratorProvider


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_title_generate_endpoint(client):
    """SPEC §1.11 line 2390: "FUNCTION generate_title(user_message, assistant_response, timeout=30s):"."""
    res = client.post(
        "/title/generate",
        json={
            "user_message": "How do I implement OAuth2 authentication in FastAPI?",
            "assistant_response": "You can use OAuth2PasswordBearer and python-jose.",
            "timeout": 20.0,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "title" in data
    assert len(data["title"]) > 0
    assert not data["title"].lower().startswith("title:")


def test_title_clean_endpoint(client):
    """SPEC §1.11 line 2415: "// Clean up artifacts"."""
    res = client.post(
        "/title/clean",
        json={
            "raw_title": 'Title: "Building a Distributed SQLite Database Engine..."',
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["cleaned_title"] == "Building a Distributed SQLite Database Engine"


def test_title_prompt_endpoint(client):
    """SPEC §1.11 line 2392: "// Truncate to keep request small"."""
    res = client.get("/title/prompt?user_snippet=Hello&assistant_snippet=World")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["prompt"]["task"] == "title_generation"
    assert "Generate a short, descriptive title" in data["prompt"]["messages"][0]["content"]


def test_title_service_503_off_switch(client, monkeypatch):
    """SPEC §1.11 line 2431: "Swappable / off state: locus.sessions.auto_title.enabled. Off → sessions use default timestamp-based titles"."""
    monkeypatch.setattr(config, "get", lambda k, d=None: False if "title" in k else True)
    monkeypatch.setattr(config, "is_enabled", lambda k, d=True: False if "title" in k else True)

    gen_res = client.post(
        "/title/generate",
        json={"user_message": "Explain quantum superposition", "assistant_response": "In quantum mechanics..."},
    )
    assert gen_res.status_code == 503
    assert "disabled" in gen_res.json()

    clean_res = client.post(
        "/title/clean",
        json={"raw_title": "Quantum Computing"},
    )
    assert clean_res.status_code == 503

    prompt_res = client.get("/title/prompt")
    assert prompt_res.status_code == 503
