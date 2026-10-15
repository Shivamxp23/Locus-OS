"""Test suite for Wave 8C: Subagents, ACP, Skills, Architect & Experience.

Covers:
- F-0033: ACP Protocol (§9.4)
- F-0035: Learning / Profiling / Reward Model (§1.7, §10.1, §10.3, §10.5-10.7)
- F-0036: Subagents / AutoResearch (§3.7, §11.1-11.5)
- F-0119: Skill System & Multi-Source Marketplace (§10.7 / §9.2)
- F-0120: Self-Evolving Architect Bot (§10.8)
- F-0121: Agent Experience Tracking (Procedural Memory) (§10.9)
"""

import json
import pytest

from sidecar.acp.server import ACPMessage, ACPServerTransport
from sidecar.learning.profiler import SignalType, UserProfileSignal, RewardModelScorer, UserLearningEngine
from sidecar.delegation.subagent_orchestrator import SubagentArchetype, SubagentState, SubagentTask, SubagentOrchestrator
from sidecar.skills.marketplace import SkillManifest, SkillMarketplaceManager
from sidecar.architect.architect_bot import ProposalSeverity, ArchitectProposal, SelfEvolvingArchitectBot
from sidecar.experience.tracker import ProceduralTrajectory, AgentExperienceTracker


# -----------------------------------------------------------------------------
# F-0033: ACP Protocol
# -----------------------------------------------------------------------------
def test_acp_transport_unit():
    transport = ACPServerTransport()
    req = ACPMessage(id="1", method="initialize", params={})
    raw_resp = transport.handle_raw_message(req.serialize())
    resp = ACPMessage.deserialize(raw_resp)
    assert resp.id == "1"
    assert resp.result["protocolVersion"] == "1.0"


def test_acp_transport_integration():
    transport = ACPServerTransport()
    # Create session
    req1 = ACPMessage(id="sess_1", method="session/create", params={"client": "vscode"})
    res1 = ACPMessage.deserialize(transport.handle_raw_message(req1.serialize()))
    sess_id = res1.result["sessionId"]
    assert sess_id in transport.active_sessions

    # Send prompt
    req2 = ACPMessage(id="p1", method="session/prompt", params={"sessionId": sess_id, "prompt": "build feature"})
    res2 = ACPMessage.deserialize(transport.handle_raw_message(req2.serialize()))
    assert "ACP Agent received" in res2.result["reply"]


# -----------------------------------------------------------------------------
# F-0035: Learning / Profiling / Reward Model
# -----------------------------------------------------------------------------
def test_user_learning_unit():
    scorer = RewardModelScorer()
    reward_pos = scorer.compute_turn_reward("Done with task", "Thanks, that was great!", True)
    assert reward_pos > 0.6

    reward_neg = scorer.compute_turn_reward("Done with task", "No, this is wrong and failed", False)
    assert reward_neg < -0.4


def test_user_learning_integration():
    engine = UserLearningEngine()
    engine.record_turn("Refactored database module", "Thanks, keep responses concise", True)
    summary = engine.get_profile_summary()
    assert summary["profile"]["prefers_terse_output"] is True
    assert summary["total_signals_recorded"] >= 1


# -----------------------------------------------------------------------------
# F-0036: Subagents / AutoResearch
# -----------------------------------------------------------------------------
def test_subagents_unit():
    orchestrator = SubagentOrchestrator(global_max_depth=3)
    task = orchestrator.spawn_subagent(SubagentArchetype.RESEARCHER, "Find citations for AlphaFold")
    assert task.archetype == SubagentArchetype.RESEARCHER
    assert task.depth == 1

    out = orchestrator.execute_subagent(task)
    assert "[RESEARCHER]" in out
    assert task.state == SubagentState.COMPLETED


def test_subagents_integration():
    orchestrator = SubagentOrchestrator(global_max_depth=2)
    t1 = orchestrator.spawn_subagent(SubagentArchetype.PLANNER, "High level architecture", parent_depth=0)
    t2 = orchestrator.spawn_subagent(SubagentArchetype.CODER, "Sub task implementation", parent_depth=1)

    # Depth limit breach
    with pytest.raises(ValueError):
        orchestrator.spawn_subagent(SubagentArchetype.CRITIC, "Excessive sub task", parent_depth=2)


# -----------------------------------------------------------------------------
# F-0119: Skill System & Multi-Source Marketplace
# -----------------------------------------------------------------------------
def test_skill_marketplace_unit():
    mgr = SkillMarketplaceManager()
    skills = mgr.search_skills("alphafold")
    assert len(skills) >= 1
    assert skills[0].name == "alphafold-database"


def test_skill_marketplace_integration():
    mgr = SkillMarketplaceManager()
    assert mgr.install_skill("chembl-database") is True
    assert "chembl-database" in mgr.installed_skills
    assert mgr.uninstall_skill("chembl-database") is True
    assert "chembl-database" not in mgr.installed_skills


# -----------------------------------------------------------------------------
# F-0120: Self-Evolving Architect Bot
# -----------------------------------------------------------------------------
def test_architect_bot_unit():
    bot = SelfEvolvingArchitectBot()
    proposal = bot.inspect_module_metrics("huge_file.py", line_count=1200, cyclomatic_complexity=10, dependencies=[])
    assert proposal is not None
    assert proposal.severity == ProposalSeverity.WARNING
    assert "Decompose Monolithic" in proposal.title


def test_architect_bot_integration():
    bot = SelfEvolvingArchitectBot()
    p1 = bot.inspect_module_metrics("clean_file.py", line_count=200, cyclomatic_complexity=5, dependencies=[])
    assert p1 is None

    p2 = bot.inspect_module_metrics("complex_logic.py", line_count=300, cyclomatic_complexity=28, dependencies=[])
    assert p2 is not None
    assert len(bot.get_pending_proposals()) == 1


# -----------------------------------------------------------------------------
# F-0121: Agent Experience Tracking (Procedural Memory)
# -----------------------------------------------------------------------------
def test_experience_tracker_unit():
    tracker = AgentExperienceTracker()
    traj = tracker.record_trajectory(
        task_goal="Fix failing SQLite unit test",
        action_sequence=["read_error", "locate_file", "patch_schema", "run_pytest"],
        success=True,
    )
    assert traj.confidence_score >= 0.90
    assert len(tracker.trajectories) == 1


def test_experience_tracker_integration():
    tracker = AgentExperienceTracker()
    tracker.record_trajectory(
        task_goal="Deploy Docker container to Kubernetes cluster",
        action_sequence=["build_image", "push_registry", "apply_k8s_manifest"],
        success=True,
    )
    similar = tracker.find_similar_trajectories("Docker container deployment")
    assert len(similar) >= 1
    assert "apply_k8s_manifest" in similar[0].action_sequence
