"""
SPEC §23.1-23.5 lines 8440-8490: CI/CD, Docker Deployment & Batch Runner Provider.
Provides BaseDeploymentProvider and DefaultDeploymentProvider with modular off-switches:
- locus.ci_cd_docker.enabled
- locus.deployment.enabled
Returning HTTP 503 when disabled.
"""
from __future__ import annotations

import abc
import logging
from typing import Any

import sidecar.config as config
from sidecar.deployment.batch_runner import (
    BatchEvaluationReport,
    BatchTrajectoryRunner,
)
from sidecar.deployment.docker_orchestrator import (
    DockerOrchestrator,
    DockerTopologyStatus,
)
from sidecar.deployment.systemd_generator import (
    SystemdGenerator,
    SystemdUnitConfig,
)

logger = logging.getLogger("locus.providers.deployment")


class BaseDeploymentProvider(abc.ABC):
    """Abstract base provider for deployment orchestration, systemd management, and batch trajectory evaluations."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Provider name."""
        raise NotImplementedError

    @abc.abstractmethod
    def is_feature_enabled(self) -> tuple[bool, str]:
        """Check if deployment features are enabled via config."""
        raise NotImplementedError

    @abc.abstractmethod
    def inspect_docker_topology(self) -> dict[str, Any]:
        """Inspect and validate container topology and port bindings."""
        raise NotImplementedError

    @abc.abstractmethod
    def generate_systemd_unit(
        self,
        service_type: str = "sidecar",
        working_dir: str = "/opt/locus/locus-os",
        user: str = "locus",
        env_file: str = "/opt/locus/.locus/.env",
    ) -> dict[str, Any]:
        """Generate hardened systemd unit file for headless service."""
        raise NotImplementedError

    @abc.abstractmethod
    def evaluate_batch(self, prompt: str, n_runs: int = 3) -> dict[str, Any]:
        """Execute batch prompt evaluation comparing variance across trajectories."""
        raise NotImplementedError

    @abc.abstractmethod
    def get_status(self) -> dict[str, Any]:
        """Return diagnostic runtime state."""
        raise NotImplementedError


class DefaultDeploymentProvider(BaseDeploymentProvider):
    """
    Default deployment provider wrapping DockerOrchestrator, SystemdGenerator, and BatchTrajectoryRunner.
    Enforces modular off-switches locus.ci_cd_docker.enabled and locus.deployment.enabled (HTTP 503).
    """

    def __init__(
        self,
        orchestrator: DockerOrchestrator | None = None,
        systemd: SystemdGenerator | None = None,
        runner: BatchTrajectoryRunner | None = None,
    ) -> None:
        self.orchestrator = orchestrator or DockerOrchestrator()
        self.systemd = systemd or SystemdGenerator()
        self.runner = runner or BatchTrajectoryRunner()

    @property
    def name(self) -> str:
        return "default_deployment_provider"

    def is_feature_enabled(self) -> tuple[bool, str]:
        """Evaluate modular off-switches."""
        for switch in ("locus.ci_cd_docker.enabled", "locus.deployment.enabled"):
            val = config.get(switch)
            if val is not None and not config.is_enabled(switch):
                return False, switch
        return True, ""

    def inspect_docker_topology(self) -> dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {"error": "feature_disabled", "disabled": switch, "status_code": 503}
        status = self.orchestrator.inspect_topology()
        return {
            "status": "ok" if status.valid else "warning",
            "valid": status.valid,
            "service_count": status.service_count,
            "security_violations": status.security_violations,
            "errors": status.errors,
            "services": {k: {"image": v.image, "ports": v.ports, "restart": v.restart_policy} for k, v in status.services.items()},
        }

    def generate_systemd_unit(
        self,
        service_type: str = "sidecar",
        working_dir: str = "/opt/locus/locus-os",
        user: str = "locus",
        env_file: str = "/opt/locus/.locus/.env",
    ) -> dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {"error": "feature_disabled", "disabled": switch, "status_code": 503}
        
        if service_type == "agent":
            unit_content = self.systemd.generate_agent_unit(working_dir=working_dir, user=user, env_file=env_file)
        else:
            unit_content = self.systemd.generate_sidecar_unit(working_dir=working_dir, user=user, env_file=env_file)

        return {
            "status": "ok",
            "service_type": service_type,
            "unit_content": unit_content,
        }

    def evaluate_batch(self, prompt: str, n_runs: int = 3) -> dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {"error": "feature_disabled", "disabled": switch, "status_code": 503}
        report = self.runner.batch_evaluate(prompt=prompt, n_runs=n_runs)
        return {
            "status": "ok",
            "report": report.to_dict(),
        }

    def get_status(self) -> dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {"error": "feature_disabled", "disabled": switch, "status_code": 503}
        return {
            "compose_file": str(self.orchestrator.compose_path),
            "compose_exists": self.orchestrator.compose_path.is_file(),
            "runner_ready": True,
        }
