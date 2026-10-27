"""Unit tests for Desktop Computer Use & Screen Subsystem (§16.1-16.2 + §20.1-20.3)."""

import pytest
from unittest.mock import patch

from sidecar.screen.capture import (
    DesktopScreenCaptureProvider,
    MockScreenCaptureProvider,
    ScreenCaptureResult,
)
from sidecar.screen.desktop_control import (
    DesktopAction,
    DesktopActionResult,
    MockDesktopController,
    NativeDesktopController,
)
from sidecar.screen.screen_intelligence import (
    ScreenElement,
    ScreenIntelligence,
)
from sidecar.screen.manager import ComputerUseManager
from sidecar.providers.screen import DefaultScreenProvider


def test_screen_capture_providers():
    """SPEC §16.1 line 6535: "RETURN native.capture_screen()" """
    mock_provider = MockScreenCaptureProvider(default_width=1920, default_height=1080)
    assert mock_provider.name == "mock"
    assert mock_provider.is_available is True

    # Capture display
    res_display = mock_provider.capture_display(display_id=0)
    assert isinstance(res_display, ScreenCaptureResult)
    assert res_display.width == 1920
    assert res_display.height == 1080
    assert len(res_display.image_base64) > 0

    # Capture region
    res_region = mock_provider.capture_region(x=10, y=20, width=400, height=300)
    assert res_region.width == 400
    assert res_region.height == 300

    # Capture window
    res_window = mock_provider.capture_window("Editor")
    assert res_window.window_title == "Editor"

    # Native desktop capture provider fallback
    desktop_provider = DesktopScreenCaptureProvider()
    assert desktop_provider.name == "desktop_native"
    res_native = desktop_provider.capture_display()
    assert isinstance(res_native, ScreenCaptureResult)


def test_desktop_controllers():
    """SPEC §16.1 line 6531: "native.mouse_click(action.x, action.y)" """
    mock_ctrl = MockDesktopController()
    assert mock_ctrl.name == "mock"
    assert mock_ctrl.is_available is True

    # Click
    click_res = mock_ctrl.mouse_click(x=150, y=250, button="left")
    assert click_res.success is True
    assert click_res.action_type == "click"
    assert len(mock_ctrl.recorded_actions) == 1

    # Keyboard type
    type_res = mock_ctrl.keyboard_type("Hello Locus")
    assert type_res.success is True
    assert type_res.action_type == "type"
    assert len(mock_ctrl.recorded_actions) == 2

    # Window focus
    focus_res = mock_ctrl.focus_window("Terminal")
    assert focus_res.success is True
    assert focus_res.action_type == "window_focus"

    # Generic execute_action
    action = DesktopAction(action_type="mouse_move", x=50, y=50)
    move_res = mock_ctrl.execute_action(action)
    assert move_res.success is True

    # Native controller fallback
    native_ctrl = NativeDesktopController()
    assert native_ctrl.name == "native_desktop"
    res = native_ctrl.focus_window("Browser")
    assert res.success is True


def test_screen_intelligence_element_analysis():
    """SPEC §16.1 line 6516: "SCREEN INTELLIGENCE (from OpenHuman screen_intelligence/): FUNCTION analyze_screen(screenshot)" """
    intelligence = ScreenIntelligence()
    mock_screenshot = "fake_base64_data"
    elements = intelligence.analyze_screen(mock_screenshot)

    assert len(elements) >= 3
    # Check button element
    btn = intelligence.find_element_by_text(elements, "Search")
    assert btn is not None
    assert btn.element_type == "button"
    assert btn.center == (160, 70)

    # Filter by type
    fields = intelligence.find_elements_by_type(elements, "text_field")
    assert len(fields) >= 1
    assert fields[0].element_id == "elem_input_query"


def test_computer_use_manager_workflow():
    """SPEC §16.1 line 6528: "DESKTOP COMPANION (from OpenHuman desktop_companion/): FUNCTION control_desktop(action)" """
    mock_cap = MockScreenCaptureProvider()
    mock_ctrl = MockDesktopController()
    intel = ScreenIntelligence()
    manager = ComputerUseManager(capture_provider=mock_cap, controller=mock_ctrl, intelligence=intel)

    # Capture screen
    cap = manager.capture_screen()
    assert cap.width == 1920

    # Control desktop screenshot action
    shot_action = DesktopAction(action_type="screenshot")
    shot_res = manager.control_desktop(shot_action)
    assert shot_res.success is True
    assert shot_res.screenshot_base64 is not None

    # Analyze and click element
    elements = manager.analyze_screen()
    click_res = manager.click_element_by_id("elem_btn_search", elements=elements)
    assert click_res.success is True
    assert click_res.action_type == "click"

    # Multi-action workflow
    actions = [
        DesktopAction(action_type="click", x=100, y=200),
        DesktopAction(action_type="type", text="test query"),
    ]
    workflow_results = manager.execute_workflow(actions)
    assert len(workflow_results) == 2
    assert all(r.success for r in workflow_results)


def test_swappable_screen_and_controller_providers():
    """SPEC §16.1 line 6549: "Provider Interface: BrowserProvider Default: Playwright. Optional: OpenHuman screen_intelligence, Browserbase." """
    manager = ComputerUseManager()
    custom_cap = MockScreenCaptureProvider(default_width=1280, default_height=720)
    custom_ctrl = MockDesktopController()

    manager.set_capture_provider(custom_cap)
    manager.set_controller(custom_ctrl)

    cap = manager.capture_screen()
    assert cap.width == 1280
    assert cap.height == 720

    action = DesktopAction(action_type="click", x=50, y=60)
    res = manager.control_desktop(action)
    assert res.success is True
    assert len(custom_ctrl.recorded_actions) == 1


def test_screen_provider_modular_off_switches():
    """SPEC §16.1 line 6549: "Component: locus/providers/browser/ Provider Interface: BrowserProvider" """
    provider = DefaultScreenProvider()
    assert provider.is_available() is True
    status = provider.get_status()
    assert status["available"] is True

    # Test locus.screen.enabled off
    with patch("sidecar.config.get", return_value="false"):
        with patch("sidecar.config.is_enabled", return_value=False):
            assert provider.is_available() is False
            with pytest.raises(RuntimeError, match="disabled by modular off-switch"):
                provider.capture_screen()
            with pytest.raises(RuntimeError, match="disabled by modular off-switch"):
                provider.control_desktop(DesktopAction(action_type="click", x=10, y=20))
            with pytest.raises(RuntimeError, match="disabled by modular off-switch"):
                provider.analyze_screen()
            with pytest.raises(RuntimeError, match="disabled by modular off-switch"):
                provider.execute_workflow([])
