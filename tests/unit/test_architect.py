"""
SPEC §10.8 lines 6306-6355:
Unit tests for Self-Evolving Architect Bot (F-0120 / US-66).
"""
from pathlib import Path
import pytest
from typing import Any, Dict, List, Optional

from sidecar.architect.engine import (
    ArchitectCandidate,
    ArchitectEngine,
    RiskClass,
    SignalBundle,
    TargetClass,
)
import sidecar.config as config
from sidecar.providers.architect import (
    BaseArchitectProvider,
    DefaultArchitectProvider,
)


def test_architect_gather_signals_and_propose_improvements(tmp_path: Path):
    """SPEC §10.8 line 6319: "1. Scan reward signals: read the §10.5 reward model (per-turn reward) + §10.6 Hebbian pattern weights + §10.9 agent-experience outcomes + §25 Life OS metrics (deferral, DCS, action-gap). Aggregate into candidate improvement targets." """
    engine = ArchitectEngine(storage_dir=tmp_path)
    signals = engine.gather_signals(
        reward_model=[{"turn": 2, "reward": 0.35, "issue": "prompt tone"}],
        hebbian_weights={"pattern_failing_tool": 0.9},
        experiences=[{"task": "parse_feed", "outcome": "failure", "error": "ValueError: malformed"}],
        life_os_metrics={"deferral_count": 5, "dcs_score": 0.5},
    )
    assert len(signals.reward_signals) == 1
    assert signals.life_os_metrics["deferral_count"] == 5

    candidates = engine.propose_improvements(signals)
    assert len(candidates) >= 3

    # Check that candidates span the target classes
    target_classes = {c.target_class for c in candidates}
    assert TargetClass.CONFIG in target_classes
    assert TargetClass.PROMPT in target_classes
    assert TargetClass.CODE in target_classes


def test_architect_classify_target_crucial_fork(tmp_path: Path):
    """SPEC §10.8 line 6323: "2. Classify the target of each candidate patch — this is the crucial fork: Config/prompt/rules (SOUL.md, config.yaml, system-prompt sections, pattern weights, blocklists) -> Locus edits them itself (these are non-code artifacts Locus owns)." """
    engine = ArchitectEngine(storage_dir=tmp_path)
    assert engine.classify_target("config_param", {}) == TargetClass.CONFIG
    assert engine.classify_target("soul_prompt_guidelines", {}) == TargetClass.PROMPT
    assert engine.classify_target("python_syntax_bug", {}) == TargetClass.CODE


def test_architect_code_delegation_philosophy_pt_7(tmp_path: Path):
    """SPEC §10.8 line 6326: "Code (an actual bug, a provider needing new logic) -> Locus delegates to a coding harness via §3.7 — it never writes its own code. This is philosophy point 7, applied to self-modification." """
    engine = ArchitectEngine(storage_dir=tmp_path)
    signals = engine.gather_signals(
        experiences=[{"task": "search_indexer", "outcome": "failure", "error": "IndexError: out of range"}],
        reward_model=[],
        life_os_metrics={"deferral_count": 0},
    )
    candidates = engine.propose_improvements(signals)
    code_cand = next(c for c in candidates if c.target_class == TargetClass.CODE)

    assert code_cand.harness_prompt is not None
    assert "search_indexer" in code_cand.harness_prompt
    assert "IndexError" in code_cand.harness_prompt

    outcome = engine.apply_patch(code_cand.id)
    assert outcome["action"] == "delegated_to_harness"
    assert "Philosophy Point 7" in outcome["note"]
    assert code_cand.status == "delegated"


def test_architect_risk_gated_deploy(tmp_path: Path):
    """SPEC §10.8 line 6330: "4. Risk-gate the deploy: each candidate carries a risk class. low (config value, reversible) -> apply immediately; medium (SOUL.md/prompt change) -> stage + require approval-gate confirmation (§13.5); high (code, schema, or anything touching the loop itself) -> require approval + a rollback point + a canary (apply to a staging copy first)." """
    engine = ArchitectEngine(storage_dir=tmp_path)
    signals = engine.gather_signals(
        reward_model=[{"turn": 1, "reward": 0.2, "issue": "unclear"}],
        life_os_metrics={"deferral_count": 4},
        experiences=[],
    )
    candidates = engine.propose_improvements(signals)

    # Low risk (config) applies immediately
    low_cand = next(c for c in candidates if c.risk_class == RiskClass.LOW)
    outcome_low = engine.apply_patch(low_cand.id, risk_gate_mode="approval")
    assert outcome_low["action"] == "applied_immediately"
    assert low_cand.status == "applied"

    # Medium risk (prompt) stages pending approval gate confirmation
    med_cand = next(c for c in candidates if c.risk_class == RiskClass.MEDIUM)
    outcome_med = engine.apply_patch(med_cand.id, risk_gate_mode="approval")
    assert outcome_med["action"] == "staged_pending_approval"
    assert med_cand.status == "staged"


def test_architect_close_the_loop_history(tmp_path: Path):
    """SPEC §10.8 line 6335: "5. Close the loop: record the patch + its effect in the trajectory/experience store (§19.2, §10.9) so the next scan can see whether the change actually improved the reward signal." """
    engine = ArchitectEngine(storage_dir=tmp_path)
    signals = engine.gather_signals(life_os_metrics={"deferral_count": 5})
    candidates = engine.propose_improvements(signals)
    c = candidates[0]

    engine.apply_patch(c.id)
    history = engine.get_history()
    assert len(history) >= 1
    assert history[-1]["candidate_id"] == c.id


def test_architect_provider_off_switch(tmp_path: Path, monkeypatch):
    """SPEC §10.8 line 6345: "Swappable / off state: locus.architect.enabled. Off -> Locus stops proposing self-changes entirely (it remains static, still fully functional)." """
    provider = DefaultArchitectProvider(storage_dir=tmp_path)

    monkeypatch.setattr(config, "get", lambda k: True)
    monkeypatch.setattr(config, "is_enabled", lambda k: True)
    assert provider.is_available() is True

    monkeypatch.setattr(config, "is_enabled", lambda k: False if k == "locus.architect.enabled" else True)
    assert provider.is_available() is False


def test_architect_provider_swappable():
    """SPEC §10.8 line 6342: "Provider Interface: ArchitectProvider" """
    class CustomArchitectProvider(BaseArchitectProvider):
        def is_available(self) -> bool:
            return True

        def scan(self, reward_model=None, hebbian_weights=None, experiences=None, life_os_metrics=None):
            return {"status": "ok", "candidates_count": 0, "candidates": []}

        def get_candidates(self):
            return [{"id": "mock-cand-1", "title": "Mock improvement"}]

        def apply_candidate(self, candidate_id: str):
            return {"status": "ok", "outcome": {"action": "mock_applied"}}

        def get_history(self):
            return [{"candidate_id": "mock-cand-1"}]

    provider: BaseArchitectProvider = CustomArchitectProvider()
    assert provider.is_available() is True
    assert len(provider.get_candidates()) == 1
    assert provider.apply_candidate("mock-cand-1")["outcome"]["action"] == "mock_applied"
