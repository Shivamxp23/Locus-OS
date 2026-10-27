"""Desktop Computer Use & Screen Subsystem (§16.1-16.2 + §20.1-20.3)."""

from sidecar.screen.capture import (
    BaseScreenCaptureProvider,
    DesktopScreenCaptureProvider,
    MockScreenCaptureProvider,
    ScreenCaptureResult,
)
from sidecar.screen.desktop_control import (
    BaseDesktopController,
    DesktopAction,
    DesktopActionResult,
    MockDesktopController,
    NativeDesktopController,
)
from sidecar.screen.manager import ComputerUseManager
from sidecar.screen.screen_intelligence import (
    ScreenElement,
    ScreenIntelligence,
)

__all__ = [
    "BaseScreenCaptureProvider",
    "DesktopScreenCaptureProvider",
    "MockScreenCaptureProvider",
    "ScreenCaptureResult",
    "BaseDesktopController",
    "DesktopAction",
    "DesktopActionResult",
    "MockDesktopController",
    "NativeDesktopController",
    "ScreenElement",
    "ScreenIntelligence",
    "ComputerUseManager",
]
