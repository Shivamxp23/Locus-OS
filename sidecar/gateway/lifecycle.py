"""
SPEC §17.10 lines 3855-3926:
Graceful Gateway Restart & State Snapshotting (F-0047 / US-80).

Implements 30s connection draining, session disk snapshot serialization,
forensic telemetry logging, and crash-resilient session recovery.
"""
from __future__ import annotations

import json
import logging
import os
import pathlib
import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class ForensicRecord:
    """Forensic telemetry captured during gateway shutdown."""
    forensic_id: str
    reason: str
    active_sessions_count: int
    pending_events: int
    uptime_seconds: float
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SessionSnapshot:
    """In-memory session state snapshot serialized for crash recovery."""
    session_id: str
    user_id: str
    channel: str
    state_data: Dict[str, Any]
    last_active: float = field(default_factory=time.time)
    snapshot_timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BaseChannelAdapter(ABC):
    """Abstract interface for ingress channel adapters (Telegram, Discord, etc.)."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def stop_receiving_new_messages(self) -> bool:
        """SPEC §17.10 line 3881: Stop Ingress (De-register webhook / stop polling)."""
        pass


class MockChannelAdapter(BaseChannelAdapter):
    """Deterministic channel adapter for testing graceful shutdown sequences."""

    def __init__(self, name: str = "mock_channel") -> None:
        self._name = name
        self.stopped = False

    @property
    def name(self) -> str:
        return self._name

    def stop_receiving_new_messages(self) -> bool:
        self.stopped = True
        return True


class GatewayLifecycleManager:
    """
    SPEC §17.10 lines 3869-3914:
    Central communication gateway supervisor; handles SIGTERM/SIGUSR1/RELOAD,
    in-flight connection draining, session serialization, and forensic logging.
    """

    def __init__(
        self,
        drain_timeout_seconds: float = 30.0,
        recovery_dir: Optional[str] = None,
        forensics_dir: Optional[str] = None,
    ) -> None:
        self.drain_timeout_seconds: float = drain_timeout_seconds
        self.active_in_flight_requests: Set[str] = set()
        self.active_sessions: Dict[str, SessionSnapshot] = {}
        self.channel_adapters: List[BaseChannelAdapter] = []
        self.is_shutting_down: bool = False
        self.start_time: float = time.time()
        self.db_pools_closed: bool = False
        self.forensic_history: List[ForensicRecord] = []

        if recovery_dir:
            self.recovery_dir = pathlib.Path(recovery_dir)
        else:
            home = pathlib.Path.home()
            self.recovery_dir = home / ".locus" / "sessions" / "recovery"

        if forensics_dir:
            self.forensics_dir = pathlib.Path(forensics_dir)
        else:
            home = pathlib.Path.home()
            self.forensics_dir = home / ".locus" / "forensics"

    def get_uptime(self) -> float:
        """Return server uptime in seconds."""
        return time.time() - self.start_time

    def register_adapter(self, adapter: BaseChannelAdapter) -> None:
        """Register a channel adapter for ingress management."""
        self.channel_adapters.append(adapter)

    def register_in_flight(self, request_id: str) -> None:
        """Track in-flight request ID."""
        self.active_in_flight_requests.add(request_id)

    def unregister_in_flight(self, request_id: str) -> None:
        """Release tracked in-flight request."""
        self.active_in_flight_requests.discard(request_id)

    def register_session(
        self,
        session_id: str,
        user_id: str = "anonymous",
        channel: str = "default",
        state_data: Optional[Dict[str, Any]] = None,
    ) -> SessionSnapshot:
        """Register active in-memory session for lifecycle tracking."""
        snap = SessionSnapshot(
            session_id=session_id,
            user_id=user_id,
            channel=channel,
            state_data=state_data or {},
            last_active=time.time(),
        )
        self.active_sessions[session_id] = snap
        return snap

    def remove_session(self, session_id: str) -> None:
        """Remove finished session from active tracking."""
        self.active_sessions.pop(session_id, None)

    def drain_connections(self, check_interval: float = 0.05) -> int:
        """
        SPEC §17.10 line 3885:
        // 2. Drain In-Flight Requests
        start_time = now()
        WHILE len(self.active_in_flight_requests) > 0 AND (now() - start_time) < self.drain_timeout_seconds:
            sleep(0.5)
        """
        start = time.time()
        while len(self.active_in_flight_requests) > 0 and (time.time() - start) < self.drain_timeout_seconds:
            time.sleep(check_interval)

        remaining = len(self.active_in_flight_requests)
        if remaining > 0:
            logger.warning(
                f"Drain timeout reached ({self.drain_timeout_seconds}s). "
                f"Forcefully serializing {remaining} pending sessions."
            )
        return remaining

    def snapshot_sessions(self) -> List[str]:
        """
        SPEC §17.10 line 3892:
        // 3. Snapshot In-Memory Session States to Disk
        FOR EACH session IN active_sessions:
            snapshot = serialize_session_state(session)
            write_json(f"~/.locus/sessions/recovery/{session.id}.json", snapshot)
        """
        self.recovery_dir.mkdir(parents=True, exist_ok=True)
        saved_files: List[str] = []

        for sid, session in self.active_sessions.items():
            session.snapshot_timestamp = time.time()
            target_path = self.recovery_dir / f"{sid}.json"
            try:
                with open(target_path, "w", encoding="utf-8") as f:
                    json.dump(session.to_dict(), f, indent=2)
                saved_files.append(str(target_path))
            except Exception as exc:
                logger.error(f"Failed to snapshot session {sid}: {exc}")

        return saved_files

    def recover_sessions(self) -> List[SessionSnapshot]:
        """
        Recover previously snapshotted session states from disk on startup.
        """
        recovered: List[SessionSnapshot] = []
        if not self.recovery_dir.exists():
            return recovered

        for p in self.recovery_dir.glob("*.json"):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                snap = SessionSnapshot(
                    session_id=data["session_id"],
                    user_id=data.get("user_id", "recovered"),
                    channel=data.get("channel", "recovered"),
                    state_data=data.get("state_data", {}),
                    last_active=data.get("last_active", time.time()),
                    snapshot_timestamp=data.get("snapshot_timestamp", time.time()),
                )
                self.active_sessions[snap.session_id] = snap
                recovered.append(snap)
            except Exception as exc:
                logger.error(f"Failed to load recovery snapshot {p}: {exc}")

        return recovered

    def log_shutdown_forensics(self, signal_type: str) -> ForensicRecord:
        """
        SPEC §17.10 line 3898:
        // 4. Record Forensic Log in Database
        log_shutdown_forensics(
            reason=signal_type,
            active_sessions_count=len(active_sessions),
            pending_events=len(self.active_in_flight_requests),
            uptime=get_uptime()
        )
        """
        self.forensics_dir.mkdir(parents=True, exist_ok=True)
        f_id = f"forensic_{int(time.time() * 1000)}"
        record = ForensicRecord(
            forensic_id=f_id,
            reason=signal_type,
            active_sessions_count=len(self.active_sessions),
            pending_events=len(self.active_in_flight_requests),
            uptime_seconds=self.get_uptime(),
        )
        self.forensic_history.append(record)

        target = self.forensics_dir / f"{f_id}.json"
        try:
            with open(target, "w", encoding="utf-8") as f:
                json.dump(record.to_dict(), f, indent=2)
        except Exception as exc:
            logger.error(f"Failed to record forensics log: {exc}")

        return record

    def close_all_db_pools(self) -> None:
        """SPEC §17.10 line 3907: Close Database Pools & Clean Up."""
        self.db_pools_closed = True

    def handle_shutdown_signal(
        self,
        signal_type: str = "SIGTERM",
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """
        SPEC §17.10 lines 3874-3914:
        Executes full graceful shutdown pipeline:
        1. Stop Ingress
        2. Drain In-Flight Requests
        3. Snapshot Sessions
        4. Log Forensics
        5. Close DB Pools
        """
        if self.is_shutting_down:
            return {
                "status": "already_shutting_down",
                "is_shutting_down": True,
            }

        self.is_shutting_down = True
        logger.info(f"Initiating graceful shutdown sequence ({signal_type}). Draining active connections...")

        # 1. Stop ingress on all channel adapters
        stopped_adapters: List[str] = []
        for adapter in self.channel_adapters:
            if adapter.stop_receiving_new_messages():
                stopped_adapters.append(adapter.name)

        # 2. Drain in-flight requests
        remaining_pending = self.drain_connections()

        # 3. Snapshot sessions to disk
        saved_snapshots = self.snapshot_sessions()

        # 4. Record forensic log
        forensic = self.log_shutdown_forensics(signal_type=signal_type)

        # 5. Close DB pools
        self.close_all_db_pools()

        return {
            "status": "gracefully_stopped",
            "signal": signal_type,
            "stopped_adapters": stopped_adapters,
            "remaining_pending": remaining_pending,
            "snapshots_saved": len(saved_snapshots),
            "forensic_id": forensic.forensic_id,
            "uptime_seconds": forensic.uptime_seconds,
            "dry_run": dry_run,
        }

    def get_status(self) -> Dict[str, Any]:
        """Return diagnostic lifecycle status."""
        return {
            "is_shutting_down": self.is_shutting_down,
            "active_in_flight_count": len(self.active_in_flight_requests),
            "active_sessions_count": len(self.active_sessions),
            "registered_adapters_count": len(self.channel_adapters),
            "drain_timeout_seconds": self.drain_timeout_seconds,
            "uptime_seconds": self.get_uptime(),
            "db_pools_closed": self.db_pools_closed,
        }
