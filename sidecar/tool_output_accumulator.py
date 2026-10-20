"""
Concrete implementation of Tool Output Accumulator (SPEC §3.10 / F-0102).
Incrementally tracks streaming tool output with bounded memory, tail snapshots,
and disk spillover for full output preservation, mirroring Pi's output-accumulator.ts.
"""
from __future__ import annotations

import io
import logging
import os
import tempfile
import threading
import uuid
from typing import Any, Dict, List, Optional, Union

from sidecar.providers.tool_output_accumulator import (
    BaseToolOutputAccumulatorProvider,
    FullOutputResult,
    OutputAccumulatorConfig,
    OutputSnapshot,
    TruncationType,
)

logger = logging.getLogger(__name__)


class _SessionAccumulator:
    """Per-session bounded streaming accumulator."""

    def __init__(
        self,
        session_id: str,
        max_lines: int = 1000,
        max_bytes: int = 100000,
        temp_file_prefix: str = "locus-output",
    ) -> None:
        self.session_id = session_id
        self.max_lines = max_lines
        self.max_bytes = max_bytes
        self.max_rolling_bytes = max(self.max_bytes * 2, 1024)
        self.temp_file_prefix = temp_file_prefix

        self.lock = threading.Lock()
        self.raw_chunks: List[bytes] = []
        self.tail_text: str = ""
        self.tail_bytes: int = 0
        self.tail_starts_at_line_boundary: bool = True

        self.total_raw_bytes: int = 0
        self.total_decoded_bytes: int = 0
        self.completed_lines: int = 0
        self.total_lines: int = 0
        self.current_line_bytes: int = 0
        self.has_open_line: bool = False
        self.finished: bool = False

        self.temp_file_path: Optional[str] = None
        self._temp_file_handle: Optional[io.BufferedWriter] = None

    def append(self, data: Union[str, bytes]) -> OutputSnapshot:
        with self.lock:
            if self.finished:
                raise RuntimeError("Cannot append to a finished output accumulator")

            raw_bytes: bytes = data.encode("utf-8") if isinstance(data, str) else data
            text: str = data if isinstance(data, str) else data.decode("utf-8", errors="replace")

            self.total_raw_bytes += len(raw_bytes)
            self._append_decoded_text(text)

            if self._temp_file_handle or self._should_use_temp_file():
                self._ensure_temp_file()
                if self._temp_file_handle:
                    self._temp_file_handle.write(raw_bytes)
                    self._temp_file_handle.flush()
            elif len(raw_bytes) > 0:
                self.raw_chunks.append(raw_bytes)

            return self._snapshot_internal(persist_if_truncated=False)

    def finish(self) -> OutputSnapshot:
        with self.lock:
            if not self.finished:
                self.finished = True
                if self._should_use_temp_file():
                    self._ensure_temp_file()
                if self._temp_file_handle:
                    self._temp_file_handle.flush()
            return self._snapshot_internal(persist_if_truncated=True)

    def snapshot(self, persist_if_truncated: bool = True) -> OutputSnapshot:
        with self.lock:
            return self._snapshot_internal(persist_if_truncated=persist_if_truncated)

    def _snapshot_internal(self, persist_if_truncated: bool = True) -> OutputSnapshot:
        # Compute tail truncation
        snapshot_text = self._get_snapshot_text()
        lines = snapshot_text.splitlines(keepends=True)

        truncated_by: Optional[TruncationType] = None
        truncated = False

        if self.total_lines > self.max_lines:
            truncated = True
            truncated_by = TruncationType.LINES
        elif self.total_decoded_bytes > self.max_bytes:
            truncated = True
            truncated_by = TruncationType.BYTES

        # Bounded content calculation
        bounded_content = snapshot_text
        if len(lines) > self.max_lines:
            bounded_content = "".join(lines[-self.max_lines:])
            truncated = True
            truncated_by = TruncationType.LINES

        bounded_bytes = bounded_content.encode("utf-8")
        if len(bounded_bytes) > self.max_bytes:
            # Trim from beginning to fit within max_bytes
            trimmed = bounded_bytes[-self.max_bytes:]
            # Avoid splitting multi-byte UTF-8
            bounded_content = trimmed.decode("utf-8", errors="ignore")
            truncated = True
            truncated_by = TruncationType.BYTES

        if persist_if_truncated and truncated:
            self._ensure_temp_file()

        return OutputSnapshot(
            content=bounded_content,
            truncated=truncated,
            truncated_by=truncated_by,
            total_lines=self.total_lines,
            total_bytes=self.total_decoded_bytes,
            max_lines=self.max_lines,
            max_bytes=self.max_bytes,
            full_output_path=self.temp_file_path,
        )

    def read_full_output(self, max_bytes: int = 50000) -> FullOutputResult:
        with self.lock:
            if not self.temp_file_path:
                full_raw = b"".join(self.raw_chunks)
                if len(full_raw) <= max_bytes:
                    return FullOutputResult(
                        content=full_raw.decode("utf-8", errors="replace"),
                        truncated=False,
                        omitted_bytes=0,
                    )
                # In-memory omission cut
                head_len = max_bytes // 2
                tail_len = max_bytes - head_len
                head = full_raw[:head_len].decode("utf-8", errors="ignore")
                tail = full_raw[-tail_len:].decode("utf-8", errors="ignore")
                omitted = len(full_raw) - head_len - tail_len
                return FullOutputResult(
                    content=f"{head}\n\n[... {omitted} bytes omitted ...]\n\n{tail}",
                    truncated=True,
                    omitted_bytes=omitted,
                )

            # Read from temp file
            if self._temp_file_handle:
                self._temp_file_handle.flush()

            file_size = os.path.getsize(self.temp_file_path)
            if file_size <= max_bytes:
                with open(self.temp_file_path, "rb") as f:
                    content = f.read().decode("utf-8", errors="replace")
                return FullOutputResult(content=content, truncated=False, omitted_bytes=0)

            head_len = max_bytes // 2
            tail_len = max_bytes - head_len
            with open(self.temp_file_path, "rb") as f:
                head_raw = f.read(head_len)
                f.seek(file_size - tail_len)
                tail_raw = f.read(tail_len)

            head_text = head_raw.decode("utf-8", errors="ignore")
            tail_text = tail_raw.decode("utf-8", errors="ignore")
            omitted = file_size - head_len - tail_len
            return FullOutputResult(
                content=f"{head_text}\n\n[... {omitted} bytes omitted ...]\n\n{tail_text}",
                truncated=True,
                omitted_bytes=omitted,
            )

    def close(self) -> None:
        with self.lock:
            if self._temp_file_handle:
                try:
                    self._temp_file_handle.close()
                except Exception:
                    pass
                self._temp_file_handle = None

    def _append_decoded_text(self, text: str) -> None:
        if not text:
            return
        b_len = len(text.encode("utf-8"))
        self.total_decoded_bytes += b_len
        self.tail_text += text
        self.tail_bytes += b_len

        if self.tail_bytes > self.max_rolling_bytes * 2:
            self._trim_tail()

        newlines = text.count("\n")
        if newlines == 0:
            self.current_line_bytes += b_len
            self.has_open_line = True
        else:
            self.completed_lines += newlines
            last_newline = text.rfind("\n")
            tail_slice = text[last_newline + 1 :]
            self.current_line_bytes = len(tail_slice.encode("utf-8"))
            self.has_open_line = len(tail_slice) > 0

        self.total_lines = self.completed_lines + (1 if self.has_open_line else 0)

    def _trim_tail(self) -> None:
        raw = self.tail_text.encode("utf-8")
        if len(raw) <= self.max_rolling_bytes:
            self.tail_bytes = len(raw)
            return

        start = len(raw) - self.max_rolling_bytes
        # UTF-8 continuation byte skip
        while start < len(raw) and (raw[start] & 0xC0) == 0x80:
            start += 1

        self.tail_starts_at_line_boundary = (start == 0) or (raw[start - 1] == 0x0A)
        self.tail_text = raw[start:].decode("utf-8", errors="ignore")
        self.tail_bytes = len(self.tail_text.encode("utf-8"))

    def _get_snapshot_text(self) -> str:
        if self.tail_starts_at_line_boundary:
            return self.tail_text
        first_nl = self.tail_text.find("\n")
        return self.tail_text if first_nl == -1 else self.tail_text[first_nl + 1 :]

    def _should_use_temp_file(self) -> bool:
        return (
            self.total_raw_bytes > self.max_bytes
            or self.total_decoded_bytes > self.max_bytes
            or self.total_lines > self.max_lines
        )

    def _ensure_temp_file(self) -> None:
        if self.temp_file_path:
            return
        fd, path = tempfile.mkstemp(prefix=f"{self.temp_file_prefix}-", suffix=".log")
        self.temp_file_path = path
        self._temp_file_handle = open(fd, "wb")
        for chunk in self.raw_chunks:
            self._temp_file_handle.write(chunk)
        self._temp_file_handle.flush()
        self.raw_chunks.clear()


