"""
SPEC §16.1-16.2 + §20.1-20.3 lines 6496-6554:
Browser Provider Interface and Implementation (F-0045 / US-78).

Implements BaseBrowserProvider and DefaultBrowserProvider with modular off-switches:
- locus.browser.enabled
- locus.browser_automation.enabled
Returning HTTP 503 when disabled.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from typing import Any, Dict, List, Optional

from sidecar.browser.automation import (
    BaseBrowserEngine,
    BrowserResult,
    BrowserTask,
    UIElement,
)
from sidecar.browser.manager import BrowserAutomationManager
import sidecar.config as config

logger = logging.getLogger(__name__)


class BaseBrowserProvider(ABC):
    """
    SPEC §16.1: Provider Interface: BrowserProvider.
    """

    @abstractmethod
    def is_available(self) -> bool:
        """Check if browser automation subsystem is enabled."""
        raise NotImplementedError

    @abstractmethod
    def navigate(self, url: str) -> BrowserResult:
        """Navigate to URL in active browser engine."""
        raise NotImplementedError

    @abstractmethod
    def click(
        self,
        selector: Optional[str] = None,
        x: Optional[int] = None,
        y: Optional[int] = None,
    ) -> BrowserResult:
        """Simulate click on selector or coordinates."""
        raise NotImplementedError

    @abstractmethod
    def type_text(self, text: str, selector: Optional[str] = None) -> BrowserResult:
        """Type text into specified element or active field."""
        raise NotImplementedError

    @abstractmethod
    def screenshot(self) -> bytes:
        """Capture screenshot from active browser page."""
        raise NotImplementedError

    @abstractmethod
    def content(self) -> str:
        """Retrieve current DOM / page HTML content."""
        raise NotImplementedError

    @abstractmethod
    def analyze_screen(self, screenshot_bytes: Optional[bytes] = None) -> List[UIElement]:
        """Perform screen intelligence analysis on current or supplied screen."""
        raise NotImplementedError

    @abstractmethod
    def automate_task(self, task: BrowserTask) -> BrowserResult:
        """Execute automated browser task flow."""
        raise NotImplementedError

    @abstractmethod
    def list_engines(self) -> List[str]:
        """List registered browser automation engines."""
        raise NotImplementedError

    @abstractmethod
    def set_engine(self, engine: BaseBrowserEngine | str) -> None:
        """Set active browser engine."""
        raise NotImplementedError


class DefaultBrowserProvider(BaseBrowserProvider):
    """
    SPEC §16.1: Default implementation of BrowserProvider.
    Wraps BrowserAutomationManager with modular off-switch enforcement.
    """

    def __init__(self, manager: Optional[BrowserAutomationManager] = None) -> None:
        self.manager = manager or BrowserAutomationManager()

    def is_available(self) -> bool:
        """
        Check modular off-switches:
        - locus.browser.enabled
        - locus.browser_automation.enabled
        """
        v1 = config.get("locus.browser.enabled")
        if v1 is not None and not config.is_enabled("locus.browser.enabled"):
            return False

        v2 = config.get("locus.browser_automation.enabled")
        if v2 is not None and not config.is_enabled("locus.browser_automation.enabled"):
            return False

        return True

    def navigate(self, url: str) -> BrowserResult:
        if not self.is_available():
            raise RuntimeError("Browser automation is disabled by modular off-switch.")
        return self.manager.navigate(url)

    def click(
        self,
        selector: Optional[str] = None,
        x: Optional[int] = None,
        y: Optional[int] = None,
    ) -> BrowserResult:
        if not self.is_available():
            raise RuntimeError("Browser automation is disabled by modular off-switch.")
        return self.manager.click(selector=selector, x=x, y=y)

    def type_text(self, text: str, selector: Optional[str] = None) -> BrowserResult:
        if not self.is_available():
            raise RuntimeError("Browser automation is disabled by modular off-switch.")
        return self.manager.type_text(text, selector=selector)

    def screenshot(self) -> bytes:
        if not self.is_available():
            raise RuntimeError("Browser automation is disabled by modular off-switch.")
        return self.manager.screenshot()

    def content(self) -> str:
        if not self.is_available():
            raise RuntimeError("Browser automation is disabled by modular off-switch.")
        return self.manager.content()

    def analyze_screen(self, screenshot_bytes: Optional[bytes] = None) -> List[UIElement]:
        if not self.is_available():
            raise RuntimeError("Browser automation is disabled by modular off-switch.")
        return self.manager.analyze_screen(screenshot_bytes=screenshot_bytes)

    def automate_task(self, task: BrowserTask) -> BrowserResult:
        if not self.is_available():
            raise RuntimeError("Browser automation is disabled by modular off-switch.")
        return self.manager.automate_task(task)

    def list_engines(self) -> List[str]:
        return self.manager.list_engines()

    def set_engine(self, engine: BaseBrowserEngine | str) -> None:
        self.manager.set_engine(engine)
