"""Locus Cron Runner — executes scheduled tasks via pi_bridge.run_pi_turn.

Enforces that cron executions start Pi ONLY through run_pi_turn with session_id='cron_<job_id>'.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sidecar.pi_bridge import PiTurnResult, run_pi_turn

logger = logging.getLogger("sidecar.cron_runner")


def match_field(val: int, expr: str, is_day_of_week: bool = False) -> bool:
    """Evaluate a single cron field expression against an integer value."""
    if expr == "*":
        return True
    if "," in expr:
        return any(match_field(val, part.strip(), is_day_of_week) for part in expr.split(","))
    if expr.startswith("*/"):
        try:
            step = int(expr[2:])
            return step > 0 and val % step == 0
        except ValueError:
            return False
    if "-" in expr:
        try:
            start, end = map(int, expr.split("-"))
            return start <= val <= end
        except ValueError:
            return False
    try:
        target = int(expr)
        if is_day_of_week:
            cron_day = (val + 1) % 7
            if target == 7:
                target = 0
            return cron_day == target
        return val == target
    except ValueError:
        return False


def matches_schedule(dt: datetime, cron_expr: str) -> bool:
    """Check if a datetime matches a standard 5-part cron expression."""
    cron_expr = cron_expr.strip()
    shorthands = {
        "@hourly": "0 * * * *",
        "@daily": "0 0 * * *",
        "@weekly": "0 0 * * 0",
        "@monthly": "0 0 1 * *",
    }
    cron_expr = shorthands.get(cron_expr, cron_expr)
    parts = cron_expr.split()
    if len(parts) != 5:
        return False
    min_exp, hour_exp, dom_exp, month_exp, dow_exp = parts
    return (
        match_field(dt.minute, min_exp)
        and match_field(dt.hour, hour_exp)
        and match_field(dt.day, dom_exp)
        and match_field(dt.month, month_exp)
        and match_field(dt.weekday(), dow_exp, is_day_of_week=True)
    )


def execute_cron_job(job_id: str, prompt: str, timeout: int = 300) -> PiTurnResult:
    """Execute a scheduled cron job via Pi bridge using session id cron_<job_id>."""
    session_id = f"cron_{job_id}"
    logger.info("Starting cron job %s (session %s)", job_id, session_id)
    return run_pi_turn(prompt=prompt, session_id=session_id, timeout=timeout)
