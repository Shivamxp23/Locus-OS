"""
SPEC §20.3 line 6555: "## Feature §20.3: VNC / Remote Desktop Protocol Control"
Unit tests for VNC remote desktop control (F-0052 / US-82).
Asserts RFB protocol client, Bezier curve mouse trajectory generation,
BoundingBox safety gate enforcement, keyboard event injection,
swappable provider interface, and modular off-switches.
"""
from __future__ import annotations

from typing import Any
import pytest

import sidecar.config as config
from sidecar.desktop.vnc_client import (
    BaseRFBProtocolClient,
    BoundingBox,
    MockRFBProtocolClient,
    SecurityException,
    VNCDesktopController,
    char_to_keysym,
    compute_bezier_path,
)
from sidecar.providers.vnc import (
    BaseVNCProvider,
    DefaultVNCProvider,
)


def test_bounding_box_security_containment() -> None:
    """SPEC §20.3 line 6589: Safety boundary check raises SecurityException on out-of-bounds clicks."""
    boundary = BoundingBox(min_x=100, min_y=100, max_x=800, max_y=600)
    assert boundary.contains(500, 400) is True
    assert boundary.contains(100, 100) is True
    assert boundary.contains(800, 600) is True
    assert boundary.contains(50, 400) is False
    assert boundary.contains(500, 50) is False
    assert boundary.contains(900, 400) is False
    assert boundary.contains(500, 700) is False

    rfb = MockRFBProtocolClient()
    controller = VNCDesktopController(rfb_client=rfb, safety_boundary=boundary)

    # Allowed click inside boundary
    res = controller.move_and_click(200, 300, button="left")
    assert res["status"] == "ok"
    assert res["coordinates"] == {"x": 200, "y": 300}

    # Forbidden click outside boundary
    with pytest.raises(SecurityException) as exc_info:
        controller.move_and_click(50, 50)
    assert "outside permitted safe region" in str(exc_info.value)


def test_compute_bezier_path() -> None:
    """SPEC §20.3 line 6593: Smooth Bezier curve movement produces human-like traversal."""
    start = (0, 0)
    end = (100, 200)
    steps = 10
    path = compute_bezier_path(start, end, steps=steps)
    assert len(path) == steps + 1
    assert path[0] == start
    assert path[-1] == end

    # Test with explicit control point
    path_custom = compute_bezier_path(start, end, steps=5, control_offset=(50, 50))
    assert len(path_custom) == 6
    assert path_custom[0] == start
    assert path_custom[-1] == end


def test_char_to_keysym_and_key_injection() -> None:
    """SPEC §20.3 line 6607: Keysym mapping and keyboard event injection."""
    assert char_to_keysym("a") == ord("a")
    assert char_to_keysym("Z") == ord("Z")
    assert char_to_keysym("1") == ord("1")

    rfb = MockRFBProtocolClient()
    controller = VNCDesktopController(rfb_client=rfb)
    res = controller.type_keys("Hello")
    assert res["status"] == "ok"
    assert res["characters_count"] == 5

    # Each char produces a key down and key up event
    assert len(rfb.key_events) == 10
    assert rfb.key_events[0] == (ord("H"), True)
    assert rfb.key_events[1] == (ord("H"), False)


def test_vnc_controller_lifecycle_and_capture() -> None:
    """SPEC §20.3 line 6578-6585: Connection, framebuffer capture, and status reporting."""
    rfb = MockRFBProtocolClient()
    controller = VNCDesktopController(host="10.0.0.1", port=5901, rfb_client=rfb)

    assert controller.connect(password="secret") is True
    assert rfb.is_connected is True

    frame = controller.capture_framebuffer()
    assert frame["format"] == "png"
    assert "data" in frame
    assert frame["width"] == 1920
    assert frame["height"] == 1080

    status = controller.get_status()
    assert status["host"] == "10.0.0.1"
    assert status["port"] == 5901
    assert status["connected"] is True
    assert status["safety_boundary"]["max_x"] == 1920

    controller.disconnect()
    assert rfb.is_connected is False


def test_swappable_vnc_provider() -> None:
    """Verify BaseVNCProvider interface and DefaultVNCProvider swappability."""
    class CustomVNCProvider(BaseVNCProvider):
        @property
        def name(self) -> str:
            return "custom_vnc"

        def is_feature_enabled(self) -> tuple[bool, str]:
            return True, ""

        def connect(self, host: str = "127.0.0.1", port: int = 5900, password: str = "") -> dict[str, Any]:
            return {"status": "ok", "custom": True}

        def disconnect(self) -> dict[str, Any]:
            return {"status": "ok", "disconnected": True}

        def capture_framebuffer(self) -> dict[str, Any]:
            return {"format": "mock"}

        def click(self, x: int, y: int, button: str = "left", steps: int = 5) -> dict[str, Any]:
            return {"action": "click", "custom": True}

        def type_keys(self, text: str) -> dict[str, Any]:
            return {"action": "type", "custom": True}

        def get_status(self) -> dict[str, Any]:
            return {"custom_active": True}

    custom = CustomVNCProvider()
    assert custom.name == "custom_vnc"
    assert custom.connect()["custom"] is True

    default_prov = DefaultVNCProvider()
    assert default_prov.name == "default_vnc_provider"
    assert default_prov.connect()["connected"] is True


def test_vnc_provider_security_and_off_switch(monkeypatch: pytest.MonkeyPatch) -> None:
    """SPEC §20.3 line 6617: Modular off-switches locus.vnc.enabled and locus.tools.vnc.enabled return 503."""
    boundary = BoundingBox(min_x=0, min_y=0, max_x=100, max_y=100)
    controller = VNCDesktopController(safety_boundary=boundary)
    provider = DefaultVNCProvider(controller=controller)

    # Security exception handled cleanly with status_code 403
    res_err = provider.click(500, 500)
    assert res_err["status_code"] == 403
    assert res_err["error"] == "security_violation"

    # Enabled when config has no setting
    enabled, switch = provider.is_feature_enabled()
    assert enabled is True

    # Disable via locus.vnc.enabled
    monkeypatch.setattr(config, "get", lambda key, default=None: False if key == "locus.vnc.enabled" else None)
    monkeypatch.setattr(config, "is_enabled", lambda key, default=False: False if key == "locus.vnc.enabled" else True)

    enabled, switch = provider.is_feature_enabled()
    assert enabled is False
    assert switch == "locus.vnc.enabled"

    res_click = provider.click(50, 50)
    assert res_click["status_code"] == 503
    assert res_click["disabled"] == "locus.vnc.enabled"

    res_type = provider.type_keys("test")
    assert res_type["status_code"] == 503

    res_cap = provider.capture_framebuffer()
    assert res_cap["status_code"] == 503

    # Disable via locus.tools.vnc.enabled
    monkeypatch.setattr(config, "get", lambda key, default=None: False if key == "locus.tools.vnc.enabled" else None)
    monkeypatch.setattr(config, "is_enabled", lambda key, default=False: False if key == "locus.tools.vnc.enabled" else True)

    enabled2, switch2 = provider.is_feature_enabled()
    assert enabled2 is False
    assert switch2 == "locus.tools.vnc.enabled"
