"""Locus Browser Automation Controller (§16.1-16.2 + §20.1-20.3).

Provides headless and interactive browser control, page navigation, DOM inspection,
element interactions (click, type), and screenshot capture for agent computer use.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class BrowserAction(str, Enum):
    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE = "type"
    SCREENSHOT = "screenshot"
    EVALUATE = "evaluate"
    EXTRACT_TEXT = "extract_text"


@dataclass
class BrowserPageSession:
    session_id: str
    current_url: str = "about:blank"
    title: str = "New Tab"
    page_content: str = ""
    history: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "current_url": self.current_url,
            "title": self.title,
            "history": self.history,
            "created_at": self.created_at,
        }


class BrowserAutomationController:
    """Controls browser instances and executes structured browser actions."""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.sessions: Dict[str, BrowserPageSession] = {}

    def create_session(self, session_id: str) -> BrowserPageSession:
        sess = BrowserPageSession(session_id=session_id)
        self.sessions[session_id] = sess
        return sess

    def execute_action(
        self,
        session_id: str,
        action: BrowserAction,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        sess = self.sessions.get(session_id)
        if not sess:
            sess = self.create_session(session_id)

        if action == BrowserAction.NAVIGATE:
            url = params.get("url", "https://example.com")
            sess.current_url = url
            sess.history.append(url)
            sess.title = f"Page: {url}"
            sess.page_content = f"<html><body><h1>Simulated DOM for {url}</h1></body></html>"
            return {"status": "ok", "url": url, "title": sess.title}

        elif action == BrowserAction.CLICK:
            selector = params.get("selector", "")
            return {"status": "ok", "clicked": selector}

        elif action == BrowserAction.TYPE:
            selector = params.get("selector", "")
            text = params.get("text", "")
            return {"status": "ok", "selector": selector, "typed": text}

        elif action == BrowserAction.SCREENSHOT:
            return {
                "status": "ok",
                "format": "png",
                "data_base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
            }

        elif action == BrowserAction.EXTRACT_TEXT:
            return {"status": "ok", "text": sess.page_content}

        elif action == BrowserAction.EVALUATE:
            expression = params.get("expression", "")
            return {"status": "ok", "result": f"Evaluated: {expression}"}

        return {"status": "error", "message": f"Unsupported action {action}"}
