"""
SPEC §1.11 / F-0011 / US-30: Unit tests for Title Generation.
Asserts prompt assembly, input truncation (500 chars), artifact cleaning,
async execution with callbacks, provider lifecycle, and modular off-switches.
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict

import pytest

from sidecar import config
from sidecar.providers.title_generator import (
    BaseTitleGeneratorProvider,
    TitleGenerationRequest,
    TitleGenerationResult,
)
from sidecar.registry import get_registry
from sidecar.title_generator import (
    TITLE_SYSTEM_PROMPT,
    TitleGeneratorProvider,
    clean_title,
    format_title_prompt,
    generate_fallback_title,
)


def test_title_generator_data_structures():
    """SPEC §1.11 line 2386: "TITLE GENERATION:"."""
    req = TitleGenerationRequest(
        user_message="Hello, can you help me refactor my database models?",
        assistant_response="Sure! Let's examine your current schema.",
        timeout=15.0,
        fallback_title="Custom Fallback",
    )
    req_dict = req.to_dict()
    assert req_dict["timeout"] == 15.0
    assert "refactor my database" in req_dict["user_message"]
    assert req_dict["fallback_title"] == "Custom Fallback"

    res = TitleGenerationResult(
        title="Refactoring Database Models",
        raw_response='Title: "Refactoring Database Models"',
        source="llm",
        status="success",
        duration_ms=45.2,
    )
    res_dict = res.to_dict()
    assert res_dict["title"] == "Refactoring Database Models"
    assert res_dict["status"] == "success"
    assert res_dict["duration_ms"] == 45.2


def test_format_title_prompt_snippet_truncation():
    """SPEC §1.11 line 2392: "// Truncate to keep request small"."""
    long_user = "U" * 1200
    long_assistant = "A" * 1200

    prompt_data = format_title_prompt(long_user, long_assistant, timeout=25.0)
    assert prompt_data["task"] == "title_generation"
    assert prompt_data["timeout"] == 25.0
    assert prompt_data["temperature"] == 0.3
    assert prompt_data["max_tokens"] == 500

    messages = prompt_data["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == TITLE_SYSTEM_PROMPT

    user_content = messages[1]["content"]
    # 500 chars max for each snippet
    assert f"User: {'U' * 500}" in user_content
    assert f"Assistant: {'A' * 500}" in user_content
    assert f"{'U' * 501}" not in user_content
    assert f"{'A' * 501}" not in user_content


def test_clean_title_strip_quotes():
    """SPEC §1.11 line 2416: "title = strip_quotes(title)"."""
    assert clean_title('"FastAPI Architecture Design"') == "FastAPI Architecture Design"
    assert clean_title("'Async Rust Concurrency'") == "Async Rust Concurrency"
    assert clean_title("“Memory Management in C++”") == "Memory Management in C++"
    assert clean_title("«Quantum Computing Foundations»") == "Quantum Computing Foundations"
    assert clean_title("`Debug Docker Networking`") == "Debug Docker Networking"


def test_clean_title_remove_prefix():
    """SPEC §1.11 line 2417: "IF title starts with \"Title:\": title = title[6:].strip()"."""
    assert clean_title("Title: Exploring Graph Algorithms") == "Exploring Graph Algorithms"
    assert clean_title("title:   Configuring NGINX Proxy  ") == "Configuring NGINX Proxy"
    assert clean_title('Title: "Optimizing SQLite Queries"') == "Optimizing SQLite Queries"
    assert clean_title('TITLE: \'Refactoring Vue Components\'') == "Refactoring Vue Components"


def test_clean_title_enforce_80_char_limit():
    """SPEC §1.11 line 2418: "IF len(title) > 80: title = title[:77] + \"...\""."""
    long_title = "Comprehensive Architectural Analysis of Distributed Microservice Patterns and Consensus Protocols"
    assert len(long_title) > 80

    cleaned = clean_title(long_title)
    assert len(cleaned) <= 80
    assert cleaned.endswith("...")
    assert cleaned == long_title[:77] + "..."


def test_clean_title_trailing_punctuation_and_whitespace():
    """SPEC §1.11 line 2415: "// Clean up artifacts"."""
    assert clean_title("Building an Event-Driven Bus...") == "Building an Event-Driven Bus"
    assert clean_title("Why Is Redis So Fast?!") == "Why Is Redis So Fast"
    assert clean_title("Summary of Decisions:") == "Summary of Decisions"
    assert clean_title("   Multi-Threaded   Execution   Pool   ") == "Multi-Threaded Execution Pool"
    assert clean_title("") == ""
    assert clean_title(None) == ""


def test_generate_fallback_title():
    """SPEC §1.11 line 2426: "// If fails: log warning, session keeps timestamp-based title"."""
    fallback_with_msg = generate_fallback_title("How do I configure Postgres replication?")
    assert "How do I configure Postgres replication" in fallback_with_msg

    fallback_empty = generate_fallback_title("")
    assert fallback_empty.startswith("Session ")


def test_title_generator_provider_synchronous_generation():
    """SPEC §1.11 line 2390: "FUNCTION generate_title(user_message, assistant_response, timeout=30s):"."""
    provider = TitleGeneratorProvider()

    def mock_llm(payload: Dict[str, Any]) -> str:
        return 'Title: "Kubernetes Pod Lifecycle Management."'

    title = provider.generate_title(
        user_message="How does Kubernetes handle pod restarts?",
        assistant_response="Kubernetes uses restartPolicy to restart terminated containers.",
        llm_caller=mock_llm,
    )
    assert title == "Kubernetes Pod Lifecycle Management"


def test_title_generator_provider_heuristic_fallback_when_caller_omitted():
    """SPEC §1.11 line 2390: "FUNCTION generate_title(user_message, assistant_response, timeout=30s):"."""
    provider = TitleGeneratorProvider()
    title = provider.generate_title(
        user_message="Docker compose network troubleshooting guide",
        assistant_response="Here is how Docker bridges containers together.",
    )
    assert title is not None
    assert len(title.split()) >= 3


def test_title_generator_async_generation():
    """SPEC §1.11 line 2422: "FUNCTION generate_title_async(user_msg, assistant_msg, callback):"."""
    provider = TitleGeneratorProvider()
    received_titles = []
    done_event = threading.Event()

    def on_title(generated: str) -> None:
        received_titles.append(generated)
        done_event.set()

    def slow_llm(payload: Dict[str, Any]) -> str:
        time.sleep(0.05)
        return "Async Event Processing Engine"

    thread = provider.generate_title_async(
        user_message="Build an event processing system",
        assistant_response="Using Kafka or RabbitMQ",
        callback=on_title,
        llm_caller=slow_llm,
    )
    assert thread.is_alive() or done_event.is_set()
    assert done_event.wait(timeout=2.0)
    assert received_titles == ["Async Event Processing Engine"]


def test_title_generator_provider_lifecycle_and_registry():
    """SPEC §1.11 line 2428: "Provider Interface: Uses Pi's auxiliary LLM call mechanism (cheapest available model)."."""
    reg = get_registry()
    provider_cls = reg.get("title_generator", "default")
    assert provider_cls is not None

    provider = provider_cls()
    assert isinstance(provider, BaseTitleGeneratorProvider)
    assert provider.is_enabled() is True


def test_title_generator_modular_off_switch(monkeypatch):
    """SPEC §1.11 line 2431: "Swappable / off state: locus.sessions.auto_title.enabled. Off → sessions use default timestamp-based titles"."""
    provider = TitleGeneratorProvider()
    assert provider.is_enabled() is True

    # Disable auto_title
    monkeypatch.setattr(config, "get", lambda k, d=None: False if "title" in k else True)
    assert provider.is_enabled() is False

    title = provider.generate_title(
        user_message="Explain semantic search algorithms",
        assistant_response="Semantic search uses dense vector embeddings.",
    )
    assert title is None
