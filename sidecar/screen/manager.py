"""Computer Use and Desktop Screen Manager (§16.1-16.2 + §20.1-20.3).

Orchestrates native desktop capture, screen intelligence element identification,
and desktop input automation into an integrated computer use subsystem.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

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
from sidecar.screen.screen_intelligence import (
    ScreenElement,
    ScreenIntelligence,
)


class ComputerUseManager:
    """High-level manager for screen capture, desktop control, and screen intelligence."""

    def __init__(
        self,
        capture_provider: Optional[BaseScreenCaptureProvider] = None,
        controller: Optional[BaseDesktopController] = None,
        intelligence: Optional[ScreenIntelligence] = None,
    ) -> None:
        self.capture_provider = capture_provider or (
            DesktopScreenCaptureProvider() if DesktopScreenCaptureProvider().is_available else MockScreenCaptureProvider()
        )
        self.controller = controller or (
            NativeDesktopController() if NativeDesktopController().is_available else MockDesktopController()
        )
        self.intelligence = intelligence or ScreenIntelligence()

    def set_capture_provider(self, provider: BaseScreenCaptureProvider) -> None:
        """Swap screen capture backend."""
        self.capture_provider = provider

    def set_controller(self, controller: BaseDesktopController) -> None:
        """Swap desktop controller backend."""
        self.controller = controller

    def capture_screen(
        self,
        display_id: int = 0,
        region: Optional[Tuple[int, int, int, int]] = None,
        window_title: Optional[str] = None,
    ) -> ScreenCaptureResult:
        """SPEC §16.1 line 6535: "RETURN native.capture_screen()" """
        if window_title:
            return self.capture_provider.capture_window(window_title)
        if region:
            x, y, w, h = region
            return self.capture_provider.capture_region(x, y, w, h)
        return self.capture_provider.capture_display(display_id)

    def control_desktop(self, action: DesktopAction) -> DesktopActionResult:
        """SPEC §16.1 lines 6529-6537:
        FUNCTION control_desktop(action):
            IF action.type == "click":
                native.mouse_click(action.x, action.y)
            ELIF action.type == "type":
                native.keyboard_type(action.text)
            ELIF action.type == "screenshot":
                RETURN native.capture_screen()
            ELIF action.type == "window_focus":
                native.focus_window(action.window_title)
        """
        if action.action_type == "screenshot":
            cap = self.capture_screen(window_title=action.window_title)
            return DesktopActionResult(
                success=True,
                action_type="screenshot",
                message="Screen captured successfully",
                screenshot_base64=cap.image_base64,
                details=cap.to_dict(),
            )
        return self.controller.execute_action(action)

    def analyze_screen(
        self,
        screenshot_base64: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> List[ScreenElement]:
        """SPEC §16.1 lines 6516-6526: analyze_screen(screenshot)."""
        if screenshot_base64 is None:
            capture = self.capture_screen()
            screenshot_base64 = capture.image_base64
        return self.intelligence.analyze_screen(screenshot_base64, prompt=prompt)

    def click_element_by_id(
        self,
        element_id: str,
        elements: Optional[List[ScreenElement]] = None,
    ) -> DesktopActionResult:
        """Find an identified element and click at its center coordinates."""
        if elements is None:
            elements = self.analyze_screen()

        target = next((e for e in elements if e.element_id == element_id), None)
        if not target:
            return DesktopActionResult(
                success=False,
                action_type="click",
                message=f"Element '{element_id}' not found in screen analysis",
                details={"element_id": element_id},
            )

        cx, cy = target.center
        action = DesktopAction(
            action_type="click",
            x=cx,
            y=cy,
            metadata={"target_element": target.to_dict()},
        )
        return self.control_desktop(action)

    def execute_workflow(self, actions: List[DesktopAction]) -> List[DesktopActionResult]:
        """Execute a sequence of desktop actions sequentially."""
        results: List[DesktopActionResult] = []
        for action in actions:
            res = self.control_desktop(action)
            results.append(res)
            if not res.success:
                break
        return results
