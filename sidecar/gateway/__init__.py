"""
SPEC §17.10 & §28.1-28.6: Gateway Subsystem (Dual-Interface & Lifecycle).
"""
from sidecar.gateway.lifecycle import (
    BaseChannelAdapter,
    ForensicRecord,
    GatewayLifecycleManager,
    MockChannelAdapter,
    SessionSnapshot,
)
from sidecar.gateway.dual_interface import (
    CheckInRecord,
    CheckInSlot,
    DualInterfaceEngine,
    SessionMessage,
)

__all__ = [
    "BaseChannelAdapter",
    "MockChannelAdapter",
    "ForensicRecord",
    "SessionSnapshot",
    "GatewayLifecycleManager",
    "CheckInRecord",
    "CheckInSlot",
    "DualInterfaceEngine",
    "SessionMessage",
]
