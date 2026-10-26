"""
SPEC §16.1-16.2 + §20.1-20.3:
Browser Automation Manager (F-0045 / US-78).

Orchestrates multi-provider browser execution, screen intelligence inspection,
and complex multi-step automated browser tasks.
"""
from __future__ import annotations

import base64
import logging
from typing import Any, Dict, List, Optional

from sidecar.browser.automation import (
    BaseBrowserEngine,
    BrowserbaseProvider,
    BrowserResult,
    BrowserTask,
    MockBrowserProvider,
    PlaywrightBrowserProvider,
    UIElement,
)
from sidecar.browser.screen_intelligence import ScreenIntelligence

logger = logging.getLogger(__name__)


class BrowserAutomationManager:
    """
    Coordinates browser engine sessions and screen intelligence capabilities.
    Default provider: Playwright.
    """

    def __init__(
        self,
        default_engine: Optional[BaseBrowserEngine | str] = None,
        screen_intel: Optional[ScreenIntelligence] = None,
    ) -> None:
        self._engines: Dict[str, BaseBrowserEngine] = {
            "playwright": PlaywrightBrowserProvider(),
            "browserbase": BrowserbaseProvider(),
            "mock": MockBrowserProvider(),
        }
        self.screen_intelligence = screen_intel or ScreenIntelligence()

        if default_engine:
            self.set_engine(default_engine)
        else:
            self._active_engine = self._engines["playwright"]

    @property
    def active_engine(self) -> BaseBrowserEngine:
        return self._active_engine

    def set_engine(self, engine: BaseBrowserEngine | str) -> None:
        if isinstance(engine, str):
            if engine not in self._engines:
                raise ValueError(f"Unknown browser engine: {engine}")
            self._active_engine = self._engines[engine]
        else:
            self._active_engine = engine
            self._engines[engine.name] = engine

    def register_engine(self, name: str, engine: BaseBrowserEngine) -> None:
        self._engines[name] = engine

    def list_engines(self) -> List[str]:
        return list(self._engines.keys())

    def navigate(self, url: str) -> BrowserResult:
        return self._active_engine.navigate(url)

    def click(
        self,
        selector: Optional[str] = None,
        x: Optional[int] = None,
        y: Optional[int] = None,
    ) -> BrowserResult:
        return self._active_engine.click(selector=selector, x=x, y=y)

    def type_text(self, text: str, selector: Optional[str] = None) -> BrowserResult:
        return self._active_engine.type_text(text, selector=selector)

    def screenshot(self) -> bytes:
        return self._active_engine.screenshot()

    def content(self) -> str:
        return self._active_engine.content()

    def close(self) -> None:
        self._active_engine.close()

    def analyze_screen(self, screenshot_bytes: Optional[bytes] = None) -> List[UIElement]:
        bytes_to_analyze = screenshot_bytes or self.screenshot()
        return self.screen_intelligence.analyze_screen(bytes_to_analyze)

    def automate_task(self, task: BrowserTask) -> BrowserResult:
        """
        SPEC §16.1:
        FUNCTION automate_browser(task):
            browser = browser_provider.launch()
            page = browser.new_page()
            page.goto(task.url)
            screenshot = page.screenshot()
            elements = vision_model.identify_elements(screenshot)
            RETURN page.content()
        """
        nav_res = self.navigate(task.url)
        logs = list(nav_res.logs)

        # Execute custom step actions if present
        for action in task.actions:
            act_type = action.get("type", "").lower()
            if act_type == "click":
                c_res = self.click(
                    selector=action.get("selector"),
                    x=action.get("x"),
                    y=action.get("y"),
                )
                logs.extend(c_res.logs)
            elif act_type == "type":
                t_res = self.type_text(
                    text=action.get("text", ""),
                    selector=action.get("selector"),
                )
                logs.extend(t_res.logs)

        # Screen intelligence analysis
        shot_bytes = self.screenshot() if task.capture_screenshot else b""
        elements = self.analyze_screen(shot_bytes) if task.capture_screenshot else nav_res.elements
        shot_b64 = base64.b64encode(shot_bytes).decode("ascii") if shot_bytes else None

        return BrowserResult(
            url=nav_res.url,
            title=nav_res.title,
            content=self.content(),
            screenshot_base64=shot_b64,
            elements=elements,
            logs=logs,
        )
