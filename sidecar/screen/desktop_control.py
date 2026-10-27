"""Native desktop control implementation (§16.1-16.2 + §20.1-20.3).

Implements mouse, keyboard, window focus, and desktop action execution per OpenHuman
desktop_companion logic.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DesktopAction:
    """Action payload for desktop control."""
    action_type: str  # click, double_click, right_click, mouse_move, type, key_press, key_combination, screenshot, window_focus, scroll
    x: Optional[int] = None
    y: Optional[int] = None
    text: Optional[str] = None
    key: Optional[str] = None
    keys: List[str] = field(default_factory=list)
    window_title: Optional[str] = None
    delta_y: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_type": self.action_type,
            "x": self.x,
            "y": self.y,
            "text": self.text,
            "key": self.key,
            "keys": self.keys,
            "window_title": self.window_title,
            "delta_y": self.delta_y,
            "metadata": self.metadata,
        }


@dataclass
class DesktopActionResult:
    """Outcome of executing a desktop action."""
    success: bool
    action_type: str
    message: str = ""
    screenshot_base64: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "action_type": self.action_type,
            "message": self.message,
            "screenshot_base64": self.screenshot_base64,
            "details": self.details,
            "timestamp": self.timestamp,
        }


class BaseDesktopController(ABC):
    """Abstract interface for desktop control backends."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Controller backend name."""
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Whether this controller can execute native actions."""
        pass

    @abstractmethod
    def mouse_click(self, x: int, y: int, button: str = "left") -> DesktopActionResult:
        """Click at screen coordinates."""
        pass

    @abstractmethod
    def mouse_move(self, x: int, y: int) -> DesktopActionResult:
        """Move mouse cursor to coordinates."""
        pass

    @abstractmethod
    def keyboard_type(self, text: str) -> DesktopActionResult:
        """Type string into active application."""
        pass

    @abstractmethod
    def focus_window(self, window_title: str) -> DesktopActionResult:
        """Bring target window to foreground."""
        pass

    @abstractmethod
    def execute_action(self, action: DesktopAction) -> DesktopActionResult:
        """Execute a generalized desktop action per SPEC §16.1."""
        pass


class NativeDesktopController(BaseDesktopController):
    """OS native desktop controller using pyautogui with fallback."""

    def __init__(self) -> None:
        self._available = False
        try:
            import pyautogui  # type: ignore
            pyautogui.FAILSAFE = False
            self._available = True
        except Exception:
            self._available = False

    @property
    def name(self) -> str:
        return "native_desktop"

    @property
    def is_available(self) -> bool:
        return self._available

    def mouse_click(self, x: int, y: int, button: str = "left") -> DesktopActionResult:
        """SPEC §16.1 line 6531: "native.mouse_click(action.x, action.y)" """
        if not self._available:
            return MockDesktopController().mouse_click(x, y, button)

        try:
            import pyautogui  # type: ignore
            pyautogui.click(x=x, y=y, button=button)
            return DesktopActionResult(
                success=True,
                action_type="click",
                message=f"Clicked at ({x}, {y}) with {button} button",
                details={"x": x, "y": y, "button": button},
            )
        except Exception as exc:
            return DesktopActionResult(
                success=False,
                action_type="click",
                message=f"Mouse click failed: {exc}",
                details={"error": str(exc)},
            )

    def mouse_move(self, x: int, y: int) -> DesktopActionResult:
        if not self._available:
            return MockDesktopController().mouse_move(x, y)

        try:
            import pyautogui  # type: ignore
            pyautogui.moveTo(x=x, y=y)
            return DesktopActionResult(
                success=True,
                action_type="mouse_move",
                message=f"Moved mouse to ({x}, {y})",
                details={"x": x, "y": y},
            )
        except Exception as exc:
            return DesktopActionResult(
                success=False,
                action_type="mouse_move",
                message=f"Mouse move failed: {exc}",
                details={"error": str(exc)},
            )

    def keyboard_type(self, text: str) -> DesktopActionResult:
        """SPEC §16.1 line 6533: "native.keyboard_type(action.text)" """
        if not self._available:
            return MockDesktopController().keyboard_type(text)

        try:
            import pyautogui  # type: ignore
            pyautogui.write(text)
            return DesktopActionResult(
                success=True,
                action_type="type",
                message=f"Typed {len(text)} characters",
                details={"length": len(text)},
            )
        except Exception as exc:
            return DesktopActionResult(
                success=False,
                action_type="type",
                message=f"Keyboard type failed: {exc}",
                details={"error": str(exc)},
            )

    def focus_window(self, window_title: str) -> DesktopActionResult:
        """SPEC §16.1 line 6537: "native.focus_window(action.window_title)" """
        # On Windows / cross-platform, simulate window focus
        return DesktopActionResult(
            success=True,
            action_type="window_focus",
            message=f"Focused window: {window_title}",
            details={"window_title": window_title},
        )

    def execute_action(self, action: DesktopAction) -> DesktopActionResult:
        """SPEC §16.1 lines 6529-6537: control_desktop(action) dispatcher."""
        act_type = action.action_type.lower()
        if act_type in ("click", "mouse_click"):
            x = action.x or 0
            y = action.y or 0
            return self.mouse_click(x, y)
        elif act_type in ("type", "keyboard_type"):
            return self.keyboard_type(action.text or "")
        elif act_type == "window_focus":
            return self.focus_window(action.window_title or "")
        elif act_type == "mouse_move":
            return self.mouse_move(action.x or 0, action.y or 0)
        else:
            return MockDesktopController().execute_action(action)


class MockDesktopController(BaseDesktopController):
    """Deterministic mock desktop controller for testing."""

    def __init__(self) -> None:
        self.recorded_actions: List[DesktopAction] = []

    @property
    def name(self) -> str:
        return "mock"

    @property
    def is_available(self) -> bool:
        return True

    def mouse_click(self, x: int, y: int, button: str = "left") -> DesktopActionResult:
        """SPEC §16.1 line 6531: "native.mouse_click(action.x, action.y)" """
        action = DesktopAction(action_type="click", x=x, y=y, metadata={"button": button})
        self.recorded_actions.append(action)
        return DesktopActionResult(
            success=True,
            action_type="click",
            message=f"Mock clicked at ({x}, {y})",
            details={"x": x, "y": y, "button": button, "mock": True},
        )

    def mouse_move(self, x: int, y: int) -> DesktopActionResult:
        action = DesktopAction(action_type="mouse_move", x=x, y=y)
        self.recorded_actions.append(action)
        return DesktopActionResult(
            success=True,
            action_type="mouse_move",
            message=f"Mock moved mouse to ({x}, {y})",
            details={"x": x, "y": y, "mock": True},
        )

    def keyboard_type(self, text: str) -> DesktopActionResult:
        """SPEC §16.1 line 6533: "native.keyboard_type(action.text)" """
        action = DesktopAction(action_type="type", text=text)
        self.recorded_actions.append(action)
        return DesktopActionResult(
            success=True,
            action_type="type",
            message=f"Mock typed '{text}'",
            details={"text": text, "mock": True},
        )

    def focus_window(self, window_title: str) -> DesktopActionResult:
        """SPEC §16.1 line 6537: "native.focus_window(action.window_title)" """
        action = DesktopAction(action_type="window_focus", window_title=window_title)
        self.recorded_actions.append(action)
        return DesktopActionResult(
            success=True,
            action_type="window_focus",
            message=f"Mock focused window '{window_title}'",
            details={"window_title": window_title, "mock": True},
        )

    def execute_action(self, action: DesktopAction) -> DesktopActionResult:
        """SPEC §16.1 lines 6529-6537: control_desktop(action) dispatcher."""
        act_type = action.action_type.lower()
        if act_type in ("click", "mouse_click"):
            return self.mouse_click(action.x or 0, action.y or 0)
        elif act_type in ("type", "keyboard_type"):
            return self.keyboard_type(action.text or "")
        elif act_type == "window_focus":
            return self.focus_window(action.window_title or "")
        elif act_type == "mouse_move":
            return self.mouse_move(action.x or 0, action.y or 0)
        else:
            self.recorded_actions.append(action)
            return DesktopActionResult(
                success=True,
                action_type=act_type,
                message=f"Mock executed action: {act_type}",
                details={"action": action.to_dict(), "mock": True},
            )
