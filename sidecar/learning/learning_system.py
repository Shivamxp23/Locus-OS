"""
SPEC §1.7, §10.1, §10.3, §10.5, §10.6-10.7: Learning / Profiling / Reward Model Subsystem (F-0035).
Implements ambient user profiling, stability detection, tool usage tracking,
logistic/heuristic reward model scoring, Hebbian edge weighting with STDP, and multi-horizon pattern engine.
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import sidecar.config as config
from sidecar.providers.learning import (
    BaseLearningProvider,
    LearningCandidate,
    PatternHorizon,
    PatternRecord,
    RewardSignal,
    StableFacet,
    ToolUsageRecord,
)

logger = logging.getLogger(__name__)

STABILITY_THRESHOLD = 0.7
PROACTIVE_REWARD_THRESHOLD = 0.6


class UnifiedLearningProvider(BaseLearningProvider):
    """
    Unified concrete implementation for Learning, User Profiling, and Reward Modeling.
    Provides stability detection over rolling windows, profile generation, tool tracking,
    reward scoring (>= 0.6 threshold), Hebbian edge plasticity with STDP, and 5-horizon patterns.
    """

    _shared_candidates: List[LearningCandidate] = []
    _shared_stable_facets: Dict[str, StableFacet] = {}
    _shared_tool_usage: List[ToolUsageRecord] = []
    _shared_reward_signals: List[RewardSignal] = []
    _shared_edge_weights: Dict[str, float] = {}
    _shared_patterns: Dict[str, PatternRecord] = {}
    _shared_lock = threading.RLock()

    def __init__(
        self,
        custom_config: Optional[Dict[str, Any]] = None,
        profile_path: Optional[Path] = None,
    ) -> None:
        self.custom_config = custom_config or {}
        if profile_path:
            self.profile_path = Path(profile_path).resolve()
        else:
            self.profile_path = config.get_locus_home() / "PROFILE.md"

        self._candidates = self._shared_candidates
        self._stable_facets = self._shared_stable_facets
        self._tool_usage = self._shared_tool_usage
        self._reward_signals = self._shared_reward_signals
        self._edge_weights = self._shared_edge_weights
        self._patterns = self._shared_patterns
        self._lock = self._shared_lock

    def is_enabled(self) -> bool:
        """Check if learning/profiling/reward model is enabled."""
        if "locus.learning_profiling_reward_model.enabled" in self.custom_config:
            return bool(self.custom_config["locus.learning_profiling_reward_model.enabled"])
        val = config.get("locus.learning_profiling_reward_model.enabled")
        if val is not None and not config.is_enabled("locus.learning_profiling_reward_model.enabled"):
            return False
        return True

    def record_candidate(self, candidate: LearningCandidate) -> None:
        """SPEC §10.3 line 2935: Push candidate into learning buffer."""
        if not self.is_enabled():
            return
        with self._lock:
            self._candidates.append(candidate)

    def check_stability(
        self, window_seconds: float = 1800.0, threshold: float = STABILITY_THRESHOLD
    ) -> List[StableFacet]:
        """
        SPEC §10.3 lines 2943-2957:
        Every 30 minutes, check if learning buffer has converged over recent window.
        If recent.length < 3: return (not enough data).
        Aggregates by facet class, calculates consistency score, and stabilizes consistent facets.
        """
        if not self.is_enabled():
            return []

        now = time.time()
        with self._lock:
            recent = [c for c in self._candidates if (now - c.timestamp) <= window_seconds]
            if len(recent) < 3:
                return []

            # Group candidates by facet class
            grouped: Dict[str, List[LearningCandidate]] = {}
            for c in recent:
                grouped.setdefault(c.facet_class, []).append(c)

            stabilized: List[StableFacet] = []
            for facet_class, items in grouped.items():
                if len(items) < 2:
                    continue

                # Count value frequencies to measure consistency
                counts: Dict[str, int] = {}
                for it in items:
                    val_str = str(it.value) if it.value is not None else str(it.evidence.get("snippet", ""))
                    counts[val_str] = counts.get(val_str, 0) + 1

                most_common_val, max_count = max(counts.items(), key=lambda kv: kv[1])
                consistency = max_count / float(len(items))

                if consistency >= threshold:
                    facet_key = f"{facet_class}:{most_common_val[:32]}"
                    stable = StableFacet(
                        facet_class=facet_class,
                        key=facet_key,
                        value=most_common_val,
                        confidence=consistency,
                        evidence_count=len(items),
                        last_updated=now,
                    )
                    self._stable_facets[facet_key] = stable
                    stabilized.append(stable)

        if stabilized:
            # Update PROFILE.md with new stable preferences
            self._write_profile_document()

        return stabilized

    def generate_profile_markdown(self) -> str:
        """
        SPEC §10.3 lines 2971-2977:
        Compile stable facets into a rendered PROFILE.md document.
        """
        with self._lock:
            facets = list(self._stable_facets.values())

        lines = [
            "# Locus User Profile",
            "<!-- Generated automatically from stable user behavioral facets -->",
            f"Last Updated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]

        if not facets:
            lines.append("_No stable profile facets established yet._")
            return "\n".join(lines)

        by_class: Dict[str, List[StableFacet]] = {}
        for f in facets:
            by_class.setdefault(f.facet_class, []).append(f)

        for facet_class, items in sorted(by_class.items()):
            lines.append(f"## {facet_class.capitalize()} Facets")
            for item in sorted(items, key=lambda x: -x.confidence):
                lines.append(f"- **{item.value}** (confidence: {item.confidence:.2f}, based on {item.evidence_count} events)")
            lines.append("")

        return "\n".join(lines).strip()

    def _write_profile_document(self) -> None:
        """Persist generated profile to disk."""
        try:
            content = self.generate_profile_markdown()
            self.profile_path.parent.mkdir(parents=True, exist_ok=True)
            self.profile_path.write_text(content, encoding="utf-8")
        except Exception as exc:
            logger.warning(f"Could not persist PROFILE.md: {exc}")

    def record_tool_usage(
        self, tool_name: str, args: Any, success: bool, duration_ms: float
    ) -> ToolUsageRecord:
        """
        SPEC §10.3 lines 2959-2968: Track every tool invocation (name, args_hash, success, duration).
        """
        args_str = json.dumps(args, sort_keys=True, default=str)
        args_hash = hashlib.sha256(args_str.encode("utf-8")).hexdigest()[:16]
        rec = ToolUsageRecord(
            tool_name=tool_name,
            args_hash=args_hash,
            success=success,
            duration_ms=duration_ms,
            timestamp=time.time(),
        )
        if self.is_enabled():
            with self._lock:
                self._tool_usage.append(rec)
        return rec

    def record_reward_signal(self, features: Dict[str, Any], label: int) -> RewardSignal:
        """
        SPEC §10.5 lines 6210-6228: Record response features with 👍 (1) or 👎 (0) label.
        """
        sig = RewardSignal(
            features=features,
            label=1 if label > 0 else 0,
            created_at=time.time(),
        )
        if self.is_enabled():
            with self._lock:
                self._reward_signals.append(sig)
        return sig

    def score_thought(self, features: Dict[str, Any]) -> float:
        """
        SPEC §10.5 lines 6230-6249:
        Calculate P(thumbs_up) based on features.
        Threshold: >= 0.6 for proactive output delivery.
        """
        if not self.is_enabled():
            return 0.5

        with self._lock:
            signals = list(self._reward_signals)

        # Baseline probability with feature weighting
        dcs = float(features.get("dcs_at_response", 70.0)) / 100.0
        confidence = float(features.get("confidence", 0.7))
        was_proactive = bool(features.get("was_proactive", False))
        tokens = float(features.get("context_forge_tokens_used", 500))

        # Weighting formula calibrated to reward signals if present
        if len(signals) >= 5:
            positive_rate = sum(s.label for s in signals) / float(len(signals))
            base_prior = positive_rate
        else:
            base_prior = 0.65

        score = (
            base_prior * 0.4
            + dcs * 0.25
            + confidence * 0.25
            + (0.1 if was_proactive and dcs > 0.6 else -0.05 if was_proactive else 0.05)
            - (0.05 if tokens > 3500 else 0.0)
        )
        return max(0.0, min(1.0, round(score, 3)))

    def update_edge_weight(
        self,
        edge_id: str,
        feedback: Optional[str] = None,
        response_time_ms: Optional[float] = None,
    ) -> float:
        """
        SPEC §10.6 lines 6254-6278:
        Hebbian Pathway Weighting & STDP:
        - Access: weight += 0.1
        - Feedback: positive * 1.3, negative * 0.7
        - STDP: < 120,000ms * 1.5, < 600,000ms * 1.2
        """
        if not self.is_enabled():
            return 1.0

        with self._lock:
            current_weight = self._edge_weights.get(edge_id, 1.0)

            # Access reinforcement
            current_weight += 0.1

            # User feedback modulation
            if feedback:
                fb_lower = feedback.strip().lower()
                if fb_lower in ("positive", "thumbs_up", "like"):
                    current_weight *= 1.3
                elif fb_lower in ("negative", "thumbs_down", "dislike"):
                    current_weight *= 0.7

            # STDP (Spike-Timing Dependent Plasticity)
            if response_time_ms is not None:
                if response_time_ms < 120000:  # < 2 min
                    current_weight *= 1.5
                elif response_time_ms < 600000:  # < 10 min
                    current_weight *= 1.2

            updated = round(current_weight, 3)
            self._edge_weights[edge_id] = updated
            return updated

    def apply_weekly_decay(self, decay_rate: float = 0.95) -> None:
        """
        SPEC §10.6 line 6263: Weekly decay: edge.weight *= 0.95 (5% weekly decay).
        """
        if not self.is_enabled():
            return
        with self._lock:
            for edge_id in list(self._edge_weights.keys()):
                self._edge_weights[edge_id] = round(self._edge_weights[edge_id] * decay_rate, 3)

    def detect_patterns(self) -> List[PatternRecord]:
        """
        SPEC §10.7 lines 6281-6305:
        Multi-horizon pattern engine across H1 (6h) to H5 (all-time).
        Promotion rule:
        If pattern.confidence > 0.75 AND pattern.count > 2 -> promoted to next horizon.
        """
        if not self.is_enabled():
            return []

        now = time.time()
        horizons_sec = {
            PatternHorizon.H1_6_HOURS: 6 * 3600,
            PatternHorizon.H2_24_HOURS: 24 * 3600,
            PatternHorizon.H3_7_DAYS: 7 * 86400,
            PatternHorizon.H4_30_DAYS: 30 * 86400,
            PatternHorizon.H5_ALL_TIME: 365 * 86400 * 10,
        }

        detected: List[PatternRecord] = []
        with self._lock:
            # Aggregate tool usages into pattern clusters
            for horizon, span in horizons_sec.items():
                horizon_usages = [u for u in self._tool_usage if (now - u.timestamp) <= span]
                tool_counts: Dict[str, int] = {}
                for u in horizon_usages:
                    tool_counts[u.tool_name] = tool_counts.get(u.tool_name, 0) + 1

                for tool_name, count in tool_counts.items():
                    if count >= 2:
                        conf = min(0.95, 0.6 + (count * 0.05))
                        rec = PatternRecord(
                            horizon=horizon,
                            pattern_type=f"frequent_tool:{tool_name}",
                            confidence=conf,
                            count=count,
                            details={"tool_name": tool_name, "period_seconds": span},
                        )
                        detected.append(rec)
                        self._patterns[f"{horizon.value}:{tool_name}"] = rec

            # Promotion rule: H1 -> H2 promotion if confidence > 0.75 and count > 2
            promoted = []
            for p in detected:
                if p.horizon == PatternHorizon.H1_6_HOURS and p.confidence > 0.75 and p.count > 2:
                    promoted_rec = PatternRecord(
                        horizon=PatternHorizon.H2_24_HOURS,
                        pattern_type=p.pattern_type,
                        confidence=p.confidence,
                        count=p.count,
                        details={"promoted_from": "H1_6h", **p.details},
                    )
                    promoted.append(promoted_rec)

            detected.extend(promoted)
            return detected
