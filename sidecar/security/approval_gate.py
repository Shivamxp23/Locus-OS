"""Approval Gate & User Confirmation Engine (§13.5).

Implements 10-minute TTL approval gate for mutating tools in SUPERVISED autonomy mode.
Supports Telegram inline confirmation hooks and automated expiration.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional


DEFAULT_APPROVAL_TTL_SECONDS: float = 600.0  # 10 minutes


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class ApprovalRequest:
    task_id: str
    tool_name: str
    params: Dict[str, Any] = field(default_factory=dict)
    status: str = ApprovalStatus.PENDING.value
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0.0

    def __post_init__(self) -> None:
        if self.expires_at == 0.0:
            self.expires_at = self.created_at + DEFAULT_APPROVAL_TTL_SECONDS

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ApprovalGate:
    """In-memory and event-driven store for pending tool approval requests."""

    def __init__(self, default_ttl: float = DEFAULT_APPROVAL_TTL_SECONDS) -> None:
        self.default_ttl = default_ttl
        self.requests: Dict[str, ApprovalRequest] = {}

    def queue_approval(
        self,
        tool_name: str,
        params: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
        ttl: Optional[float] = None,
    ) -> ApprovalRequest:
        tid = task_id or ("appr_" + str(uuid.uuid4())[:8])
        now = time.time()
        timeout = ttl or self.default_ttl
        req = ApprovalRequest(
            task_id=tid,
            tool_name=tool_name,
            params=params or {},
            created_at=now,
            expires_at=now + timeout,
        )
        self.requests[tid] = req
        return req

    def get_status(self, task_id: str) -> str:
        req = self.requests.get(task_id)
        if not req:
            return "not_found"
        if req.status == ApprovalStatus.PENDING.value and req.is_expired:
            req.status = ApprovalStatus.EXPIRED.value
        return req.status

    def approve(self, task_id: str) -> bool:
        req = self.requests.get(task_id)
        if not req:
            return False
        if req.is_expired:
            req.status = ApprovalStatus.EXPIRED.value
            return False
        if req.status == ApprovalStatus.PENDING.value:
            req.status = ApprovalStatus.APPROVED.value
            return True
        return False

    def reject(self, task_id: str) -> bool:
        req = self.requests.get(task_id)
        if not req:
            return False
        if req.status == ApprovalStatus.PENDING.value:
            req.status = ApprovalStatus.REJECTED.value
            return True
        return False

    def list_pending(self) -> List[ApprovalRequest]:
        now = time.time()
        pending = []
        for req in self.requests.values():
            if req.status == ApprovalStatus.PENDING.value:
                if req.expires_at <= now:
                    req.status = ApprovalStatus.EXPIRED.value
                else:
                    pending.append(req)
        return pending
