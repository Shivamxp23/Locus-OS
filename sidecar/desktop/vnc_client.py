"""
SPEC §20.3 lines 6555-6621: VNC / Remote Desktop Protocol Control.
RFB 3.8 protocol client, Bezier curve mouse trajectory generation,
and BoundingBox safety gate enforcement.
"""
from __future__ import annotations

import abc
import base64
import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("locus.desktop.vnc")

BUTTON_MASKS = {
    "left": 1,
    "middle": 2,
    "right": 4,
    "none": 0,
}


class SecurityException(Exception):
    """Raised when an agent attempts an input action outside permitted safety boundaries."""
    pass


@dataclass
class BoundingBox:
    """Safety boundary coordinates an agent is permitted to touch."""
    min_x: int = 0
    min_y: int = 0
    max_x: int = 1920
    max_y: int = 1080

    def contains(self, x: int, y: int) -> bool:
        """Check if coordinates fall within the permitted rectangular region."""
        return self.min_x <= x <= self.max_x and self.min_y <= y <= self.max_y


def compute_bezier_path(
    start: tuple[int, int],
    end: tuple[int, int],
    steps: int = 10,
    control_offset: tuple[int, int] | None = None,
) -> list[tuple[int, int]]:
    """
    Compute a smooth quadratic Bezier curve trajectory between start and end.
    Produces human-like mouse cursor traversal rather than instantaneous jump.
    """
    x0, y0 = start
    x2, y2 = end
    if control_offset is None:
        # Generate natural arc offset midpoint
        cx = (x0 + x2) // 2 + (y2 - y0) // 8
        cy = (y0 + y2) // 2 + (x2 - x0) // 8
    else:
        cx, cy = control_offset

    points: list[tuple[int, int]] = []
    for i in range(steps + 1):
        t = i / float(steps)
        # B(t) = (1-t)^2 * P0 + 2(1-t)t * P1 + t^2 * P2
        xt = int((1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t ** 2 * x2)
        yt = int((1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t ** 2 * y2)
        points.append((xt, yt))
    return points


def char_to_keysym(ch: str) -> int:
    """Convert a character into an X11 keysym integer."""
    if len(ch) == 1:
        cp = ord(ch)
        # Standard ASCII keysyms match Latin-1 codepoints
        if cp < 256:
            return cp
    return 0xFF20  # Fallback keysym


class BaseRFBProtocolClient(abc.ABC):
    """Abstract interface for RFB protocol communication."""

    @property
    @abc.abstractmethod
    def is_connected(self) -> bool:
        """Connection status."""
        raise NotImplementedError

    @abc.abstractmethod
    def connect(self, host: str, port: int = 5900) -> bool:
        """Establish RFB socket connection."""
        raise NotImplementedError

    @abc.abstractmethod
    def authenticate(self, password: str = "") -> bool:
        """Perform RFB authentication handshake."""
        raise NotImplementedError

    @abc.abstractmethod
    def set_encodings(self, encodings: list[str]) -> None:
        """Negotiate supported frame encodings."""
        raise NotImplementedError

    @abc.abstractmethod
    def request_update(self) -> bytes:
        """Request and return raw framebuffer update bytes."""
        raise NotImplementedError

    @abc.abstractmethod
    def send_pointer_event(self, x: int, y: int, button_mask: int = 0) -> None:
        """Send pointer motion and button state."""
        raise NotImplementedError

    @abc.abstractmethod
    def send_key_event(self, keysym: int, down: bool = True) -> None:
        """Send keystroke event."""
        raise NotImplementedError

    @abc.abstractmethod
    def disconnect(self) -> None:
        """Close RFB connection."""
        raise NotImplementedError


class MockRFBProtocolClient(BaseRFBProtocolClient):
    """Hermetic mock RFB 3.8 client for unit testing and offline environments."""

    def __init__(self) -> None:
        self._connected = False
        self._encodings: list[str] = ["tight", "zrle", "raw"]
        self.pointer_events: list[tuple[int, int, int]] = []
        self.key_events: list[tuple[int, bool]] = []
        self.width = 1920
        self.height = 1080

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self, host: str, port: int = 5900) -> bool:
        self._connected = True
        return True

    def authenticate(self, password: str = "") -> bool:
        return True

    def set_encodings(self, encodings: list[str]) -> None:
        self._encodings = encodings

    def request_update(self) -> bytes:
        # Synthetic PNG/RGB raw framebuffer byte stream (1x1 pixel test image)
        return b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"

    def send_pointer_event(self, x: int, y: int, button_mask: int = 0) -> None:
        self.pointer_events.append((x, y, button_mask))

    def send_key_event(self, keysym: int, down: bool = True) -> None:
        self.key_events.append((keysym, down))

    def disconnect(self) -> None:
        self._connected = False


class VNCDesktopController:
    """
    SPEC §20.3: VNC Desktop Controller.
    Manages remote desktop connection, human-like Bezier cursor traversal,
    keystroke injection, and coordinate bounding-box safety gating.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 5900,
        rfb_client: BaseRFBProtocolClient | None = None,
        safety_boundary: BoundingBox | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.rfb_client = rfb_client or MockRFBProtocolClient()
        self.safety_boundary = safety_boundary or BoundingBox()
        self.current_pos = (0, 0)

    def connect(self, password: str = "") -> bool:
        """Connect to VNC remote server with credentials."""
        ok = self.rfb_client.connect(self.host, self.port)
        if ok:
            self.rfb_client.authenticate(password)
            self.rfb_client.set_encodings(["tight", "zrle", "raw"])
        return ok

    def disconnect(self) -> None:
        """Close connection."""
        self.rfb_client.disconnect()

    def capture_framebuffer(self) -> dict[str, Any]:
        """Capture current remote display framebuffer."""
        raw_bytes = self.rfb_client.request_update()
        b64_img = base64.b64encode(raw_bytes).decode("ascii")
        return {
            "format": "png",
            "data": b64_img,
            "width": getattr(self.rfb_client, "width", 1920),
            "height": getattr(self.rfb_client, "height", 1080),
            "timestamp": time.time(),
        }

    def move_and_click(
        self,
        x: int,
        y: int,
        button: str = "left",
        steps: int = 5,
    ) -> dict[str, Any]:
        """
        Move mouse along Bezier curve and perform click with safety boundary verification.
        """
        # 1. Safety Boundary Check
        if not self.safety_boundary.contains(x, y):
            raise SecurityException(
                f"Click at ({x}, {y}) outside permitted safe region "
                f"[{self.safety_boundary.min_x}, {self.safety_boundary.min_y}, "
                f"{self.safety_boundary.max_x}, {self.safety_boundary.max_y}]."
            )

        # 2. Smooth Bezier Curve Movement
        trajectory = compute_bezier_path(self.current_pos, (x, y), steps=steps)
        for pt in trajectory:
            self.rfb_client.send_pointer_event(pt[0], pt[1], button_mask=0)

        # 3. Button Press & Release
        mask = BUTTON_MASKS.get(button.lower(), 1)
        self.rfb_client.send_pointer_event(x, y, button_mask=mask)
        self.rfb_client.send_pointer_event(x, y, button_mask=0)
        self.current_pos = (x, y)

        return {
            "status": "ok",
            "action": "click",
            "coordinates": {"x": x, "y": y},
            "button": button,
            "trajectory_steps": len(trajectory),
        }

    def type_keys(self, text: str) -> dict[str, Any]:
        """Inject keystrokes into remote VNC desktop."""
        keys_sent = 0
        for ch in text:
            keysym = char_to_keysym(ch)
            self.rfb_client.send_key_event(keysym, down=True)
            self.rfb_client.send_key_event(keysym, down=False)
            keys_sent += 1

        return {
            "status": "ok",
            "action": "type",
            "characters_count": keys_sent,
        }

    def get_status(self) -> dict[str, Any]:
        """Return diagnostic runtime state."""
        return {
            "host": self.host,
            "port": self.port,
            "connected": self.rfb_client.is_connected,
            "current_pos": list(self.current_pos),
            "safety_boundary": {
                "min_x": self.safety_boundary.min_x,
                "min_y": self.safety_boundary.min_y,
                "max_x": self.safety_boundary.max_x,
                "max_y": self.safety_boundary.max_y,
            },
        }
