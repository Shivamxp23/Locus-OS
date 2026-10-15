"""Locus Agent Communication Protocol (ACP) Transport (§9.4).

Implements the JSON-RPC based ACP server and client framing for standard agent-to-agent
and IDE-to-agent inter-process communication.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class ACPMessageType(str, Enum):
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ERROR = "error"


@dataclass
class ACPMessage:
    jsonrpc: str = "2.0"
    method: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    id: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None

    def serialize(self) -> str:
        data: Dict[str, Any] = {"jsonrpc": self.jsonrpc}
        if self.id is not None:
            data["id"] = self.id
        if self.method is not None:
            data["method"] = self.method
        if self.params is not None:
            data["params"] = self.params
        if self.result is not None:
            data["result"] = self.result
        if self.error is not None:
            data["error"] = self.error
        return json.dumps(data)

    @classmethod
    def deserialize(cls, payload_str: str) -> ACPMessage:
        obj = json.loads(payload_str)
        return cls(
            jsonrpc=obj.get("jsonrpc", "2.0"),
            method=obj.get("method"),
            params=obj.get("params"),
            id=obj.get("id"),
            result=obj.get("result"),
            error=obj.get("error"),
        )


class ACPServerTransport:
    """Handles ACP RPC method registrations and message dispatching."""

    def __init__(self, agent_name: str = "locus-agent"):
        self.agent_name = agent_name
        self.methods: Dict[str, Callable[[Dict[str, Any]], Any]] = {}
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        self.register_method("initialize", self._handle_initialize)
        self.register_method("session/create", self._handle_session_create)
        self.register_method("session/prompt", self._handle_session_prompt)
        self.register_method("session/cancel", self._handle_session_cancel)

    def register_method(self, method_name: str, handler: Callable[[Dict[str, Any]], Any]) -> None:
        self.methods[method_name] = handler

    def handle_raw_message(self, raw_str: str) -> str:
        try:
            req = ACPMessage.deserialize(raw_str)
        except Exception as e:
            err_msg = ACPMessage(
                id=None,
                error={"code": -32700, "message": f"Parse error: {str(e)}"},
            )
            return err_msg.serialize()

        if not req.method or req.method not in self.methods:
            resp = ACPMessage(
                id=req.id,
                error={"code": -32601, "message": f"Method '{req.method}' not found"},
            )
            return resp.serialize()

        try:
            res = self.methods[req.method](req.params or {})
            resp = ACPMessage(id=req.id, result=res)
            return resp.serialize()
        except Exception as e:
            resp = ACPMessage(
                id=req.id,
                error={"code": -32603, "message": f"Internal error: {str(e)}"},
            )
            return resp.serialize()

    def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "protocolVersion": "1.0",
            "serverInfo": {"name": self.agent_name, "version": "1.0.0"},
            "capabilities": {"sessions": True, "streaming": True, "tools": True},
        }

    def _handle_session_create(self, params: Dict[str, Any]) -> Dict[str, Any]:
        sess_id = f"acp_sess_{int(time.time() * 1000)}"
        self.active_sessions[sess_id] = {"created_at": time.time(), "params": params}
        return {"sessionId": sess_id}

    def _handle_session_prompt(self, params: Dict[str, Any]) -> Dict[str, Any]:
        prompt = params.get("prompt", "")
        return {"reply": f"ACP Agent received: {prompt}", "status": "completed"}

    def _handle_session_cancel(self, params: Dict[str, Any]) -> Dict[str, Any]:
        sess_id = params.get("sessionId", "")
        if sess_id in self.active_sessions:
            del self.active_sessions[sess_id]
        return {"cancelled": True}
