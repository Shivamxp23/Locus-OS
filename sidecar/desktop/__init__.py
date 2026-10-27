"""
Desktop automation and remote protocol control package.
"""
from sidecar.desktop.vnc_client import (
    BaseRFBProtocolClient,
    BoundingBox,
    MockRFBProtocolClient,
    SecurityException,
    VNCDesktopController,
    compute_bezier_path,
)

__all__ = [
    "BaseRFBProtocolClient",
    "BoundingBox",
    "MockRFBProtocolClient",
    "SecurityException",
    "VNCDesktopController",
    "compute_bezier_path",
]
