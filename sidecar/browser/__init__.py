"""
SPEC §16.1-16.2 + §20.1-20.3:
Browser Automation module re-exports (F-0045 / US-78).
"""
from sidecar.browser.automation import (
    BaseBrowserEngine,
    BrowserbaseProvider,
    BrowserResult,
    BrowserTask,
    MockBrowserProvider,
    PlaywrightBrowserProvider,
    UIElement,
)
from sidecar.browser.manager import BrowserAutomationManager
from sidecar.browser.screen_intelligence import ScreenIntelligence

__all__ = [
    "UIElement",
    "BrowserTask",
    "BrowserResult",
    "BaseBrowserEngine",
    "PlaywrightBrowserProvider",
    "BrowserbaseProvider",
    "MockBrowserProvider",
    "ScreenIntelligence",
    "BrowserAutomationManager",
]
