"""
SPEC §16.1-16.2 + §20.1-20.3 lines 6496-6554:
Unit tests for Browser Automation & Desktop Control (F-0045 / US-78).
"""
from __future__ import annotations

import pytest

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
from sidecar.providers.browser import (
    BaseBrowserProvider,
    DefaultBrowserProvider,
)
import sidecar.config as config


def test_playwright_browser_provider():
    """SPEC §16.1 line 6499: "Default: Playwright browser = browser_provider.launch() page = browser.new_page()" """
    provider = PlaywrightBrowserProvider()
    assert provider.name == "playwright"
    assert provider.is_available() is True

    res = provider.navigate("https://example.com")
    assert res.url == "https://example.com"
    assert "example.com" in res.title
    assert len(res.elements) > 0

    click_res = provider.click(selector="#btn-submit")
    assert len(click_res.logs) > 0

    type_res = provider.type_text("Hello Browser", selector="#search-input")
    assert len(type_res.logs) > 0

    shot = provider.screenshot()
    assert len(shot) > 0


def test_browserbase_and_mock_providers():
    """SPEC §16.1 line 6549: "Optional: OpenHuman screen_intelligence, Browserbase." """
    bb = BrowserbaseProvider()
    assert bb.name == "browserbase"
    bb_res = bb.navigate("https://locus.dev")
    assert bb_res.url == "https://locus.dev"

    mock = MockBrowserProvider()
    assert mock.name == "mock"
    assert mock.is_available() is True
    mock_res = mock.navigate("https://mock.test")
    assert mock_res.url == "https://mock.test"
    assert len(mock.history) == 1
    mock.click(x=10, y=20)
    assert len(mock.actions_log) == 1
    mock.type_text("test input")
    assert len(mock.actions_log) == 2


def test_screen_intelligence_element_analysis():
    """SPEC §16.1 line 6516: "SCREEN INTELLIGENCE: FUNCTION analyze_screen(screenshot): Return coordinates and descriptions." """
    intel = ScreenIntelligence()
    assert intel.analyze_screen(b"") == []

    dummy_screenshot = b"\x89PNG\r\n\x1a\nfake_image"
    elements = intel.analyze_screen(dummy_screenshot)
    assert len(elements) >= 3

    # Element hit testing
    found = intel.extract_element_at(elements, x=160, y=70)
    assert found is not None
    assert found.id == "el_search"

    not_found = intel.extract_element_at(elements, x=999, y=999)
    assert not_found is None


def test_browser_automation_manager_task_execution():
    """SPEC §16.1 line 6499: "BROWSER AUTOMATION: FUNCTION automate_browser(task): ... RETURN page.content()" """
    mgr = BrowserAutomationManager(default_engine="mock")
    task = BrowserTask(
        url="https://locus.dev",
        actions=[
            {"type": "click", "selector": "#btn-action"},
            {"type": "type", "selector": "#input-search", "text": "research query"},
        ],
        capture_screenshot=True,
    )
    res = mgr.automate_task(task)
    assert res.url == "https://locus.dev"
    assert res.screenshot_base64 is not None
    assert len(res.elements) > 0
    assert len(res.logs) >= 3


def test_browser_provider_modular_off_switches():
    """SPEC §16.1 line 6549: "Modular off-switch returns HTTP 503 when feature is disabled." """
    mgr = BrowserAutomationManager(default_engine="mock")
    provider = DefaultBrowserProvider(manager=mgr)

    assert provider.is_available() is True

    # Disable via primary off-switch
    config.set("locus.browser.enabled", False)
    try:
        assert provider.is_available() is False
        with pytest.raises(RuntimeError, match="disabled by modular off-switch"):
            provider.navigate("https://example.com")
        with pytest.raises(RuntimeError, match="disabled by modular off-switch"):
            provider.screenshot()
        with pytest.raises(RuntimeError, match="disabled by modular off-switch"):
            provider.automate_task(BrowserTask(url="https://example.com"))
    finally:
        config.set("locus.browser.enabled", True)

    # Disable via secondary off-switch
    config.set("locus.browser_automation.enabled", False)
    try:
        assert provider.is_available() is False
        with pytest.raises(RuntimeError, match="disabled by modular off-switch"):
            provider.navigate("https://example.com")
    finally:
        config.set("locus.browser_automation.enabled", True)

    assert provider.is_available() is True


def test_swappable_browser_engine():
    """SPEC §16.1 line 6549: "Provider Interface: BrowserProvider swappable engine." """
    mgr = BrowserAutomationManager()
    provider = DefaultBrowserProvider(manager=mgr)

    provider.set_engine(MockBrowserProvider())
    assert provider.manager.active_engine.name == "mock"

    res = provider.navigate("https://swapped.org")
    assert res.url == "https://swapped.org"
