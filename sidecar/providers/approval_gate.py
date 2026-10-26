"""
SPEC §13.5 lines 3333-3365:
Approval Gate Provider Interface and Implementation (F-0109 / US-71).

Implements BaseApprovalGateProvider and DefaultApprovalGateProvider with modular off-switches:
- locus.approval_gate.enabled
- locus.security.approval_gate.enabled
"""
from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from typing import Any, Dict, List, Optional

from sidecar.security.approval_store import (
    ApprovalRequest,
    ApprovalStatus,
    ApprovalStore,
)
import sidecar.config as config

logger = logging.getLogger(__name__)


class BaseApprovalGateProvider(ABC):
    """
    SPEC §13.5: Provider Interface: ApprovalGateProvider.
    """

    @abstractmethod
    def is_available(self) -> bool:
        """Check if Approval Gate provider is enabled."""
        raise NotImplementedError

    @abstractmethod
    def queue_approval(self, task_id: str, changes: Any, ttl: Optional[int] = None) -> Dict[str, Any]:
        """Queue approval request with changes and expiration TTL."""
        raise NotImplementedError

    @abstractmethod
    def get_status(self, task_id: str) -> Dict[str, Any]:
        """Retrieve current approval status."""
        raise NotImplementedError

    @abstractmethod
    def resolve(self, task_id: str, status: str, resolved_by: Optional[str] = None) -> Dict[str, Any]:
        """Resolve pending approval (approve or reject)."""
        raise NotImplementedError

    @abstractmethod
    def wait(self, task_id: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Wait for approval until decided or timed out."""
        raise NotImplementedError

    @abstractmethod
    def list_pending(self) -> List[Dict[str, Any]]:
        """List active pending approvals."""
        raise NotImplementedError


class DefaultApprovalGateProvider(BaseApprovalGateProvider):
    """
    SPEC §13.5: Default implementation of ApprovalGateProvider.
    Maintains runtime approval queue with 10-minute default TTL.
    """

    def __init__(self, default_ttl: int = 600):
        self.store = ApprovalStore(default_ttl=default_ttl)

    def is_available(self) -> bool:
        """
        Check modular off-switches:
        - locus.approval_gate.enabled
        - locus.security.approval_gate.enabled
        """
        v1 = config.get("locus.approval_gate.enabled")
        if v1 is not None and not config.is_enabled("locus.approval_gate.enabled"):
            return False

        v2 = config.get("locus.security.approval_gate.enabled")
        if v2 is not None and not config.is_enabled("locus.security.approval_gate.enabled"):
            return False

        return True

    def queue_approval(self, task_id: str, changes: Any, ttl: Optional[int] = None) -> Dict[str, Any]:
        req = self.store.queue_approval(task_id=task_id, changes=changes, ttl=ttl)
        return {
            "status": "ok",
            "request": req.to_dict(),
        }

    def get_status(self, task_id: str) -> Dict[str, Any]:
        req = self.store.get_approval(task_id)
        if not req:
            return {
                "status": "not_found",
                "task_id": task_id,
            }
        return {
            "status": "ok",
            "request": req.to_dict(),
        }

    def resolve(self, task_id: str, status: str, resolved_by: Optional[str] = None) -> Dict[str, Any]:
        req = self.store.resolve_approval(task_id=task_id, status=status, resolved_by=resolved_by)
        if not req:
            return {
                "status": "not_found",
                "task_id": task_id,
            }
        return {
            "status": "ok",
            "request": req.to_dict(),
        }

    def wait(self, task_id: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        approved = self.store.wait_for_approval(task_id=task_id, timeout=timeout)
        req = self.store.get_approval(task_id)
        return {
            "status": "ok",
            "approved": approved,
            "request": req.to_dict() if req else None,
        }

    def list_pending(self) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self.store.list_pending()]
