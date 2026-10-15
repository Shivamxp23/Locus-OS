"""sidecar/vault/livesync_bridge.py - Obsidian Self-Hosted LiveSync CouchDB Bridge.

Implements Spec §27.2 and Security Rule S-2:
- Synchronizes Obsidian Markdown notes between local vault and CouchDB.
- Strictly enforces loopback or HTTPS transport: rejects unencrypted public HTTP (S-2).
- Deterministic multi-client conflict resolution: preserves winner at canonical path
  and creates deterministic sidecar conflict note if divergence occurs.
- Off-state / modular switch: locus.vault.sync_engine (couchdb_livesync | local_only).
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
from pathlib import Path
import time
from typing import Any, Dict, Optional, Protocol, Tuple
import urllib.error
import urllib.parse
import urllib.request

logger = logging.getLogger("sidecar.vault.livesync")

DEFAULT_COUCHDB_URL = "http://127.0.0.1:5984"
DEFAULT_DATABASE = "locus-vault"


class VaultSyncProvider(Protocol):
    """Protocol for vault synchronization providers."""

    def status(self) -> dict[str, Any]:
        """Return provider status."""
        return {"provider": "unconfigured"}

    def push(self, rel_path: str, content: str | bytes, mtime: Optional[int] = None) -> dict[str, Any]:
        """Push note to sync target."""
        return {"status": "unsupported"}

    def pull(self, rel_path: str) -> Optional[dict[str, Any]]:
        """Pull note from sync target."""
        return None


def validate_transport_security(url: str) -> bool:
    """Validate that remote CouchDB URL complies with Security Rule S-2.

    LiveSync reaches CouchDB only over loopback (127.0.0.1 / localhost),
    or secure HTTPS (with TLS reverse proxy / private overlay network).
    Rejects plain unencrypted HTTP over non-loopback addresses.
    """
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    hostname = (parsed.hostname or "").lower()

    if scheme == "https":
        return True

    if scheme == "http":
        if hostname in ("127.0.0.1", "localhost", "::1"):
            return True
        raise ValueError(
            f"Security Law S-2 violation: CouchDB over HTTP is strictly restricted to loopback (127.0.0.1). "
            f"Remote endpoints must use HTTPS, got: {url}"
        )

    raise ValueError(f"Invalid or unsupported URL scheme: {scheme}")


def resolve_concurrent_conflict(
    disk_path: Path,
    remote_bytes: bytes,
    remote_mtime: int,
) -> Tuple[bool, Optional[Path]]:
    """Deterministic conflict resolution between local file and incoming remote document.

    Compares (mtime, sha256_hash). The winner retains the canonical filename,
    while the loser is preserved in a sidecar conflict file: `<stem>.conflict-<timestamp>.md`.
    Returns (local_won, conflict_file_path).
    """
    local_bytes = disk_path.read_bytes() if disk_path.is_file() else b""
    local_mtime = int(disk_path.stat().st_mtime * 1000) if disk_path.is_file() else 0

    local_hash = hashlib.sha256(local_bytes).hexdigest()
    remote_hash = hashlib.sha256(remote_bytes).hexdigest()

    # Exact content match -> no conflict
    if local_hash == remote_hash:
        return True, None

    local_tuple = (local_mtime, local_hash)
    remote_tuple = (remote_mtime, remote_hash)

    timestamp_slug = int(time.time())
    conflict_path = disk_path.parent / f"{disk_path.stem}.conflict-{timestamp_slug}.md"

    if local_tuple >= remote_tuple:
        # Local wins canonical name; remote saved to conflict sidecar
        conflict_path.write_bytes(remote_bytes)
        logger.warning("LiveSync conflict on %s: local preserved, remote saved as %s", disk_path.name, conflict_path.name)
        return True, conflict_path
    else:
        # Remote wins canonical name; local saved to conflict sidecar
        conflict_path.write_bytes(local_bytes)
        disk_path.write_bytes(remote_bytes)
        logger.warning("LiveSync conflict on %s: remote applied, local saved as %s", disk_path.name, conflict_path.name)
        return False, conflict_path


class LiveSyncBridge:
    """Headless CouchDB LiveSync client for Locus OS vault synchronization."""

    def __init__(
        self,
        vault_root: Path,
        couchdb_url: str = DEFAULT_COUCHDB_URL,
        database: str = DEFAULT_DATABASE,
        username: Optional[str] = None,
        password: Optional[str] = None,
        enabled: bool = True,
    ):
        self.vault_root = Path(vault_root).expanduser().resolve()
        self.couchdb_url = couchdb_url.rstrip("/")
        self.database = database
        self.username = username
        self.password = password
        self.enabled = enabled

        if self.enabled:
            validate_transport_security(self.couchdb_url)

    def _get_auth_header(self) -> dict[str, str]:
        if self.username and self.password:
            creds = f"{self.username}:{self.password}".encode("utf-8")
            return {"Authorization": f"Basic {base64.b64encode(creds).decode('ascii')}"}
        return {}

    def status(self) -> dict[str, Any]:
        """Check CouchDB connection status and replication readiness."""
        if not self.enabled:
            return {"status": "disabled", "engine": "local_only"}

        target_url = f"{self.couchdb_url}/{self.database}"
        headers = self._get_auth_header()
        headers["User-Agent"] = "Locus-LiveSyncBridge/1.0"

        req = urllib.request.Request(target_url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                if resp.status in (200, 201):
                    data = json.loads(resp.read().decode("utf-8"))
                    return {
                        "status": "connected",
                        "database": self.database,
                        "doc_count": data.get("doc_count", 0),
                        "update_seq": data.get("update_seq", 0),
                    }
                return {"status": "error", "code": resp.status}
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {"status": "connected", "database": self.database, "database_exists": False}
            return {"status": "auth_error" if e.code in (401, 403) else "http_error", "code": e.code}
        except Exception as e:
            return {"status": "unreachable", "error": str(e)}

    def push(
        self,
        rel_path: str,
        content: str | bytes,
        mtime: Optional[int] = None,
    ) -> dict[str, Any]:
        """Push a note to CouchDB using the Obsidian LiveSync document schema."""
        if not self.enabled:
            return {"status": "skipped", "reason": "sync_disabled"}

        content_bytes = content.encode("utf-8") if isinstance(content, str) else content
        now_ms = mtime or int(time.time() * 1000)
        norm_path = rel_path.replace("\\", "/").strip("/")
        doc_id = f"note:{norm_path.lower()}"

        doc_payload: dict[str, Any] = {
            "_id": doc_id,
            "type": "leaf",
            "path": norm_path,
            "size": len(content_bytes),
            "mtime": now_ms,
            "eden": {
                "content": content_bytes.decode("utf-8", errors="replace"),
                "diff": None,
            },
            "children": [],
        }

        # Check existing revision
        existing = self.pull(rel_path)
        if existing and "_rev" in existing:
            doc_payload["_rev"] = existing["_rev"]

        url = f"{self.couchdb_url}/{self.database}/{urllib.parse.quote(doc_id, safe='')}"
        headers = self._get_auth_header()
        headers["Content-Type"] = "application/json"
        body = json.dumps(doc_payload).encode("utf-8")

        req = urllib.request.Request(url, data=body, headers=headers, method="PUT")
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            return {
                "status": "success",
                "path": norm_path,
                "rev": res_data.get("rev"),
                "doc_id": doc_id,
            }

    def pull(self, rel_path: str) -> Optional[dict[str, Any]]:
        """Retrieve a note document from CouchDB by relative path."""
        if not self.enabled:
            return None

        norm_path = rel_path.replace("\\", "/").strip("/")
        doc_id = f"note:{norm_path.lower()}"
        url = f"{self.couchdb_url}/{self.database}/{urllib.parse.quote(doc_id, safe='')}"

        headers = self._get_auth_header()
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    return data
                return None
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            raise
        except Exception as e:
            logger.error("Failed to pull document %s: %s", doc_id, e)
            return None
