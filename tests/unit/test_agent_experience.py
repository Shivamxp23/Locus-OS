"""
Unit tests for Agent Experience Tracking (Procedural Memory) (SPEC §10.9 / F-0121 / US-67).
"""
import shutil
import tempfile
from pathlib import Path
import pytest

from sidecar.experience.procedural import (
    AgentExperience,
    AgentExperienceCaptureHook,
    ExperienceStore,
    prepend_experience_block,
    redact_text,
    render_experience_hits,
    stable_experience_id,
)
from sidecar.providers.agent_experience import DefaultAgentExperienceProvider
import sidecar.config as config


@pytest.fixture
def temp_exp_dir():
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_stable_experience_id():
    """SPEC §10.9 line 6380: "Deterministic dedupe (stable_experience_id): sha256(task_summary.lower() + tool_sequence.lower() + outcome) truncated to 24 hex chars, prefixed exp_." """
    id1 = stable_experience_id("search code", ["grep", "file_read"], "Success")
    id2 = stable_experience_id("SEARCH CODE", ["grep", "file_read"], "SUCCESS")
    id3 = stable_experience_id("search code", ["grep", "write_file"], "Success")

    assert id1.startswith("exp_")
    assert len(id1) == 28  # "exp_" (4) + 24 hex chars = 28
    assert id1 == id2
    assert id1 != id3


def test_redact_text_scrubbing():
    """SPEC §10.9 line 6384: "Redaction (redact_text): three regexes scrub Bearer tokens, sk- OpenAI-style keys, and token/api_key/secret/password[:=] value patterns before anything is stored." """
    raw = (
        "Authorization: Bearer ya29.a0AfH6SM... and sk-proj-1234567890abcdef "
        "with api_key: secret_value_xyz and password=MySecretPass123"
    )
    scrubbed = redact_text(raw)
    assert "Bearer [redacted]" in scrubbed
    assert "sk-[redacted]" in scrubbed
    assert "api_key=[redacted]" in scrubbed or "api_key: [redacted]" in scrubbed or "api_key=[redacted]" in scrubbed
    assert "password=[redacted]" in scrubbed or "password: [redacted]" in scrubbed
    assert "ya29" not in scrubbed
    assert "1234567890abcdef" not in scrubbed
    assert "secret_value_xyz" not in scrubbed
    assert "MySecretPass123" not in scrubbed


def test_candidate_extraction_success_sequence(temp_exp_dir):
    """SPEC §10.9 line 6389: "1. Successful multi-tool sequence — ≥2 successful calls → Success, confidence 0.72" """
    store = ExperienceStore(storage_dir=temp_exp_dir)
    hook = AgentExperienceCaptureHook(store=store)

    turn_ctx = {
        "task_summary": "Investigate git log and check repository files",
        "task_fingerprint": "git-log-check",
        "tool_calls": [
            {"name": "git_status", "status": "success"},
            {"name": "file_read", "status": "success"},
        ],
    }

    candidates = hook.extract_candidates(turn_ctx)
    assert len(candidates) == 1
    c = candidates[0]
    assert c.outcome == "Success"
    assert c.confidence == 0.72
    assert c.tool_sequence == ["git_status", "file_read"]
    assert "git_status -> file_read" in c.lesson
    assert "reuse git_status -> file_read" in (c.reuse_hint or "")


def test_candidate_extraction_repeated_failure(temp_exp_dir):
    """SPEC §10.9 line 6391: "2. Repeated failure — any tool that failed ≥2 times in one turn → Failure, confidence 0.68, error_class parsed from the output summary" """
    store = ExperienceStore(storage_dir=temp_exp_dir)
    hook = AgentExperienceCaptureHook(store=store)

    turn_ctx = {
        "task_summary": "Read privileged configuration",
        "task_fingerprint": "read-priv-config",
        "tool_calls": [
            {"name": "read_file", "status": "error", "error": "permission_denied: /etc/shadow"},
            {"name": "read_file", "status": "error", "error": "permission_denied: /etc/shadow"},
        ],
    }

    candidates = hook.extract_candidates(turn_ctx)
    assert len(candidates) == 1
    c = candidates[0]
    assert c.outcome == "Failure"
    assert c.confidence == 0.68
    assert "permission_denied" in (c.error_class or "")
    assert "avoid retrying read_file repeatedly" in (c.avoid_hint or "")


