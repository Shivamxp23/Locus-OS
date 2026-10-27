"""
SPEC §25.7 lines 4698-4718: Deferral Detection (3/5/8+).
Thresholds:
    3x defer -> warn: "Consider dropping or delegating"
    5x defer -> escalate: surfaced at weekly review
    8x defer -> flag as phantom task: auto-parked with review note
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("locus.life_os.deferral")


class DeferralAction(str, Enum):
    NORMAL = "normal"
    WARN = "warn"
    ESCALATE = "escalate"
    PHANTOM_PARK = "phantom_park"


@dataclass
class DeferralRecord:
    task_id: str
    deferral_count: int = 0
    history: List[Dict[str, Any]] = field(default_factory=list)
    action: DeferralAction = DeferralAction.NORMAL
    is_parked: bool = False
    message: str = "Task in normal scheduling flow"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "deferral_count": self.deferral_count,
            "action": self.action.value,
            "is_parked": self.is_parked,
            "message": self.message,
            "history_count": len(self.history),
        }


class DeferralTracker:
    """
    SPEC §25.7: Task deferral tracker enforcing 3/5/8+ thresholds.
    """

    def __init__(self) -> None:
        self._records: Dict[str, DeferralRecord] = {}

    def get_record(self, task_id: str) -> DeferralRecord:
        if task_id not in self._records:
            self._records[task_id] = DeferralRecord(task_id=task_id)
        return self._records[task_id]

    def record_deferral(self, task_id: str, reason: str = "") -> DeferralRecord:
        record = self.get_record(task_id)
        record.deferral_count += 1
        entry = {
            "timestamp": time.time(),
            "count": record.deferral_count,
            "reason": reason,
        }
        record.history.append(entry)

        # Enforce thresholds
        if record.deferral_count >= 8:
            record.action = DeferralAction.PHANTOM_PARK
            record.is_parked = True
            record.message = "Flagged as phantom task: auto-parked with review note"
        elif record.deferral_count >= 5:
            record.action = DeferralAction.ESCALATE
            record.is_parked = False
            record.message = "Escalated: surfaced at weekly review for evaluation"
        elif record.deferral_count >= 3:
            record.action = DeferralAction.WARN
            record.is_parked = False
            record.message = "Warn: Consider dropping or delegating"
        else:
            record.action = DeferralAction.NORMAL
            record.is_parked = False
            record.message = f"Deferred {record.deferral_count} time(s)"

        return record

    def list_parked_tasks(self) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self._records.values() if r.is_parked]

    def list_escalations(self) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self._records.values() if r.action == DeferralAction.ESCALATE]
