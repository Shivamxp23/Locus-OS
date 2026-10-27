"""Screen capture provider implementation for Desktop Computer Use (§16.1-16.2 + §20.1-20.3).

Provides screen capture interfaces and implementations supporting full display,
window capture, and region capture with deterministic mock capabilities.
"""

from __future__ import annotations

import base64
import io
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple


@dataclass
class ScreenCaptureResult:
    """Result of a screen capture operation."""
    image_base64: str
    width: int
    height: int
    format: str = "png"
    display_id: int = 0
    window_title: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "image_base64": self.image_base64,
            "width": self.width,
            "height": self.height,
            "format": self.format,
            "display_id": self.display_id,
            "window_title": self.window_title,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


class BaseScreenCaptureProvider(ABC):
    """Abstract interface for screen capture backends."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Whether this capture provider is available in current environment."""
        pass

    @abstractmethod
    def capture_display(self, display_id: int = 0) -> ScreenCaptureResult:
        """Capture full screen of specified display."""
        pass

    @abstractmethod
    def capture_region(self, x: int, y: int, width: int, height: int) -> ScreenCaptureResult:
        """Capture a rectangular bounding box on screen."""
        pass

    @abstractmethod
    def capture_window(self, window_title: str) -> ScreenCaptureResult:
        """Capture content of a specific application window."""
        pass


class DesktopScreenCaptureProvider(BaseScreenCaptureProvider):
    """Native OS desktop screen capture provider using PIL.ImageGrab or mss."""

    def __init__(self) -> None:
        self._available = False
        try:
            from PIL import ImageGrab  # type: ignore
            self._available = True
        except ImportError:
            self._available = False

    @property
    def name(self) -> str:
        return "desktop_native"

    @property
    def is_available(self) -> bool:
        return self._available

    def capture_display(self, display_id: int = 0) -> ScreenCaptureResult:
        """SPEC §16.1 line 6535: "native.capture_screen()" """
        if not self._available:
            return MockScreenCaptureProvider().capture_display(display_id)

        try:
            from PIL import ImageGrab  # type: ignore
            img = ImageGrab.grab()
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")
            return ScreenCaptureResult(
                image_base64=b64,
                width=img.width,
                height=img.height,
                display_id=display_id,
                metadata={"backend": "PIL.ImageGrab"},
            )
        except Exception:
            return MockScreenCaptureProvider().capture_display(display_id)

    def capture_region(self, x: int, y: int, width: int, height: int) -> ScreenCaptureResult:
        if not self._available:
            return MockScreenCaptureProvider().capture_region(x, y, width, height)

        try:
            from PIL import ImageGrab  # type: ignore
            bbox = (x, y, x + width, y + height)
            img = ImageGrab.grab(bbox=bbox)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")
            return ScreenCaptureResult(
                image_base64=b64,
                width=img.width,
                height=img.height,
                metadata={"backend": "PIL.ImageGrab", "bbox": bbox},
            )
        except Exception:
            return MockScreenCaptureProvider().capture_region(x, y, width, height)

    def capture_window(self, window_title: str) -> ScreenCaptureResult:
        """SPEC §16.1 line 6537: "focus_window(action.window_title)" """
        # Fallback to full screen if window capture is unsupported on platform
        res = self.capture_display()
        res.window_title = window_title
        res.metadata["window_title"] = window_title
        return res


class MockScreenCaptureProvider(BaseScreenCaptureProvider):
    """Deterministic synthetic screen capture provider for headless/testing environments."""

    def __init__(self, default_width: int = 1920, default_height: int = 1080) -> None:
        self.default_width = default_width
        self.default_height = default_height
        # A minimal 1x1 transparent/solid PNG encoded in base64
        self._sample_png_b64 = (
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
            "+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )

    @property
    def name(self) -> str:
        return "mock"

    @property
    def is_available(self) -> bool:
        return True

    def capture_display(self, display_id: int = 0) -> ScreenCaptureResult:
        """SPEC §16.1 line 6535: "native.capture_screen()" """
        return ScreenCaptureResult(
            image_base64=self._sample_png_b64,
            width=self.default_width,
            height=self.default_height,
            display_id=display_id,
            metadata={"mock": True, "display_id": display_id},
        )

    def capture_region(self, x: int, y: int, width: int, height: int) -> ScreenCaptureResult:
        return ScreenCaptureResult(
            image_base64=self._sample_png_b64,
            width=width,
            height=height,
            metadata={"mock": True, "region": (x, y, width, height)},
        )

    def capture_window(self, window_title: str) -> ScreenCaptureResult:
        return ScreenCaptureResult(
            image_base64=self._sample_png_b64,
            width=self.default_width,
            height=self.default_height,
            window_title=window_title,
            metadata={"mock": True, "window_title": window_title},
        )
