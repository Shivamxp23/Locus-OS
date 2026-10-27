"""
SPEC §16.1-16.2 + §20.1-20.3 lines 6496-6554:
Screen and Computer Use Provider Interface and Implementation (F-0051 / US-79).

Implements BaseScreenProvider and DefaultScreenProvider with modular off-switches:
- locus.screen.enabled
- locus.computer_use.enabled
- locus.desktop_control.enabled
Returning HTTP 503 when disabled.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

import sidecar.config as config
from sidecar.screen.capture import (
    BaseScreenCaptureProvider,
    ScreenCaptureResult,
)
from sidecar.screen.desktop_control import (
    BaseDesktopController,
    DesktopAction,
    DesktopActionResult,
)
from sidecar.screen.manager import ComputerUseManager
from sidecar.screen.screen_intelligence import (
    ScreenElement,
    ScreenIntelligence,
)

logger = logging.getLogger(__name__)


class BaseScreenProvider(ABC):
    """
    SPEC §16.1: Provider Interface for Desktop Computer Use and Screen Capture.
    """

    @abstractmethod
    def is_available(self) -> bool:
        """Check if screen/computer use subsystem is enabled."""
        raise NotImplementedError

    @abstractmethod
    def capture_screen(
        self,
        display_id: int = 0,
        region: Optional[Tuple[int, int, int, int]] = None,
        window_title: Optional[str] = None,
    ) -> ScreenCaptureResult:
        """Capture screen display, region, or application window."""
        raise NotImplementedError

    @abstractmethod
    def control_desktop(self, action: DesktopAction) -> DesktopActionResult:
        """Perform desktop action (mouse, keyboard, window focus)."""
        raise NotImplementedError

    @abstractmethod
    def analyze_screen(
        self,
        screenshot_base64: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> List[ScreenElement]:
        """Analyze screen capture with screen intelligence."""
        raise NotImplementedError

    @abstractmethod
    def click_element(
        self,
        element_id: str,
        elements: Optional[List[ScreenElement]] = None,
    ) -> DesktopActionResult:
        """Click an identified UI element by id."""
        raise NotImplementedError

    @abstractmethod
    def execute_workflow(self, actions: List[DesktopAction]) -> List[DesktopActionResult]:
        """Execute sequence of desktop actions."""
        raise NotImplementedError

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Get status of computer use subsystem."""
        raise NotImplementedError


class DefaultScreenProvider(BaseScreenProvider):
    """
    SPEC §16.1: Default implementation of ScreenProvider.
    Wraps ComputerUseManager with modular off-switch enforcement.
    """

    def __init__(self, manager: Optional[ComputerUseManager] = None) -> None:
        self.manager = manager or ComputerUseManager()

    def is_available(self) -> bool:
        """
        Check modular off-switches:
        - locus.screen.enabled
        - locus.computer_use.enabled
        - locus.desktop_control.enabled
        """
        v1 = config.get("locus.screen.enabled")
        if v1 is not None and not config.is_enabled("locus.screen.enabled"):
            return False

        v2 = config.get("locus.computer_use.enabled")
        if v2 is not None and not config.is_enabled("locus.computer_use.enabled"):
            return False

        v3 = config.get("locus.desktop_control.enabled")
        if v3 is not None and not config.is_enabled("locus.desktop_control.enabled"):
            return False

        return True

    def capture_screen(
        self,
        display_id: int = 0,
        region: Optional[Tuple[int, int, int, int]] = None,
        window_title: Optional[str] = None,
    ) -> ScreenCaptureResult:
        if not self.is_available():
            raise RuntimeError("Screen / Computer Use is disabled by modular off-switch.")
        return self.manager.capture_screen(display_id=display_id, region=region, window_title=window_title)

    def control_desktop(self, action: DesktopAction) -> DesktopActionResult:
        if not self.is_available():
            raise RuntimeError("Screen / Computer Use is disabled by modular off-switch.")
        return self.manager.control_desktop(action)

    def analyze_screen(
        self,
        screenshot_base64: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> List[ScreenElement]:
        if not self.is_available():
            raise RuntimeError("Screen / Computer Use is disabled by modular off-switch.")
        return self.manager.analyze_screen(screenshot_base64=screenshot_base64, prompt=prompt)

    def click_element(
        self,
        element_id: str,
        elements: Optional[List[ScreenElement]] = None,
    ) -> DesktopActionResult:
        if not self.is_available():
            raise RuntimeError("Screen / Computer Use is disabled by modular off-switch.")
        return self.manager.click_element_by_id(element_id=element_id, elements=elements)

    def execute_workflow(self, actions: List[DesktopAction]) -> List[DesktopActionResult]:
        if not self.is_available():
            raise RuntimeError("Screen / Computer Use is disabled by modular off-switch.")
        return self.manager.execute_workflow(actions)

    def get_status(self) -> Dict[str, Any]:
        return {
            "available": self.is_available(),
            "capture_backend": self.manager.capture_provider.name,
            "controller_backend": self.manager.controller.name,
            "has_vision": self.manager.intelligence is not None,
        }
