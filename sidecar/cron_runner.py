from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sidecar.config import get as config_get, get_env, is_enabled
from sidecar.pi_bridge import PiTurnResult, run_pi_turn

logger = logging.getLogger("sidecar.cron_runner")

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_FILE = "cron.db"


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


def ensure_cron_db(db_path: Path) -> None:
    """Initialize SQLite database for cron execution logs."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cron_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                job_id TEXT NOT NULL,
                status TEXT NOT NULL,
                returncode INTEGER,
                token_usage INTEGER DEFAULT 0,
                output_path TEXT,
                error TEXT
            )
            """
        )
        conn.commit()


def record_cron_execution(
    db_path: Path,
    job_id: str,
    status: str,
    returncode: int | None,
    token_usage: int = 0,
    output_path: str | None = None,
    error: str | None = None,
) -> int:
    """Record execution details into cron_executions table."""
    ensure_cron_db(db_path)
    now_iso = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(str(db_path)) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO cron_executions (timestamp, job_id, status, returncode, token_usage, output_path, error)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (now_iso, job_id, status, returncode, token_usage, output_path, error),
        )
        conn.commit()
        return cur.lastrowid or 0


def get_execution_logs(db_path: Path, limit: int = 50) -> list[dict[str, Any]]:
    """Retrieve recent execution logs from the database."""
    if not db_path.exists():
        return []
    with sqlite3.connect(str(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM cron_executions ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        rows = cur.fetchall()
        return [dict(row) for row in rows]


def resolve_vault_destination(destination_template: str, job_id: str, vault_root: Path) -> Path:
    """Resolve vault output path replacing tokens like YYYY-MM-DD and <name>."""
    dest = destination_template.strip()
    # Normalize vault prefix
    if dest.startswith("vault/") or dest.startswith("vault\\"):
        dest = dest[6:]
    elif dest.startswith("/vault/") or dest.startswith("\\vault\\"):
        dest = dest[7:]

    now = datetime.now()
    dest = dest.replace("YYYY-MM-DD", now.strftime("%Y-%m-%d"))
    dest = dest.replace("<name>", job_id)
    return (vault_root / dest).resolve()


def format_vault_markdown(
    title: str,
    content: str,
    job_id: str,
    tags: list[str] | None = None,
) -> str:
    """Format markdown note with required YAML frontmatter."""
    tags_list = tags or ["research", "automated"]
    tags_formatted = "\n".join(f"  - {t}" for t in tags_list)
    date_str = datetime.now().strftime("%Y-%m-%d")
    return (
        f"---\n"
        f"title: \"{title}\"\n"
        f"date: \"{date_str}\"\n"
        f"source: locus-scheduler\n"
        f"job_id: \"{job_id}\"\n"
        f"tags:\n{tags_formatted}\n"
        f"---\n\n"
        f"{content}\n"
    )


def format_notification_message(
    job_title: str,
    status: str,
    timestamp: str,
    body: str,
) -> str:
    """Format notification message for delivery to channel recipient."""
    status_str = status.upper()
    body_str = body.strip() if body else "(No output generated)"
    return (
        f"📊 Research Job: {job_title}\n"
        f"Status: {status_str}\n"
        f"Timestamp: {timestamp}\n\n"
        f"{body_str}"
    )


def get_paired_owner_chat_id(channel: Any, custom_config_path: Path | None = None) -> int | str | None:
    """Resolve paired owner ID from channel pairing manager or config."""
    if hasattr(channel, "pairing_manager") and channel.pairing_manager is not None:
        try:
            allowed = channel.pairing_manager.get_allowed_user_ids()
            if allowed:
                return allowed[0]
        except Exception:
            pass

    # Check config paths
    for key in (
        "locus.channels.telegram.allowed_user_ids",
        "locus.channel.telegram.allowed_user_ids",
    ):
        val = config_get(key, custom_path=custom_config_path)
        if isinstance(val, list) and val:
            return val[0]

    for key in (
        "locus.channels.telegram.allowed_user_id",
        "locus.channel.telegram.allowed_user_id",
    ):
        val = config_get(key, custom_path=custom_config_path)
        if val is not None:
            return val

    return None


def dispatch_job_notification(
    job: Any,
    status: str,
    stdout: str,
    stderr: str,
    custom_config_path: Path | None = None,
    channel_provider: Any = None,
) -> tuple[bool, str | None]:
    """Deliver completed research job results to the paired owner via ChannelProvider."""
    if not getattr(job, "notify", True):
        return True, None

    from sidecar.registry import get_registry

    channel = channel_provider
    if channel is None:
        try:
            reg = get_registry()
            # Try channel provider
            try:
                channel = reg.get("channel", custom_config_path=custom_config_path)
            except Exception:
                channel = reg.get(("channel", "telegram"), custom_config_path=custom_config_path)
        except Exception as e:
            logger.warning("No channel provider registered: %s", e)
            return False, f"No channel provider registered: {e}"

    if channel is None:
        logger.warning("Channel provider is None; notification skipped")
        return False, "Channel provider is None"

    owner_id = get_paired_owner_chat_id(channel, custom_config_path=custom_config_path)
    if owner_id is None:
        msg = "No paired owner chat ID found; notification skipped"
        logger.warning(msg)
        return False, msg

    body = stdout if status == "success" else f"ERROR: {stderr or 'Unknown error'}"
    timestamp_str = datetime.now(timezone.utc).isoformat()
    job_name = getattr(job, "name", getattr(job, "id", "Research Job"))
    formatted_msg = format_notification_message(
        job_title=job_name,
        status=status,
        timestamp=timestamp_str,
        body=body,
    )

    try:
        ok = channel.send_message(recipient=owner_id, text=formatted_msg)
        if ok:
            logger.info("Delivered research job notification to recipient %s", owner_id)
            return True, None
        else:
            msg = f"Channel send_message returned False for recipient {owner_id}"
            logger.warning(msg)
            return False, msg
    except Exception as e:
        msg = f"Channel send_message raised exception: {e}"
        logger.error(msg)
        return False, msg


def run_research_job(
    job: Any,
    vault_root: Path | None = None,
    db_path: Path | None = None,
    custom_config_path: Path | None = None,
    timeout: int = 300,
    channel_provider: Any = None,
) -> dict[str, Any]:
    """Execute a research job according to errata D-15.
    
    1. Checks if locus.scheduler.enabled is true.
    2. Runs Pi turn with session_id='cron_<job_id>'.
    3. Writes markdown output to vault destination with frontmatter.
    4. Delivers notification to paired owner on Telegram if notify is enabled.
    5. Records execution log in SQLite table.
    """
    val = config_get("locus.scheduler.enabled", default=True, custom_path=custom_config_path)
    if isinstance(val, bool):
        is_on = val
    elif isinstance(val, str):
        is_on = val.strip().lower() in ("true", "1", "yes", "on")
    elif isinstance(val, (int, float)):
        is_on = val != 0
    else:
        is_on = True

    if not is_on:
        logger.info("Scheduler disabled by config; skipping job %s", getattr(job, "id", str(job)))
        return {
            "job_id": getattr(job, "id", str(job)),
            "status": "disabled",
            "returncode": None,
            "output_path": None,
            "error": "scheduler disabled by config",
            "notify_delivered": False,
        }

    job_id = getattr(job, "id", str(job))
    job_name = getattr(job, "name", job_id)
    prompt = getattr(job, "prompt", "")
    destination = getattr(job, "destination", "vault/05-Daily/Research/YYYY-MM-DD-<name>.md")

    # Resolve paths
    v_root = vault_root or (REPO_ROOT / "vault")
    locus_home = Path(get_env("LOCUS_HOME", default=str(Path.home() / ".locus")))
    d_path = db_path or (locus_home / DEFAULT_DB_FILE)

    res = execute_cron_job(job_id=job_id, prompt=prompt, timeout=timeout)

    output_path_str: str | None = None
    delivery_err: str | None = None
    notify_ok = False

    if res.ok:
        status = "success"
        error_msg = None
        target_path = resolve_vault_destination(destination, job_id, v_root)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        markdown = format_vault_markdown(title=job_name, content=res.stdout, job_id=job_id)
        target_path.write_text(markdown, encoding="utf-8")
        output_path_str = str(target_path)
        logger.info("Research job %s succeeded, output written to %s", job_id, output_path_str)
    else:
        status = "failed"
        error_msg = res.stderr or f"Process exited with code {res.returncode}"
        logger.warning("Research job %s failed: %s", job_id, error_msg)

    # Deliver notification if enabled
    if getattr(job, "notify", True):
        notify_ok, delivery_err = dispatch_job_notification(
            job=job,
            status=status,
            stdout=res.stdout,
            stderr=res.stderr,
            custom_config_path=custom_config_path,
            channel_provider=channel_provider,
        )
        if delivery_err:
            if error_msg:
                error_msg = f"{error_msg}; Delivery error: {delivery_err}"
            else:
                error_msg = f"Delivery error: {delivery_err}"

    record_cron_execution(
        db_path=d_path,
        job_id=job_id,
        status=status,
        returncode=res.returncode,
        token_usage=0,
        output_path=output_path_str,
        error=error_msg,
    )

    return {
        "job_id": job_id,
        "status": status,
        "returncode": res.returncode,
        "output_path": output_path_str,
        "error": error_msg,
        "notify_delivered": notify_ok,
    }

