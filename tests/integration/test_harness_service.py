"""
SPEC §3.7 + §11.5 / §03 line 35: Harness Delegation Service Integration Tests.
Tests HTTP endpoints on the sidecar service for task delegation, harness listing,
and modular 503 off-switch behavior.
"""
from __future__ import annotations

import subprocess
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from sidecar import config
from sidecar.harness.delegation import HarnessProvider
from sidecar.providers.harness import HarnessType
from sidecar.registry import ProviderRegistry
from sidecar.service import create_app


def test_harness_service_endpoints(monkeypatch):
    """SPEC §3.7 line 2735: "Harness delegation service endpoints execute tasks and list harnesses"."""
    def fake_subprocess_run(cmd, *args, **kwargs):
        mock = MagicMock()
        mock.returncode = 0
        if "worktree" in cmd:
            mock.stdout = "worktree ready"
            mock.stderr = ""
        elif "diff" in cmd and "--name-only" in cmd:
            mock.stdout = "src/main.py\n"
            mock.stderr = ""
        elif "diff" in cmd:
            mock.stdout = "+ print('hello')\n"
            mock.stderr = ""
        else:
            mock.stdout = "Harness finished execution"
            mock.stderr = ""
        return mock

    monkeypatch.setattr(subprocess, "run", fake_subprocess_run)

    registry = ProviderRegistry()
    registry.register("harness", "default_harness", HarnessProvider)

    app = create_app(registry=registry)
    client = TestClient(app)

    # 1. List available harnesses
    list_res = client.get("/harness/harnesses")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["status"] == "ok"
    assert HarnessType.PI.value in list_data["harnesses"]

    # 2. Delegate task execution
    del_res = client.post(
        "/harness/delegate",
        json={
            "description": "Add feature flag to main.py",
            "target_files": ["src/main.py"],
            "complexity": "normal",
        },
    )
    assert del_res.status_code == 200
    del_data = del_res.json()
    assert del_data["status"] == "ok"
    assert del_data["result"]["status"] == "success"
    assert "src/main.py" in del_data["result"]["modified_files"]
    assert "+ print('hello')" in del_data["result"]["diff"]


def test_harness_service_modular_off_switch(monkeypatch):
    """SPEC §03 line 35: "a disabled feature's HTTP routes answer 503 with {'disabled': '<config key>'}"."""
    monkeypatch.setattr(config, "get", lambda k, d=None: False if k == "locus.harness.enabled" else d)

    registry = ProviderRegistry()
    registry.register("harness", "default_harness", HarnessProvider)

    app = create_app(registry=registry)
    client = TestClient(app)

    # 1. Delegate endpoint returns 503
    del_res = client.post("/harness/delegate", json={"description": "Test off switch"})
    assert del_res.status_code == 503
    assert del_res.json() == {"disabled": "locus.harness.enabled"}

    # 2. List harnesses endpoint returns 503
    list_res = client.get("/harness/harnesses")
    assert list_res.status_code == 503
    assert list_res.json() == {"disabled": "locus.harness.enabled"}
