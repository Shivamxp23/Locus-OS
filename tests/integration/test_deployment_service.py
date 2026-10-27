"""
SPEC §23.1-23.5 lines 8440-8490: Integration tests for CI/CD, Docker Deployment, and Batch Runner routes (F-0054 / US-84).
Tests FastAPI endpoints under /deployment/ and modular off-switches returning HTTP 503.
"""
from __future__ import annotations

import pytest
from starlette.testclient import TestClient

import sidecar.config as config
from sidecar.deployment.batch_runner import BatchTrajectoryRunner
from sidecar.deployment.docker_orchestrator import DockerOrchestrator
from sidecar.deployment.systemd_generator import SystemdGenerator
from sidecar.providers.ci_cd_docker import DefaultDeploymentProvider
from sidecar.service import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    orchestrator = DockerOrchestrator(compose_path="docker-compose.yml")
    systemd = SystemdGenerator()
    runner = BatchTrajectoryRunner()
    provider = DefaultDeploymentProvider(orchestrator=orchestrator, systemd=systemd, runner=runner)
    app.state.deployment_provider = provider
    return TestClient(app)


def test_deployment_service_docker_status(client: TestClient) -> None:
    """SPEC §23.2 line 8446: GET /deployment/docker/status endpoint."""
    res = client.get("/deployment/docker/status")
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True
    assert data["service_count"] >= 5
    assert "sidecar" in data["services"]
    assert len(data["security_violations"]) == 0


def test_deployment_service_systemd_generate(client: TestClient) -> None:
    """SPEC §23.1: POST /deployment/systemd/generate endpoint."""
    res = client.post(
        "/deployment/systemd/generate",
        json={"service_type": "sidecar", "working_dir": "/opt/locus", "user": "locus"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "NoNewPrivileges=true" in data["unit_content"]
    assert "WorkingDirectory=/opt/locus" in data["unit_content"]


def test_deployment_service_batch_evaluate(client: TestClient) -> None:
    """SPEC §23.5 lines 8475-8488: POST /deployment/batch/evaluate endpoint."""
    res = client.post(
        "/deployment/batch/evaluate",
        json={"prompt": "Deploy containerized research job", "n_runs": 3},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    report = data["report"]
    assert report["n_runs"] == 3
    assert report["successful_runs"] == 3
    assert "consistency_score" in report


def test_deployment_service_status(client: TestClient) -> None:
    """GET /deployment/status diagnostic route."""
    res = client.get("/deployment/status")
    assert res.status_code == 200
    data = res.json()
    assert data["compose_exists"] is True
    assert data["runner_ready"] is True


def test_deployment_service_off_switches(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """SPEC §23.1: Modular off-switches return HTTP 503."""
    # Switch 1: locus.ci_cd_docker.enabled
    monkeypatch.setattr(config, "get", lambda key, default=None: False if key == "locus.ci_cd_docker.enabled" else True)
    monkeypatch.setattr(config, "is_enabled", lambda key, default=False: False if key == "locus.ci_cd_docker.enabled" else True)

    res_docker = client.get("/deployment/docker/status")
    assert res_docker.status_code == 503
    assert res_docker.json()["disabled"] == "locus.ci_cd_docker.enabled"

    res_gen = client.post("/deployment/systemd/generate", json={})
    assert res_gen.status_code == 503

    res_eval = client.post("/deployment/batch/evaluate", json={"prompt": "test"})
    assert res_eval.status_code == 503

    # Switch 2: locus.deployment.enabled
    monkeypatch.setattr(config, "get", lambda key, default=None: False if key == "locus.deployment.enabled" else None)
    monkeypatch.setattr(config, "is_enabled", lambda key, default=False: False if key == "locus.deployment.enabled" else True)

    res_status2 = client.get("/deployment/status")
    assert res_status2.status_code == 503
    assert res_status2.json()["disabled"] == "locus.deployment.enabled"
