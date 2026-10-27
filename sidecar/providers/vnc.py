"""
SPEC §20.3 lines 6555-6621: VNC Remote Desktop Control Provider.
Provides BaseVNCProvider and DefaultVNCProvider with modular off-switches:
- locus.vnc.enabled
- locus.tools.vnc.enabled
Returning HTTP 503 when disabled.
"""
from __future__ import annotations

import abc
import logging
from typing import Any

import sidecar.config as config
from sidecar.desktop.vnc_client import (
    BaseRFBProtocolClient,
    BoundingBox,
    MockRFBProtocolClient,
    SecurityException,
    VNCDesktopController,
)

logger = logging.getLogger("locus.providers.vnc")


class BaseVNCProvider(abc.ABC):
    """Abstract base provider for VNC and remote desktop protocol control."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Provider name."""
        raise NotImplementedError

    @abc.abstractmethod
    def is_feature_enabled(self) -> tuple[bool, str]:
        """Check if VNC remote control is enabled via config."""
        raise NotImplementedError

    @abc.abstractmethod
    def connect(self, host: str = "127.0.0.1", port: int = 5900, password: str = "") -> dict[str, Any]:
        """Establish connection to remote VNC display."""
        raise NotImplementedError

    @abc.abstractmethod
    def disconnect(self) -> dict[str, Any]:
        """Disconnect from remote VNC display."""
        raise NotImplementedError

    @abc.abstractmethod
    def capture_framebuffer(self) -> dict[str, Any]:
        """Capture current display framebuffer."""
        raise NotImplementedError

    @abc.abstractmethod
    def click(self, x: int, y: int, button: str = "left", steps: int = 5) -> dict[str, Any]:
        """Perform mouse move and click within safe boundary."""
        raise NotImplementedError

    @abc.abstractmethod
    def type_keys(self, text: str) -> dict[str, Any]:
        """Inject keystrokes into remote desktop."""
        raise NotImplementedError

    @abc.abstractmethod
    def get_status(self) -> dict[str, Any]:
        """Return diagnostic status of VNC controller."""
        raise NotImplementedError


class DefaultVNCProvider(BaseVNCProvider):
    """
    Default VNC desktop control provider wrapping VNCDesktopController.
    Enforces modular off-switches locus.vnc.enabled and locus.tools.vnc.enabled (HTTP 503),
    and BoundingBox safety gate containment.
    """

    def __init__(self, controller: VNCDesktopController | None = None) -> None:
        self.controller = controller or VNCDesktopController()

    @property
    def name(self) -> str:
        return "default_vnc_provider"

    def is_feature_enabled(self) -> tuple[bool, str]:
        """Evaluate modular off-switches."""
        for switch in ("locus.vnc.enabled", "locus.tools.vnc.enabled"):
            val = config.get(switch)
            if val is not None and not config.is_enabled(switch):
                return False, switch
        return True, ""

    def connect(self, host: str = "127.0.0.1", port: int = 5900, password: str = "") -> dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {"error": "feature_disabled", "disabled": switch, "status_code": 503}
        self.controller.host = host
        self.controller.port = port
        ok = self.controller.connect(password=password)
        return {"status": "ok" if ok else "failed", "connected": ok, "host": host, "port": port}

    def disconnect(self) -> dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {"error": "feature_disabled", "disabled": switch, "status_code": 503}
        self.controller.disconnect()
        return {"status": "ok", "connected": False}

    def capture_framebuffer(self) -> dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {"error": "feature_disabled", "disabled": switch, "status_code": 503}
        return self.controller.capture_framebuffer()

    def click(self, x: int, y: int, button: str = "left", steps: int = 5) -> dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {"error": "feature_disabled", "disabled": switch, "status_code": 503}
        try:
            return self.controller.move_and_click(x=x, y=y, button=button, steps=steps)
        except SecurityException as e:
            return {"error": "security_violation", "message": str(e), "status_code": 403}

    def type_keys(self, text: str) -> dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {"error": "feature_disabled", "disabled": switch, "status_code": 503}
        return self.controller.type_keys(text=text)

    def get_status(self) -> dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {"error": "feature_disabled", "disabled": switch, "status_code": 503}
        return self.controller.get_status()
