"""
SPEC §13.5 lines 3333-3365:
Approval Gate Store and Runtime Lifecycle (F-0109 / US-71).

Implements:
1. queue_approval(task_id, changes, ttl=600):
   Records approval request with pending status and 10-minute default TTL expiration.
2. wait_for_approval(task_id, timeout):
   Polls status until approved (True), rejected (False), or TTL expired (auto-reject = False).
3. Runtime-only memory store without persisting sensitive approval payloads to disk.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import logging
import time
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class ApprovalStatus(str, Enum):
    """
    SPEC §13.5: Approval lifecycle status.
    """
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"

    @classmethod
    def from_str(cls, val: Optional[str]) -> "ApprovalStatus":
        if not val:
            return cls.PENDING
        v = str(val).strip().lower()
        if v in ("approved", "allow", "accept", "true", "yes"):
            return cls.APPROVED
        if v in ("rejected", "deny", "block", "false", "no"):
            return cls.REJECTED
        if v in ("expired", "timeout"):
            return cls.EXPIRED
        return cls.PENDING


@dataclass
class ApprovalRequest:
    """
    SPEC §13.5: Record of a queued approval request.
    """
    task_id: str
    changes: Any
    status: str
    created_at: float
    expires_at: float
    resolved_at: Optional[float] = None
    resolved_by: Optional[str] = None

    def check_expiration(self, now_ts: Optional[float] = None) -> bool:
        """Update status to expired if TTL has lapsed."""
        now = now_ts if now_ts is not None else time.time()
        if self.status == ApprovalStatus.PENDING.value and now >= self.expires_at:
            self.status = ApprovalStatus.EXPIRED.value
            self.resolved_at = now
            self.resolved_by = "ttl_auto_reject"
            return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ApprovalStore:
    """
    SPEC §13.5: Runtime in-memory approval store.
    """

    def __init__(self, default_ttl: int = 600):
        self.default_ttl = default_ttl
        self._requests: Dict[str, ApprovalRequest] = {}

    def queue_approval(
        self,
        task_id: str,
        changes: Any,
        ttl: Optional[int] = None,
    ) -> ApprovalRequest:
        """
        SPEC §13.5: FUNCTION queue_approval(task_id, changes, ttl=600):
            approval_store.set(task_id, { changes, status: "pending", expires: now()+ttl })
        """
        effective_ttl = ttl if ttl is not None and ttl > 0 else self.default_ttl
        now = time.time()
        expires = now + effective_ttl

        req = ApprovalRequest(
            task_id=task_id,
            changes=changes,
            status=ApprovalStatus.PENDING.value,
            created_at=now,
            expires_at=expires,
        )
        self._requests[task_id] = req
        return req

    def get_approval(self, task_id: str) -> Optional[ApprovalRequest]:
        """Retrieve request and automatically enforce TTL expiration."""
        req = self._requests.get(task_id)
        if req:
            req.check_expiration()
        return req

    def resolve_approval(
        self,
        task_id: str,
        status: Union[str, ApprovalStatus],
        resolved_by: Optional[str] = None,
    ) -> Optional[ApprovalRequest]:
        """
        Approve or reject a pending request.
        """
        req = self.get_approval(task_id)
        if not req:
            return None

        # Expired items cannot be resolved
        if req.status == ApprovalStatus.EXPIRED.value:
            return req

        stat_enum = status if isinstance(status, ApprovalStatus) else ApprovalStatus.from_str(status)
        now = time.time()
        req.status = stat_enum.value
        req.resolved_at = now
        req.resolved_by = resolved_by or "user"
        return req

    def list_pending(self) -> List[ApprovalRequest]:
        """List all active, non-expired pending approvals."""
        pending: List[ApprovalRequest] = []
        for req in self._requests.values():
            if not req.check_expiration() and req.status == ApprovalStatus.PENDING.value:
                pending.append(req)
        return pending

    def wait_for_approval(
        self,
        task_id: str,
        timeout: Optional[float] = None,
        poll_interval: float = 0.05,
    ) -> bool:
        """
        SPEC §13.5: FUNCTION wait_for_approval(task_id, ttl):
            WHILE now() < expires:
                status = approval_store.get(task_id).status
                IF status == "approved": RETURN true
                IF status == "rejected": RETURN false
                sleep(5)
            RETURN false  // TTL expired = auto-reject
        """
        req = self.get_approval(task_id)
        if not req:
            return False

        max_wait = timeout if timeout is not None else (req.expires_at - time.time())
        if max_wait <= 0:
            req.check_expiration()
            return req.status == ApprovalStatus.APPROVED.value

        deadline = time.time() + max_wait
        while time.time() < deadline:
            req = self.get_approval(task_id)
            if not req:
                return False
            if req.status == ApprovalStatus.APPROVED.value:
                return True
            if req.status in (ApprovalStatus.REJECTED.value, ApprovalStatus.EXPIRED.value):
                return False
            time.sleep(poll_interval)

        # Timeout reached
        req = self.get_approval(task_id)
        if req:
            req.check_expiration()
        return req is not None and req.status == ApprovalStatus.APPROVED.value

    def clear(self) -> None:
        """Clear store contents (for testing and reset)."""
        self._requests.clear()
