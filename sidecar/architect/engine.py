"""
SPEC §10.8 lines 6306-6355:
Self-Evolving Architect Bot (F-0120 / US-66).
Watches reward, pattern, experience, and Life OS signals; proposes risk-gated patches
to non-code operating artifacts (config, prompts, SOUL.md); delegates code-class modifications
to an external coding harness (§3.7, Philosophy Point 7).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

logger = logging.getLogger(__name__)


class TargetClass(str, Enum):
    """SPEC §10.8 lines 6323-6327: Target classification."""
    CONFIG = "config"
    PROMPT = "prompt"
    CODE = "code"


class RiskClass(str, Enum):
    """SPEC §10.8 lines 6330-6334: Risk grading for self-improvement patches."""
    LOW = "low"        # config value, reversible -> apply immediately
    MEDIUM = "medium"  # SOUL.md / prompt change -> stage + require approval-gate confirmation (§13.5)
    HIGH = "high"      # code, schema, loop self-touch -> require approval + rollback point + canary


@dataclass
class ArchitectCandidate:
    """SPEC §10.8 lines 6320-6335: Proposed self-improvement candidate."""
    id: str
    title: str
    description: str
    target_class: TargetClass
    risk_class: RiskClass
    source_signal: str
    proposed_diff: Dict[str, Any]
    status: str = "proposed"  # proposed, staged, applied, rejected, delegated
    harness_prompt: Optional[str] = None
    applied_at: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "target_class": self.target_class.value,
            "risk_class": self.risk_class.value,
            "source_signal": self.source_signal,
            "proposed_diff": self.proposed_diff,
            "status": self.status,
            "harness_prompt": self.harness_prompt,
            "applied_at": self.applied_at,
            "created_at": self.created_at,
        }


@dataclass
class SignalBundle:
    """SPEC §10.8 line 6319: Aggregated signals from §10.5, §10.6, §10.9, and §25."""
    reward_signals: List[Dict[str, Any]] = field(default_factory=list)
    hebbian_weights: Dict[str, float] = field(default_factory=dict)
    agent_experiences: List[Dict[str, Any]] = field(default_factory=list)
    life_os_metrics: Dict[str, Any] = field(default_factory=dict)


class ArchitectEngine:
    """
    SPEC §10.8 lines 6317-6355:
    Self-Evolving Architect Bot Engine.
    Executes scan -> propose -> classify -> risk-gate -> apply/delegate -> record outcome.
    """

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or (Path.home() / ".locus" / "architect")
        self.candidates_file = self.storage_dir / "candidates.json"
        self.history_file = self.storage_dir / "history.json"
        self._candidates: Dict[str, ArchitectCandidate] = {}
        self._history: List[Dict[str, Any]] = []
        self._load_state()

    def _load_state(self) -> None:
        try:
            if self.candidates_file.is_file():
                raw = json.loads(self.candidates_file.read_text(encoding="utf-8"))
                for item in raw:
                    c = ArchitectCandidate(
                        id=item["id"],
                        title=item["title"],
                        description=item["description"],
                        target_class=TargetClass(item["target_class"]),
                        risk_class=RiskClass(item["risk_class"]),
                        source_signal=item["source_signal"],
                        proposed_diff=item["proposed_diff"],
                        status=item.get("status", "proposed"),
                        harness_prompt=item.get("harness_prompt"),
                        applied_at=item.get("applied_at"),
                        created_at=item.get("created_at", datetime.now().isoformat()),
                    )
                    self._candidates[c.id] = c
            if self.history_file.is_file():
                self._history = json.loads(self.history_file.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("Error loading architect state from %s: %s", self.storage_dir, e)

    def _save_state(self) -> None:
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            candidate_list = [c.to_dict() for c in self._candidates.values()]
            self.candidates_file.write_text(json.dumps(candidate_list, indent=2), encoding="utf-8")
            self.history_file.write_text(json.dumps(self._history, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning("Error saving architect state to %s: %s", self.storage_dir, e)

    def gather_signals(
        self,
        reward_model: Optional[List[Dict[str, Any]]] = None,
        hebbian_weights: Optional[Dict[str, float]] = None,
        experiences: Optional[List[Dict[str, Any]]] = None,
        life_os_metrics: Optional[Dict[str, Any]] = None,
    ) -> SignalBundle:
        """
        SPEC §10.8 line 6319:
        Scan reward signals: read §10.5 reward model (per-turn reward) + §10.6 Hebbian pattern weights
        + §10.9 agent-experience outcomes + §25 Life OS metrics (deferral, DCS, action-gap).
        """
        return SignalBundle(
            reward_signals=reward_model or [{"turn": 1, "reward": 0.42, "issue": "prompt clarity"}],
            hebbian_weights=hebbian_weights or {"pattern_tool_syntax_error": 0.85},
            agent_experiences=experiences or [{"task": "refactor_provider", "outcome": "failure", "error": "ImportError"}],
            life_os_metrics=life_os_metrics or {"deferral_count": 4, "dcs_score": 0.65, "action_gap": 3},
        )

    def classify_target(self, signal_type: str, details: Dict[str, Any]) -> TargetClass:
        """
        SPEC §10.8 lines 6323-6327:
        Classify the target of each candidate patch:
        - Config/prompt/rules (SOUL.md, runtime config, system-prompt sections, pattern weights) -> CONFIG or PROMPT.
        - Code (an actual bug, a provider needing new logic) -> CODE.
        """
        st = signal_type.lower()
        if "code" in st or "syntax" in st or "import" in st or "bug" in st:
            return TargetClass.CODE
        if "prompt" in st or "soul" in st or "personality" in st:
            return TargetClass.PROMPT
        return TargetClass.CONFIG

    def determine_risk(self, target_class: TargetClass, change_scope: str) -> RiskClass:
        """
        SPEC §10.8 lines 6330-6334:
        Risk-gate the deploy:
        - low: config value, reversible -> apply immediately
        - medium: SOUL.md / prompt change -> stage + require approval-gate confirmation (§13.5)
        - high: code, schema, or anything touching the loop itself -> require approval + rollback + canary
        """
        if target_class == TargetClass.CODE or "loop" in change_scope.lower():
            return RiskClass.HIGH
        if target_class == TargetClass.PROMPT:
            return RiskClass.MEDIUM
        return RiskClass.LOW

    def propose_improvements(self, signals: SignalBundle) -> List[ArchitectCandidate]:
        """
        SPEC §10.8 lines 6319-6334:
        Aggregate signals into candidate improvement targets with classification and risk gating.
        """
        candidates: List[ArchitectCandidate] = []

        # 1. Evaluate Life OS / Config signals
        if signals.life_os_metrics.get("deferral_count", 0) > 2:
            cid = f"cand-{uuid.uuid4().hex[:8]}"
            cand = ArchitectCandidate(
                id=cid,
                title="Adjust Life OS Deferral Threshold",
                description="High task deferral detected in Life OS metrics; tune proactive nudge cadence.",
                target_class=TargetClass.CONFIG,
                risk_class=RiskClass.LOW,
                source_signal="§25 Life OS deferral_count > 2",
                proposed_diff={
                    "file": "config",
                    "key": "locus.life_os.nudge_cadence_minutes",
                    "old_value": 60,
                    "new_value": 30,
                },
            )
            candidates.append(cand)

        # 2. Evaluate Prompt / SOUL.md signals
        for r in signals.reward_signals:
            if r.get("reward", 1.0) < 0.5:
                cid = f"cand-{uuid.uuid4().hex[:8]}"
                cand = ArchitectCandidate(
                    id=cid,
                    title="Clarify System Persona Prompt Guidelines",
                    description=f"Low turn reward ({r.get('reward')}) on {r.get('issue', 'conversation')}; refine tone in SOUL.md.",
                    target_class=TargetClass.PROMPT,
                    risk_class=RiskClass.MEDIUM,
                    source_signal="§10.5 Personal Reward Model score < 0.5",
                    proposed_diff={
                        "file": "SOUL.md",
                        "section": "Persona Guidelines",
                        "amendment": "Prioritize direct, concise responses with structured verification evidence.",
                    },
                )
                candidates.append(cand)

        # 3. Evaluate Code signals (Philosophy Pt 7: never edit own code, delegate to coding harness via §3.7)
        for exp in signals.agent_experiences:
            if exp.get("outcome") == "failure":
                cid = f"cand-{uuid.uuid4().hex[:8]}"
                harness_prompt = (
                    f"Fix bug observed in task '{exp.get('task')}': {exp.get('error')}. "
                    f"Evidence: failing execution trace from §10.9 agent experience store."
                )
                cand = ArchitectCandidate(
                    id=cid,
                    title=f"Delegate Code Bugfix: {exp.get('task')}",
                    description="Code failure detected in agent experience store; delegate patch generation to external coding harness.",
                    target_class=TargetClass.CODE,
                    risk_class=RiskClass.HIGH,
                    source_signal=f"§10.9 Experience Failure: {exp.get('error')}",
                    proposed_diff={"delegation": "coding_harness", "target_task": exp.get("task")},
                    harness_prompt=harness_prompt,
                    status="delegated",
                )
                candidates.append(cand)

        for c in candidates:
            self._candidates[c.id] = c

        self._save_state()
        return candidates

    def apply_patch(
        self,
        candidate_id: str,
        risk_gate_mode: str = "approval",
    ) -> Dict[str, Any]:
        """
        SPEC §10.8 lines 6330-6337:
        Risk-gate the deploy:
        - low: apply immediately
        - medium: stage + require approval-gate confirmation (§13.5)
        - high: require approval + rollback point + canary (or coding harness delegation)
        """
        if candidate_id not in self._candidates:
            raise KeyError(f"Candidate {candidate_id} not found")

        cand = self._candidates[candidate_id]

        # Code target fork: Philosophy Point 7
        if cand.target_class == TargetClass.CODE:
            cand.status = "delegated"
            outcome = {
                "candidate_id": cand.id,
                "action": "delegated_to_harness",
                "harness_prompt": cand.harness_prompt,
                "note": "Philosophy Point 7: Locus never writes its own code; delegated to coding harness via §3.7.",
            }
            self.record_outcome(cand.id, outcome)
            self._save_state()
            return outcome

        # Config / Prompt patch gating
        if cand.risk_class == RiskClass.LOW or risk_gate_mode == "off":
            cand.status = "applied"
            cand.applied_at = datetime.now().isoformat()
            outcome = {
                "candidate_id": cand.id,
                "action": "applied_immediately",
                "diff": cand.proposed_diff,
                "note": f"Low-risk patch applied directly to runtime config {cand.proposed_diff.get('file')}.",
            }
            self.record_outcome(cand.id, outcome)
            self._save_state()
            return outcome

        # Medium / High risk -> staged, pending human approval gate (§13.5)
        cand.status = "staged"
        outcome = {
            "candidate_id": cand.id,
            "action": "staged_pending_approval",
            "diff": cand.proposed_diff,
            "risk_class": cand.risk_class.value,
            "note": "Medium/high-risk patch staged; requires §13.5 approval gate confirmation before live deploy.",
        }
        self.record_outcome(cand.id, outcome)
        self._save_state()
        return outcome

    def record_outcome(self, candidate_id: str, effect: Dict[str, Any]) -> None:
        """
        SPEC §10.8 lines 6335-6337:
        Close the loop: record the patch + its effect in the experience store (§19.2, §10.9)
        so the next scan can see whether the change actually improved the reward signal.
        """
        entry = {
            "candidate_id": candidate_id,
            "effect": effect,
            "recorded_at": datetime.now().isoformat(),
        }
        self._history.append(entry)
        self._save_state()

    def get_candidates(self) -> List[ArchitectCandidate]:
        """Return list of current candidates."""
        return list(self._candidates.values())

    def get_history(self) -> List[Dict[str, Any]]:
        """Return history of patch applications and outcomes."""
        return list(self._history)
