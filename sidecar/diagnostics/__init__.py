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
from sidecar.diagnostics.notifications import (
    BaseNotificationChannel,
    MemoryNotificationChannel,
    NotificationDeliveryResult,
    NotificationDispatcher,
    NotificationPriority,
    QueuedNotification,
)
from sidecar.diagnostics.connectivity import (
    ConnectivityChecker,
    DEFAULT_CONNECTIVITY_ENDPOINTS,
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
    "NotificationPriority",
    "QueuedNotification",
    "NotificationDeliveryResult",
    "BaseNotificationChannel",
    "MemoryNotificationChannel",
    "NotificationDispatcher",
    "ConnectivityChecker",
    "DEFAULT_CONNECTIVITY_ENDPOINTS",
]
