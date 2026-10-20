"""
Unit tests for Tool Output Accumulator (SPEC §3.10 / F-0102).
Asserts line and byte truncation, disk spillover, full output omission cuts,
session lifecycle, and modular provider interchangeability.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional, Union

import pytest

from sidecar.providers.tool_output_accumulator import (
    BaseToolOutputAccumulatorProvider,
    FullOutputResult,
    OutputAccumulatorConfig,
    OutputSnapshot,
    TruncationType,
)
from sidecar.registry import ProviderRegistry
from sidecar.tool_output_accumulator import ToolOutputAccumulatorProvider


def test_accumulator_basic_append_no_truncation():
    """SPEC §3.10 line 2700: "Scope: Built-in truncation. Inherited unchanged." """
    provider = ToolOutputAccumulatorProvider()
    acc_id = provider.create_accumulator(max_lines=10, max_bytes=1000)

    snap = provider.append(acc_id, "hello world\nline two\n")
    assert snap.truncated is False
    assert snap.truncated_by is None
    assert snap.total_lines == 2
    assert "hello world" in snap.content
    assert snap.full_output_path is None

    provider.close(acc_id)


def test_accumulator_line_limit_truncation():
    """SPEC §3.10 line 2700: "Scope: Built-in truncation. Inherited unchanged." """
    provider = ToolOutputAccumulatorProvider()
    acc_id = provider.create_accumulator(max_lines=3, max_bytes=5000)

    # Append 5 lines
    for i in range(5):
        provider.append(acc_id, f"Line number {i}\n")

    snap = provider.snapshot(acc_id, persist_if_truncated=True)
    assert snap.truncated is True
    assert snap.truncated_by == TruncationType.LINES
    assert snap.total_lines == 5
    # Snapshot content should only retain the last 3 lines
    lines = [ln.strip() for ln in snap.content.splitlines() if ln.strip()]
    assert len(lines) == 3
    assert lines[-1] == "Line number 4"
    assert lines[0] == "Line number 2"
    assert snap.full_output_path is not None
    assert os.path.exists(snap.full_output_path)

    provider.close(acc_id)


def test_accumulator_byte_limit_truncation():
    """SPEC §3.10 line 2700: "Scope: Built-in truncation. Inherited unchanged." """
    provider = ToolOutputAccumulatorProvider()
    # 50 bytes limit, plenty of lines
    acc_id = provider.create_accumulator(max_lines=100, max_bytes=50)

    long_chunk = "A" * 120
    snap = provider.append(acc_id, long_chunk)
    assert snap.truncated is True
    assert snap.truncated_by == TruncationType.BYTES
    assert len(snap.content.encode("utf-8")) <= 50
    assert snap.total_bytes == 120

    provider.close(acc_id)


def test_accumulator_temp_file_spillover():
    """SPEC §3.10 line 2698: "Verdict: 📦 KEEP-PI · Source: pi/output-accumulator.ts · Repo vs .locus: locus-os (inherited)" """
    provider = ToolOutputAccumulatorProvider()
    acc_id = provider.create_accumulator(max_lines=5, max_bytes=100)

    for i in range(15):
        provider.append(acc_id, f"Log record {i} with some descriptive padding\n")

    snap = provider.finish(acc_id)
    assert snap.truncated is True
    assert snap.full_output_path is not None
    assert os.path.exists(snap.full_output_path)

    # Verify temp file contains the entire unabridged log
    with open(snap.full_output_path, "r", encoding="utf-8") as f:
        full_disk = f.read()
    assert "Log record 0" in full_disk
    assert "Log record 14" in full_disk

    provider.close(acc_id)


def test_accumulator_read_full_output_with_omission():
    """SPEC §3.10 line 2698: "Verdict: 📦 KEEP-PI · Source: pi/output-accumulator.ts · Repo vs .locus: locus-os (inherited)" """
    provider = ToolOutputAccumulatorProvider()
    acc_id = provider.create_accumulator(max_lines=5, max_bytes=100)

    for i in range(20):
        provider.append(acc_id, f"Entry {i:02d}: payload data line\n")

    provider.finish(acc_id)

    # Read full output with budget smaller than total output
    full_res = provider.read_full_output(acc_id, max_bytes=80)
    assert full_res.truncated is True
    assert "bytes omitted" in full_res.content
    assert full_res.omitted_bytes > 0
    # Head and tail both represented
    assert "Entry 00" in full_res.content
    assert "Entry 19" in full_res.content

    provider.close(acc_id)


def test_accumulator_finish_and_reappend_error():
    """SPEC §3.10 line 2700: "Scope: Built-in truncation. Inherited unchanged." """
    provider = ToolOutputAccumulatorProvider()
    acc_id = provider.create_accumulator()

    provider.append(acc_id, "first chunk")
    provider.finish(acc_id)

    with pytest.raises(RuntimeError, match="Cannot append to a finished"):
        provider.append(acc_id, "second chunk")

    provider.close(acc_id)


def test_accumulator_session_lifecycle_and_close():
    """SPEC §3.10 line 2700: "Scope: Built-in truncation. Inherited unchanged." """
    provider = ToolOutputAccumulatorProvider()
    acc_id = provider.create_accumulator()

    provider.append(acc_id, "test data")
    health = provider.health_check()
    assert health["active_accumulators"] == 1

    provider.close(acc_id)
    health_after = provider.health_check()
    assert health_after["active_accumulators"] == 0

    with pytest.raises(KeyError, match="not found"):
        provider.snapshot(acc_id)


def test_modular_accumulator_provider_swap():
    """SPEC §3.10 line 2699: "Off state: N/A (core Pi infrastructure)" """
    registry = ProviderRegistry()

    class CustomAccumulatorProvider(BaseToolOutputAccumulatorProvider):
        def create_accumulator(self, accumulator_id=None, max_lines=None, max_bytes=None, temp_file_prefix=None):
            return "custom-acc-1"

        def append(self, accumulator_id: str, data: Union[str, bytes]) -> OutputSnapshot:
            return OutputSnapshot(content="custom-append", truncated=False)

        def snapshot(self, accumulator_id: str, persist_if_truncated: bool = True) -> OutputSnapshot:
            return OutputSnapshot(content="custom-snapshot", truncated=False)

        def finish(self, accumulator_id: str) -> OutputSnapshot:
            return OutputSnapshot(content="custom-finish", truncated=False)

        def read_full_output(self, accumulator_id: str, max_bytes: int = 50000) -> FullOutputResult:
            return FullOutputResult(content="custom-full", truncated=False)

        def close(self, accumulator_id: str) -> None:
            pass

        def get_config(self) -> OutputAccumulatorConfig:
            return OutputAccumulatorConfig()

        def health_check(self) -> Dict[str, Any]:
            return {"status": "custom"}

    registry.register("tool_output_accumulator", "custom", CustomAccumulatorProvider)
    active_cls = registry.get_active_provider("tool_output_accumulator", default_name="custom")
    assert active_cls is CustomAccumulatorProvider

    inst = active_cls()
    assert inst.create_accumulator() == "custom-acc-1"
    assert inst.snapshot("custom-acc-1").content == "custom-snapshot"