def test_candidate_extraction_partial_success(temp_exp_dir):
    """SPEC §10.9 line 6393: "3. Partial success — a failure followed by a later success → Partial, confidence 0.62, lesson = 'the task recovered by continuing with <sequence>'." """
    store = ExperienceStore(storage_dir=temp_exp_dir)
    hook = AgentExperienceCaptureHook(store=store)

    turn_ctx = {
        "task_summary": "Search codebase with grep fallback",
        "task_fingerprint": "search-codebase-grep",
        "tool_calls": [
            {"name": "fast_search", "status": "error", "error": "timeout"},
            {"name": "grep", "status": "success"},
        ],
    }

    candidates = hook.extract_candidates(turn_ctx)
    assert len(candidates) == 1
    c = candidates[0]
    assert c.outcome == "Partial"
    assert c.confidence == 0.62
    assert "the task recovered by continuing with fast_search -> grep" in c.lesson


def test_experience_store_upsert_and_redaction(temp_exp_dir):
    """SPEC §10.9 line 6385: "Same task + same tool sequence + same outcome → same id → the store upserts instead of duplicating." """
    store = ExperienceStore(storage_dir=temp_exp_dir)

    exp_id = stable_experience_id("query database", ["db_connect", "db_query"], "Success")
    exp1 = AgentExperience(
        id=exp_id,
        source="ToolLoop",
        agent_id="test-agent",
        entrypoint="test",
        task_fingerprint="db-query",
        task_summary="query database with token: secret_token_123",
        tools_used=["db_connect", "db_query"],
        tool_sequence=["db_connect", "db_query"],
        outcome="Success",
        lesson="connected with Bearer secret_bearer_token",
        confidence=0.72,
    )

    store.put(exp1)
    assert len(store.list()) == 1

    stored = store.get(exp_id)
    assert stored is not None
    assert "secret_token_123" not in stored.task_summary
    assert "token=[redacted]" in stored.task_summary
    assert "secret_bearer_token" not in stored.lesson
    assert "Bearer [redacted]" in stored.lesson

    # Upsert with new confidence
    exp2 = AgentExperience(
        id=exp_id,
        source="ToolLoop",
        agent_id="test-agent",
        entrypoint="test",
        task_fingerprint="db-query",
        task_summary="query database with updated parameters",
        tools_used=["db_connect", "db_query"],
        tool_sequence=["db_connect", "db_query"],
        outcome="Success",
        lesson="updated lesson",
        confidence=0.85,
    )
    store.put(exp2)
    assert len(store.list()) == 1
    assert store.get(exp_id).confidence == 0.85


def test_render_and_prepend_experience_block():
    """SPEC §10.9 line 6395: "Injection (prompt.rs): relevant hits are rendered as a compact, byte-capped block — '## Relevant Operating Experience' ... and prepended to the enriched message" """
    exp = AgentExperience(
        id="exp_01",
        source="ToolLoop",
        agent_id="test-agent",
        entrypoint="test",
        task_fingerprint="grep-files",
        task_summary="grep for files",
        tools_used=["grep", "file_read"],
        tool_sequence=["grep", "file_read"],
        outcome="Success",
        lesson="grep followed by file_read succeeded",
        confidence=0.72,
        reuse_hint="reuse grep -> file_read",
    )

    block = render_experience_hits([exp])
    assert "## Relevant Operating Experience" in block
    assert "1. success sequence: grep -> file_read" in block
    assert "lesson: grep followed by file_read succeeded" in block
    assert "reuse: reuse grep -> file_read" in block

    prepended = prepend_experience_block("User question here", [exp])
    assert prepended.startswith("## Relevant Operating Experience")
    assert prepended.endswith("User question here")


def test_provider_off_switches(temp_exp_dir, monkeypatch):
    """SPEC §10.9 line 6407: "Swappable / off state: locus.experience.enabled. Off → no capture, no injection; the 'Relevant Operating Experience' block simply never appears." """
    provider = DefaultAgentExperienceProvider(storage_dir=temp_exp_dir)

    monkeypatch.setattr(config, "get", lambda key: True if "enabled" in key else None)
    monkeypatch.setattr(config, "is_enabled", lambda key: True)
    assert provider.is_available() is True

    # Off switch 1: locus.experience.enabled
    monkeypatch.setattr(config, "get", lambda key: False if key == "locus.experience.enabled" else True)
    monkeypatch.setattr(config, "is_enabled", lambda key: False if key == "locus.experience.enabled" else True)
    assert provider.is_available() is False

    # Off switch 2: locus.agent_experience_tracking_procedural_memory.enabled
    monkeypatch.setattr(config, "get", lambda key: False if key == "locus.agent_experience_tracking_procedural_memory.enabled" else True)
    monkeypatch.setattr(config, "is_enabled", lambda key: False if key == "locus.agent_experience_tracking_procedural_memory.enabled" else True)
    assert provider.is_available() is False
