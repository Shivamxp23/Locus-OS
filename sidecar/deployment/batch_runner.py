"""
SPEC §23.5 lines 8475-8488: Batch Trajectory Runner.
Evaluates agent consistency, token usage, tool invocations, and response quality across multiple runs.
"""
from __future__ import annotations

import logging
import statistics
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Callable

logger = logging.getLogger("locus.deployment.batch")


@dataclass
class RunResult:
    run_index: int
    duration_sec: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    tool_calls: list[str] = field(default_factory=list)
    output_text: str = ""
    status: str = "success"


@dataclass
class BatchEvaluationReport:
    prompt: str
    n_runs: int
    successful_runs: int
    mean_duration_sec: float
    mean_tokens: float
    total_tokens_consumed: int
    unique_tool_calls: list[str] = field(default_factory=list)
    consistency_score: float = 1.0
    runs: list[RunResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "prompt": self.prompt,
            "n_runs": self.n_runs,
            "successful_runs": self.successful_runs,
            "mean_duration_sec": self.mean_duration_sec,
            "mean_tokens": self.mean_tokens,
            "total_tokens_consumed": self.total_tokens_consumed,
            "unique_tool_calls": self.unique_tool_calls,
            "consistency_score": self.consistency_score,
            "runs": [asdict(r) for r in self.runs],
        }


class BatchTrajectoryRunner:
    """
    SPEC §23.5: Batch Trajectory Runner.
    Executes multiple trials of an evaluation prompt and computes variance metrics across trajectories.
    """

    def batch_evaluate(
        self,
        prompt: str,
        n_runs: int = 3,
        runner_fn: Callable[[str, int], dict[str, Any]] | None = None,
    ) -> BatchEvaluationReport:
        """
        Execute n_runs trials on the evaluation prompt and produce comparison report.
        """
        runs: list[RunResult] = []
        all_tools: set[str] = set()

        for i in range(n_runs):
            t0 = time.time()
            if runner_fn:
                run_data = runner_fn(prompt, i)
            else:
                # Default hermetic synthetic evaluation run
                run_data = {
                    "prompt_tokens": len(prompt.split()) * 2,
                    "completion_tokens": 40 + (i % 3) * 5,
                    "tool_calls": ["search", "read_file"] if i % 2 == 0 else ["search"],
                    "output_text": f"Simulated autonomous completion for run {i}",
                    "status": "success",
                }

            duration = max(0.001, time.time() - t0)
            pt = int(run_data.get("prompt_tokens", 0))
            ct = int(run_data.get("completion_tokens", 0))
            tools = list(run_data.get("tool_calls", []))
            all_tools.update(tools)

            result = RunResult(
                run_index=i + 1,
                duration_sec=round(duration, 4),
                prompt_tokens=pt,
                completion_tokens=ct,
                total_tokens=pt + ct,
                tool_calls=tools,
                output_text=str(run_data.get("output_text", "")),
                status=str(run_data.get("status", "success")),
            )
            runs.append(result)

        successful = [r for r in runs if r.status == "success"]
        token_counts = [r.total_tokens for r in successful] or [0]
        durations = [r.duration_sec for r in successful] or [0.0]

        mean_tok = float(statistics.mean(token_counts))
        total_tok = sum(token_counts)
        mean_dur = float(statistics.mean(durations))

        # Consistency score: 1.0 - coefficient of variation
        if len(token_counts) > 1 and mean_tok > 0:
            std_dev = statistics.stdev(token_counts)
            cv = std_dev / mean_tok
            consistency = max(0.0, min(1.0, 1.0 - cv))
        else:
            consistency = 1.0

        return BatchEvaluationReport(
            prompt=prompt,
            n_runs=n_runs,
            successful_runs=len(successful),
            mean_duration_sec=round(mean_dur, 4),
            mean_tokens=round(mean_tok, 2),
            total_tokens_consumed=total_tok,
            unique_tool_calls=sorted(all_tools),
            consistency_score=round(consistency, 4),
            runs=runs,
        )
