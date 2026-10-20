"""
SPEC §4.14 lines 1424, 1459-1465:
Cold Storage Archiver for Deeply Decayed Memory Clusters.
Serializes and moves deeply decayed memory nodes from active Neo4j graph / memory store
to compressed JSONL storage under .locus/memory/cold_archive/{project_id}.jsonl.gz.
"""
from __future__ import annotations

import gzip
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from sidecar import config


def get_cold_archive_dir(override_dir: Optional[Path | str] = None) -> Path:
    """Return the directory for cold archive storage, resolving relative to LOCUS_HOME."""
    if override_dir:
        archive_dir = Path(override_dir).expanduser().resolve()
    else:
        archive_dir = config.get_locus_home() / "memory" / "cold_archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    return archive_dir


def get_cold_archive_path(project_id: str, override_dir: Optional[Path | str] = None) -> Path:
    """Return the canonical .jsonl.gz path for a given project ID."""
    clean_id = str(project_id).strip().replace("/", "_").replace("\\", "_")
    return get_cold_archive_dir(override_dir) / f"{clean_id}.jsonl.gz"


def archive_cluster_to_cold_storage(
    project_id: str,
    nodes: List[Dict[str, Any]],
    override_dir: Optional[Path | str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Path:
    """
    SPEC §4.14 lines 1459-1465:
    Archive node cluster to compressed cold JSONL storage (.jsonl.gz).
    Writes cluster metadata header followed by each individual memory node.
    """
    archive_path = get_cold_archive_path(project_id, override_dir)
    archive_path.parent.mkdir(parents=True, exist_ok=True)

    header = {
        "_locus_cold_archive": True,
        "project_id": str(project_id),
        "archived_at": time.time(),
        "node_count": len(nodes),
        "metadata": metadata or {},
    }

    temp_path = archive_path.with_suffix(".tmp.gz")
    try:
        with gzip.open(temp_path, "wt", encoding="utf-8") as f:
            f.write(json.dumps(header, ensure_ascii=False) + "\n")
            for node in nodes:
                f.write(json.dumps(node, ensure_ascii=False) + "\n")
        # Atomic rename
        if temp_path.exists():
            temp_path.replace(archive_path)
    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass

    return archive_path


def load_cold_archive(
    project_id: str,
    override_dir: Optional[Path | str] = None,
) -> Dict[str, Any]:
    """
    Read and decompress cold archived memory cluster.
    Returns dictionary with header metadata and list of nodes.
    """
    archive_path = get_cold_archive_path(project_id, override_dir)
    if not archive_path.is_file():
        raise FileNotFoundError(f"No cold archive found for project {project_id} at {archive_path}")

    header: Dict[str, Any] = {}
    nodes: List[Dict[str, Any]] = []

    with gzip.open(archive_path, "rt", encoding="utf-8") as f:
        first_line = True
        for line in f:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            if first_line and entry.get("_locus_cold_archive"):
                header = entry
                first_line = False
            else:
                first_line = False
                nodes.append(entry)

    return {
        "project_id": project_id,
        "archive_path": str(archive_path),
        "header": header,
        "nodes": nodes,
        "node_count": len(nodes),
    }


def list_cold_archives(override_dir: Optional[Path | str] = None) -> List[Dict[str, Any]]:
    """List all available cold archive files and their sizes/timestamps."""
    archive_dir = get_cold_archive_dir(override_dir)
    results: List[Dict[str, Any]] = []

    for path in archive_dir.glob("*.jsonl.gz"):
        try:
            stat = path.stat()
            project_id = path.name[:-9]  # strip .jsonl.gz
            results.append({
                "project_id": project_id,
                "path": str(path),
                "size_bytes": stat.st_size,
                "modified_at": stat.st_mtime,
            })
        except Exception:
            continue

    return sorted(results, key=lambda x: str(x["project_id"]))
