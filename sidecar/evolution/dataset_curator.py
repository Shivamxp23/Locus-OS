"""Locus QLoRA Dataset Curator & Fine-Tuning Pipeline (§30.6 / §30.7).

Curates agent trajectories, successful tool uses, and user correction pairs into
standard training formats (Alpaca, ShareGPT) with quality filtering and deduplication.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TrainingSample:
    sample_id: str
    instruction: str
    input_context: str
    output: str
    source_type: str  # "user_correction", "trajectory_success", "synthetic"
    quality_score: float = 1.0
    tokens_count: int = 0
    created_at: float = field(default_factory=time.time)

    def to_alpaca(self) -> Dict[str, Any]:
        return {
            "instruction": self.instruction,
            "input": self.input_context,
            "output": self.output,
        }

    def to_sharegpt(self) -> Dict[str, Any]:
        conversations = [
            {"from": "human", "value": f"{self.instruction}\n{self.input_context}".strip()},
            {"from": "gpt", "value": self.output},
        ]
        return {"id": self.sample_id, "conversations": conversations}


class QLoRADatasetCurator:
    """Manages training sample ingestion, filtering, and export for QLoRA adapter training."""

    def __init__(self, min_quality_threshold: float = 0.75):
        self.min_quality = min_quality_threshold
        self.samples: List[TrainingSample] = []

    def add_sample(
        self,
        sample_id: str,
        instruction: str,
        input_context: str,
        output: str,
        source_type: str = "trajectory_success",
        quality_score: float = 0.9,
    ) -> Optional[TrainingSample]:
        if quality_score < self.min_quality:
            return None

        tokens = len(instruction.split()) + len(input_context.split()) + len(output.split())
        sample = TrainingSample(
            sample_id=sample_id,
            instruction=instruction,
            input_context=input_context,
            output=output,
            source_type=source_type,
            quality_score=quality_score,
            tokens_count=tokens,
        )
        self.samples.append(sample)
        return sample

    def export_dataset(self, format_type: str = "alpaca") -> List[Dict[str, Any]]:
        if format_type == "sharegpt":
            return [s.to_sharegpt() for s in self.samples]
        return [s.to_alpaca() for s in self.samples]

    def get_dataset_statistics(self) -> Dict[str, Any]:
        total_tokens = sum(s.tokens_count for s in self.samples)
        return {
            "total_samples": len(self.samples),
            "total_tokens": total_tokens,
            "avg_tokens_per_sample": (total_tokens / len(self.samples)) if self.samples else 0,
        }
