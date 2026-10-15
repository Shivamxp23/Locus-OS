"""Locus Auxiliary LLM Client (§29.2).

Dedicated lightweight LLM client executing background and sidecar tasks
(title generation, tag extraction, note cleanup, error diagnosis, prompt summarization)
without contaminating primary conversation turns or exhausting expensive model quotas.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class AuxiliaryTaskType(str, Enum):
    TITLE_GENERATION = "title_generation"
    TAG_EXTRACTION = "tag_extraction"
    NOTE_PARSING = "note_parsing"
    ERROR_CLASSIFICATION = "error_classification"
    CONTEXT_SUMMARY = "context_summary"
    INTENT_ROUTING = "intent_routing"


@dataclass
class AuxiliaryLLMResponse:
    task_type: AuxiliaryTaskType
    content: str
    token_usage: int
    duration_ms: float
    model: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_type": self.task_type.value,
            "content": self.content,
            "token_usage": self.token_usage,
            "duration_ms": self.duration_ms,
            "model": self.model,
            "metadata": self.metadata,
        }


class AuxiliaryLLMClient:
    """Dispatches low-latency secondary prompts to budget-friendly models."""

    def __init__(self, default_model: str = "mock-small-fast", max_tokens: int = 500):
        self.default_model = default_model
        self.max_tokens = max_tokens
        self.call_history: List[AuxiliaryLLMResponse] = []

    def execute_task(
        self,
        task_type: AuxiliaryTaskType,
        prompt: str,
        system_instruction: Optional[str] = None,
        override_model: Optional[str] = None,
    ) -> AuxiliaryLLMResponse:
        start_time = time.time()
        model = override_model or self.default_model

        # Deterministic simulated completion based on task type
        if task_type == AuxiliaryTaskType.TITLE_GENERATION:
            content = f"Title: {prompt[:30].strip()}..."
        elif task_type == AuxiliaryTaskType.TAG_EXTRACTION:
            content = "#project #architecture #locus"
        elif task_type == AuxiliaryTaskType.CONTEXT_SUMMARY:
            content = f"Summary: Extracted key points from input context ({len(prompt)} chars)."
        else:
            content = f"Auxiliary output for {task_type.value}: OK"

        duration = (time.time() - start_time) * 1000.0
        resp = AuxiliaryLLMResponse(
            task_type=task_type,
            content=content,
            token_usage=min(self.max_tokens, len(prompt.split()) + len(content.split())),
            duration_ms=max(1.0, duration),
            model=model,
            metadata={"prompt_preview": prompt[:50]},
        )
        self.call_history.append(resp)
        return resp

    def get_total_auxiliary_tokens(self) -> int:
        return sum(r.token_usage for r in self.call_history)
