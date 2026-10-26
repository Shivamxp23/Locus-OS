"""
SPEC §10.9 lines 6356-6430:
Agent Experience Tracking (Procedural Memory) (F-0121 / US-67).

Captures procedural lessons from tool execution loops and injects relevant
operating experience into context before user turns.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import datetime
import hashlib
import json
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Scrubbing regexes per §10.9
BEARER_PATTERN = re.compile(r"Bearer\s+[A-Za-z0-9_\-\.]+", re.IGNORECASE)
SK_PATTERN = re.compile(r"sk-[A-Za-z0-9_\-\.]+", re.IGNORECASE)
SECRET_PATTERN = re.compile(
    r"(?i)\b(token|api_key|secret|password)\s*[:=]\s*[^\s,\"\']+"
)


def redact_text(text: str) -> str:
    """
    SPEC §10.9: Redaction before persistence.
    Scrub Bearer tokens, sk- keys, and password/secret assignments.
    """
    if not text:
        return ""
    scrubbed = BEARER_PATTERN.sub("Bearer [redacted]", text)
    scrubbed = SK_PATTERN.sub("sk-[redacted]", scrubbed)
    scrubbed = SECRET_PATTERN.sub(r"\1=[redacted]", scrubbed)
    return scrubbed


def stable_experience_id(task_summary: str, tool_sequence: List[str], outcome: str) -> str:
    """
    SPEC §10.9: Deterministic deduplication id.
    sha256(task_summary.lower() + "".join(tool_sequence).lower() + outcome.lower())[:24], prefixed exp_.
    """
    raw = (
        (task_summary or "").strip().lower()
        + "".join(t.strip().lower() for t in tool_sequence)
        + (outcome or "").strip().lower()
    )
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
    return f"exp_{digest}"


@dataclass
class AgentExperience:
    """
    SPEC §10.9: The record (AgentExperience).
    """
    id: str
    source: str  # ToolLoop | AgentReflection | Manual | WorkflowCandidate
    agent_id: str
    entrypoint: str
    task_fingerprint: str
    task_summary: str
    tools_used: List[str]
    tool_sequence: List[str]
    outcome: str  # Success | Failure | Partial
    lesson: str
    confidence: float
    reuse_hint: Optional[str] = None
    avoid_hint: Optional[str] = None
    error_class: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    dismissed: bool = False
    created_at: str = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AgentExperience:
        return cls(
            id=data["id"],
            source=data.get("source", "ToolLoop"),
            agent_id=data.get("agent_id", "locus-agent"),
            entrypoint=data.get("entrypoint", "tool_loop"),
            task_fingerprint=data.get("task_fingerprint", ""),
            task_summary=data.get("task_summary", "")[:280],
            tools_used=list(data.get("tools_used", [])),
            tool_sequence=list(data.get("tool_sequence", [])),
            outcome=data.get("outcome", "Success"),
            lesson=data.get("lesson", ""),
            confidence=float(data.get("confidence", 0.5)),
            reuse_hint=data.get("reuse_hint"),
            avoid_hint=data.get("avoid_hint"),
            error_class=data.get("error_class"),
            tags=list(data.get("tags", [])),
            dismissed=bool(data.get("dismissed", False)),
            created_at=data.get(
                "created_at",
                datetime.datetime.now(datetime.timezone.utc).isoformat(),
            ),
        )


class ExperienceStore:
    """
    SPEC §10.9: AgentExperienceStore.
    Manages persistence and queries for procedural memories.
    """

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or (Path.home() / ".locus" / "experience")
        self.storage_file = self.storage_dir / "experiences.json"
        self._cache: Dict[str, AgentExperience] = {}
        self._load()

    def _load(self) -> None:
        if not self.storage_file.exists():
            return
        try:
            with open(self.storage_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    exp = AgentExperience.from_dict(item)
                    self._cache[exp.id] = exp
        except Exception as e:
            logger.warning("Failed to load experience store from %s: %s", self.storage_file, e)

    def _persist(self) -> None:
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            with open(self.storage_file, "w", encoding="utf-8") as f:
                json.dump([exp.to_dict() for exp in self._cache.values()], f, indent=2)
        except Exception as e:
            logger.error("Failed to persist experience store to %s: %s", self.storage_file, e)

    def put(self, experience: AgentExperience) -> AgentExperience:
        """
        SPEC §10.9: Redact and upsert experience by stable id.
        """
        # Redact any sensitive text before persistence
        clean_exp = AgentExperience(
            id=experience.id,
            source=experience.source,
            agent_id=experience.agent_id,
            entrypoint=experience.entrypoint,
            task_fingerprint=experience.task_fingerprint,
            task_summary=redact_text(experience.task_summary[:280]),
            tools_used=experience.tools_used,
            tool_sequence=experience.tool_sequence,
            outcome=experience.outcome,
            lesson=redact_text(experience.lesson),
            confidence=experience.confidence,
            reuse_hint=redact_text(experience.reuse_hint) if experience.reuse_hint else None,
            avoid_hint=redact_text(experience.avoid_hint) if experience.avoid_hint else None,
            error_class=redact_text(experience.error_class) if experience.error_class else None,
            tags=experience.tags,
            dismissed=experience.dismissed,
            created_at=experience.created_at,
        )
        self._cache[clean_exp.id] = clean_exp
        self._persist()
        return clean_exp

    def get(self, exp_id: str) -> Optional[AgentExperience]:
        return self._cache.get(exp_id)

    def list(self, limit: int = 50, include_dismissed: bool = False) -> List[AgentExperience]:
        results = [
            exp for exp in self._cache.values()
            if include_dismissed or not exp.dismissed
        ]
        results.sort(key=lambda x: x.created_at, reverse=True)
        return results[:limit]

    def query(self, task_fingerprint: str, limit: int = 5) -> List[AgentExperience]:
        """
        SPEC §10.9: Query scored by fingerprint and keyword overlap.
        """
        if not task_fingerprint:
            return self.list(limit=limit)

        query_tokens = set(re.findall(r"\w+", task_fingerprint.lower()))
        scored: List[tuple[float, AgentExperience]] = []

        for exp in self._cache.values():
            if exp.dismissed:
                continue
            score = 0.0
            if exp.task_fingerprint and exp.task_fingerprint.lower() == task_fingerprint.lower():
                score += 3.0

            target_tokens = set(re.findall(r"\w+", (exp.task_summary + " " + exp.lesson).lower()))
            if query_tokens and target_tokens:
                overlap = len(query_tokens.intersection(target_tokens))
                score += float(overlap) / max(1, len(query_tokens))

            # Include base confidence
            total_score = score + exp.confidence
            if score > 0 or not query_tokens:
                scored.append((total_score, exp))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [pair[1] for pair in scored[:limit]]


class AgentExperienceCaptureHook:
    """
    SPEC §10.9: PostTurnHook extracting up to three candidate experiences.
    """

    def __init__(self, store: ExperienceStore):
        self.store = store

    def extract_candidates(self, turn_context: Dict[str, Any]) -> List[AgentExperience]:
        """
        SPEC §10.9: Extract up to three candidate experiences from turn context:
        1. Successful multi-tool sequence (>= 2 successful calls -> Success, conf 0.72)
        2. Repeated failure (any tool failed >= 2 times -> Failure, conf 0.68)
        3. Partial success (failure followed by later success -> Partial, conf 0.62)
        """
        tool_calls: List[Dict[str, Any]] = turn_context.get("tool_calls", [])
        if not tool_calls:
            return []

        task_summary = (turn_context.get("task_summary") or "")[:280]
        task_fingerprint = str(turn_context.get("task_fingerprint") or "")
        agent_id = str(turn_context.get("agent_id") or "locus-agent")
        entrypoint = str(turn_context.get("entrypoint") or "tool_loop")

        candidates: List[AgentExperience] = []
        seq = [str(call.get("name", "unknown")) for call in tool_calls]
        tools_used = list(dict.fromkeys(seq))

        # Check success/error status per call
        success_indices = [
            i for i, call in enumerate(tool_calls)
            if call.get("status") in ("success", "ok", 0, None)
        ]
        error_indices = [
            i for i, call in enumerate(tool_calls)
            if call.get("status") in ("error", "failed", "failure")
        ]

        # 1. Successful multi-tool sequence (>= 2 successful calls)
        if len(success_indices) >= 2:
            succ_seq = [seq[i] for i in success_indices]
            seq_str = " -> ".join(succ_seq)
            outcome = "Success"
            exp_id = stable_experience_id(task_summary, succ_seq, outcome)
            c1 = AgentExperience(
                id=exp_id,
                source="ToolLoop",
                agent_id=agent_id,
                entrypoint=entrypoint,
                task_fingerprint=task_fingerprint,
                task_summary=task_summary,
                tools_used=list(dict.fromkeys(succ_seq)),
                tool_sequence=succ_seq,
                outcome=outcome,
                lesson=f"the successful tool sequence was {seq_str}",
                reuse_hint=f"reuse {seq_str} when the task resembles {task_summary}",
                confidence=0.72,
                tags=["multi-tool", "success"],
            )
            candidates.append(c1)

        # 2. Repeated failure (any tool that failed >= 2 times in one turn)
        fail_counts: Dict[str, int] = {}
        error_class: Optional[str] = None
        for i in error_indices:
            name = seq[i]
            fail_counts[name] = fail_counts.get(name, 0) + 1
            if not error_class:
                err_msg = str(tool_calls[i].get("error") or tool_calls[i].get("output_summary") or "")
                error_class = err_msg[:60] if err_msg else "tool_execution_failed"

        for tool_name, count in fail_counts.items():
            if count >= 2:
                outcome = "Failure"
                fail_seq = [tool_name] * count
                exp_id = stable_experience_id(task_summary, fail_seq, outcome)
                c2 = AgentExperience(
                    id=exp_id,
                    source="ToolLoop",
                    agent_id=agent_id,
                    entrypoint=entrypoint,
                    task_fingerprint=task_fingerprint,
                    task_summary=task_summary,
                    tools_used=[tool_name],
                    tool_sequence=fail_seq,
                    outcome=outcome,
                    error_class=error_class or "repeated_failure",
                    lesson=f"tool {tool_name} repeatedly failed {count} times",
                    avoid_hint=f"avoid retrying {tool_name} repeatedly without changing inputs",
                    confidence=0.68,
                    tags=["repeated-failure", "tool-failure"],
                )
                candidates.append(c2)

        # 3. Partial success (a failure followed by a later success)
        if error_indices and success_indices and min(error_indices) < max(success_indices):
            seq_str = " -> ".join(seq)
            outcome = "Partial"
            exp_id = stable_experience_id(task_summary, seq, outcome)
            c3 = AgentExperience(
                id=exp_id,
                source="ToolLoop",
                agent_id=agent_id,
                entrypoint=entrypoint,
                task_fingerprint=task_fingerprint,
                task_summary=task_summary,
                tools_used=tools_used,
                tool_sequence=seq,
                outcome=outcome,
                lesson=f"the task recovered by continuing with {seq_str}",
                reuse_hint=f"continue with {seq_str} to recover from early tool failure",
                confidence=0.62,
                tags=["recovery", "partial-success"],
            )
            candidates.append(c3)

        return candidates

    def on_turn_complete(self, turn_context: Dict[str, Any]) -> List[AgentExperience]:
        """
        Extracts candidates and saves them into the store.
        """
        candidates = self.extract_candidates(turn_context)
        stored: List[AgentExperience] = []
        for c in candidates:
            stored.append(self.store.put(c))
        return stored


def render_experience_hits(hits: List[AgentExperience], max_bytes: int = 2000) -> str:
    """
    SPEC §10.9: Render relevant hits as a compact, byte-capped markdown block.
    """
    if not hits:
        return ""
    lines = ["## Relevant Operating Experience"]
    current_bytes = len(lines[0].encode("utf-8")) + 1

    for i, hit in enumerate(hits, 1):
        seq_str = " -> ".join(hit.tool_sequence)
        parts = [f"{i}. {hit.outcome.lower()} sequence: {seq_str}"]
        if hit.lesson:
            parts.append(f"lesson: {hit.lesson}")
        if hit.reuse_hint:
            parts.append(f"reuse: {hit.reuse_hint}")
        if hit.avoid_hint:
            parts.append(f"avoid: {hit.avoid_hint}")
        line = " | ".join(parts)
        line_bytes = len(line.encode("utf-8")) + 1
        if current_bytes + line_bytes > max_bytes:
            break
        lines.append(line)
        current_bytes += line_bytes

    return "\n".join(lines)


def prepend_experience_block(message: str, hits: List[AgentExperience], max_bytes: int = 2000) -> str:
    """
    SPEC §10.9: Prepend experience block before user message.
    """
    block = render_experience_hits(hits, max_bytes=max_bytes)
    if not block:
        return message
    if not message:
        return block
    return f"{block}\n\n{message}"