class ToolOutputAccumulatorProvider(BaseToolOutputAccumulatorProvider):
    """Default provider for Tool Output Accumulator."""

    def __init__(self, name: str = "tool_output_accumulator_default") -> None:
        super().__init__(name=name)
        self._config = OutputAccumulatorConfig()
        self._accumulators: Dict[str, _SessionAccumulator] = {}
        self._lock = threading.Lock()

    def get_config(self) -> OutputAccumulatorConfig:
        return self._config

    def health_check(self) -> Dict[str, Any]:
        with self._lock:
            active_count = len(self._accumulators)
        return {
            "status": "healthy",
            "provider": self.__class__.__name__,
            "active_accumulators": active_count,
            "config": self._config.to_dict(),
        }

    def create_accumulator(
        self,
        accumulator_id: Optional[str] = None,
        max_lines: Optional[int] = None,
        max_bytes: Optional[int] = None,
        temp_file_prefix: Optional[str] = None,
    ) -> str:
        acc_id = accumulator_id or str(uuid.uuid4())
        session = _SessionAccumulator(
            session_id=acc_id,
            max_lines=max_lines or self._config.default_max_lines,
            max_bytes=max_bytes or self._config.default_max_bytes,
            temp_file_prefix=temp_file_prefix or self._config.temp_file_prefix,
        )
        with self._lock:
            self._accumulators[acc_id] = session
        return acc_id

    def append(
        self,
        accumulator_id: str,
        data: Union[str, bytes],
    ) -> OutputSnapshot:
        with self._lock:
            session = self._accumulators.get(accumulator_id)
        if not session:
            raise KeyError(f"Accumulator session '{accumulator_id}' not found")
        return session.append(data)

    def snapshot(
        self,
        accumulator_id: str,
        persist_if_truncated: bool = True,
    ) -> OutputSnapshot:
        with self._lock:
            session = self._accumulators.get(accumulator_id)
        if not session:
            raise KeyError(f"Accumulator session '{accumulator_id}' not found")
        return session.snapshot(persist_if_truncated=persist_if_truncated)

    def finish(self, accumulator_id: str) -> OutputSnapshot:
        with self._lock:
            session = self._accumulators.get(accumulator_id)
        if not session:
            raise KeyError(f"Accumulator session '{accumulator_id}' not found")
        return session.finish()

    def read_full_output(
        self,
        accumulator_id: str,
        max_bytes: int = 50000,
    ) -> FullOutputResult:
        with self._lock:
            session = self._accumulators.get(accumulator_id)
        if not session:
            raise KeyError(f"Accumulator session '{accumulator_id}' not found")
        return session.read_full_output(max_bytes=max_bytes)

    def close(self, accumulator_id: str) -> None:
        with self._lock:
            session = self._accumulators.pop(accumulator_id, None)
        if session:
            session.close()
