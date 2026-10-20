"""
SPEC §4.12: Brain reward model interfacing turn outcomes with STDP edge updates.
`sidecar/brain/reward_model.py`
"""
from __future__ import annotations

import time
from typing import Any, Dict, Optional

from sidecar.providers.stdp_reinforcement import OutcomeEvent


class RewardModel:
    """
    Interfaces turn outcomes and user feedback with graph reinforcement.
    """

    def create_outcome_event(
        self,
        session_id: str,
        turn_id: str,
        success: bool,
        occurred_at: Optional[float] = None,
    ) -> OutcomeEvent:
        """Construct an OutcomeEvent for STDP processing."""
        return OutcomeEvent(
            session_id=session_id,
            turn_id=turn_id,
            success=success,
            occurred_at=occurred_at if occurred_at is not None else time.time(),
        )
