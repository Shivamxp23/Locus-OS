"""
Diagnostics and Observability subsystem symbols re-export.
"""
from sidecar.diagnostics.error_classifier import (
    ErrorCategory,
    ErrorClassification,
    ErrorClassifier,
    RecoveryAction,
)
from sidecar.diagnostics.auxiliary_client import (
    AuxiliaryGenerationRequest,
    AuxiliaryGenerationResult,
    AuxiliaryLLMClient,
    AuxiliaryLLMConfig,
    DEFAULT_AUXILIARY_MODEL,
    DEFAULT_MAIN_MODEL,
)
from sidecar.diagnostics.health_checker import (
    HealthChecker,
    ProviderHealthResult,
    SystemHealthReport,
    health_check_all,
)

__all__ = [
    "ErrorCategory",
    "RecoveryAction",
    "ErrorClassification",
    "ErrorClassifier",
    "AuxiliaryLLMConfig",
    "AuxiliaryGenerationRequest",
    "AuxiliaryGenerationResult",
    "AuxiliaryLLMClient",
    "DEFAULT_AUXILIARY_MODEL",
    "DEFAULT_MAIN_MODEL",
    "HealthChecker",
    "ProviderHealthResult",
    "SystemHealthReport",
    "health_check_all",
]
