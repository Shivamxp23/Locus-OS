"""
SPEC §23.1-23.5 line 8440: "## Feature §23.1-23.5: Tests, Docker, Batch Runner"
Unit tests for CI/CD, Docker Deployment, and Batch Runner (F-0054 / US-84).
Asserts Docker compose multi-container topology, loopback binding security,
hardened systemd unit generation, batch trajectory evaluation variance,
swappable provider interface, and modular off-switches.
"""
from __future__ import annotations

from typing import Any
import pytest

import sidecar.config as config
from sidecar.deployment.batch_runner import (
    BatchEvaluationReport,
    BatchTrajectoryRunner,
    RunResult,
)
from sidecar.deployment.docker_orchestrator import (
    ContainerConfig,
    DockerOrchestrator,
    DockerTopologyStatus,
)
from sidecar.deployment.systemd_generator import (
    SystemdGenerator,
    SystemdUnitConfig,
)
from sidecar.providers.ci_cd_docker import (
    BaseDeploymentProvider,
    DefaultDeploymentProvider,
)


def test_docker_orchestrator_topology() -> None:
    """SPEC §23.2 lines 8446-8473: 5-container topology inspection and loopback isolation."""
    orchestrator = DockerOrchestrator(compose_path="docker-compose.yml")
    status = orchestrator.inspect_topology()

    assert status.valid is True
    assert status.service_count >= 5
    assert "sidecar" in status.services
    assert "couchdb" in status.services
    assert "neo4j" in status.services
    assert "postgres" in status.services
    assert "redis" in status.services

    # Verify loopback binding for security
    for svc_name, cfg in status.services.items():
        for port in cfg.ports:
            assert not port.startswith("0.0.0.0:"), f"Insecure port binding in {svc_name}: {port}"
            assert port.startswith("127.0.0.1:"), f"Port must bind to 127.0.0.1: {port}"


def test_systemd_generator_hardening() -> None:
    """SPEC §23.1: Hardened Linux systemd service unit generation."""
    gen = SystemdGenerator()

    # 1. Sidecar unit
    sidecar_unit = gen.generate_sidecar_unit(
        working_dir="/opt/locus/locus-os",
        user="locus",
        env_file="/opt/locus/.locus/.env",
    )
    assert "Description=Locus Personal Intelligence Sidecar Service" in sidecar_unit
    assert "NoNewPrivileges=true" in sidecar_unit
    assert "PrivateTmp=true" in sidecar_unit
    assert "EnvironmentFile=-/opt/locus/.locus/.env" in sidecar_unit
    assert "Restart=on-failure" in sidecar_unit

    # 2. Agent unit
    agent_unit = gen.generate_agent_unit()
    assert "Description=Locus Supervisor & Autonomous Agent Engine" in agent_unit
    assert "--headless" in agent_unit


def test_batch_trajectory_runner_evaluation() -> None:
    """SPEC §23.5 lines 8475-8488: Batch evaluation across multiple trajectory runs."""
    runner = BatchTrajectoryRunner()
    report = runner.batch_evaluate("Test complex reasoning query", n_runs=4)

    assert report.n_runs == 4
    assert report.successful_runs == 4
    assert report.total_tokens_consumed > 0
    assert report.mean_tokens > 0
    assert 0.0 <= report.consistency_score <= 1.0
    assert len(report.runs) == 4
    assert len(report.unique_tool_calls) >= 1

    d = report.to_dict()
    assert d["n_runs"] == 4
    assert "runs" in d


def test_swappable_deployment_provider() -> None:
    """Verify BaseDeploymentProvider interface and DefaultDeploymentProvider swappability."""
    class CustomDeploymentProvider(BaseDeploymentProvider):
        @property
        def name(self) -> str:
            return "custom_deploy"

        def is_feature_enabled(self) -> tuple[bool, str]:
            return True, ""

        def inspect_docker_topology(self) -> dict[str, Any]:
            return {"status": "ok", "custom": True}

        def generate_systemd_unit(self, service_type: str = "sidecar", working_dir: str = "", user: str = "", env_file: str = "") -> dict[str, Any]:
            return {"status": "ok", "custom": True}

        def evaluate_batch(self, prompt: str, n_runs: int = 3) -> dict[str, Any]:
            return {"status": "ok", "custom": True}

        def get_status(self) -> dict[str, Any]:
            return {"status": "ok", "custom_active": True}

    custom = CustomDeploymentProvider()
    assert custom.name == "custom_deploy"
    assert custom.inspect_docker_topology()["custom"] is True

    default_prov = DefaultDeploymentProvider()
    assert default_prov.name == "default_deployment_provider"
    assert default_prov.inspect_docker_topology()["valid"] is True


def test_deployment_provider_off_switches(monkeypatch: pytest.MonkeyPatch) -> None:
    """SPEC §23.1: Modular off-switches locus.ci_cd_docker.enabled and locus.deployment.enabled return 503."""
    provider = DefaultDeploymentProvider()

    # Enabled when config has no setting
    enabled, switch = provider.is_feature_enabled()
    assert enabled is True

    # Disable via locus.ci_cd_docker.enabled
    monkeypatch.setattr(config, "get", lambda key, default=None: False if key == "locus.ci_cd_docker.enabled" else None)
    monkeypatch.setattr(config, "is_enabled", lambda key, default=False: False if key == "locus.ci_cd_docker.enabled" else True)

    enabled, switch = provider.is_feature_enabled()
    assert enabled is False
    assert switch == "locus.ci_cd_docker.enabled"

    res_inspect = provider.inspect_docker_topology()
    assert res_inspect["status_code"] == 503
    assert res_inspect["disabled"] == "locus.ci_cd_docker.enabled"

    res_unit = provider.generate_systemd_unit()
    assert res_unit["status_code"] == 503

    res_batch = provider.evaluate_batch("prompt")
    assert res_batch["status_code"] == 503

    # Disable via locus.deployment.enabled
    monkeypatch.setattr(config, "get", lambda key, default=None: False if key == "locus.deployment.enabled" else None)
    monkeypatch.setattr(config, "is_enabled", lambda key, default=False: False if key == "locus.deployment.enabled" else True)

    enabled2, switch2 = provider.is_feature_enabled()
    assert enabled2 is False
    assert switch2 == "locus.deployment.enabled"
