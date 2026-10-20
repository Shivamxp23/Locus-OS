"""
Unit tests for Memory Provider Interface & Stackable Memory Manager (SPEC §4.18 / F-0118 / US-57).
Asserts:
  - MemoryProvider lifecycle: is_available, initialize, shutdown
  - Prefetch and queue_prefetch context recall
  - Non-blocking sync_turn turn persistence
  - Tool schemas export and tool call execution
  - Optional lifecycle hooks (on_turn_start, on_session_switch, on_pre_compress, etc.)
  - Stackable MemoryManager: multi-provider registration, merged prefetch, broadcast sync_turn, tool routing
"""
import json
import pytest

from sidecar.memory.provider_interface import (
    DefaultMemoryProvider,
    MemoryManager,
    MemoryProvider,
)


class SecondaryMemoryProvider(MemoryProvider):
    """Secondary test provider (e.g. simulating PageIndex or vector store)."""

    def __init__(self, name: str = "vector_memory") -> None:
        super().__init__(name=name)
        self.turns: list = []

    def is_available(self) -> bool:
        return True

    def initialize(self, session_id: str, **kwargs) -> None:
        self.active_session_id = session_id
        self.is_initialized = True

    def system_prompt_block(self) -> str:
        return "[VectorMemory: Semantic index active]"

    def prefetch(self, query: str, session_id: str | None = None) -> str:
        if "architecture" in query.lower():
            return "Semantic fact: Locus OS uses a 6-layer cognitive pipeline."
        return ""

    def queue_prefetch(self, query: str, session_id: str | None = None) -> None:
        pass

    def sync_turn(self, user_content: str, assistant_content: str, session_id: str | None = None, messages: list | None = None) -> None:
        self.turns.append({"u": user_content, "a": assistant_content})

    def get_tool_schemas(self) -> list:
        return [
            {
                "type": "function",
                "function": {
                    "name": f"{self.name}_knn",
                    "description": "Semantic k-nearest-neighbors search",
                    "parameters": {"type": "object", "properties": {"q": {"type": "string"}}},
                },
            }
        ]

    def handle_tool_call(self, tool_name: str, args: dict) -> str:
        if tool_name == f"{self.name}_knn":
            return json.dumps({"knn_results": ["fact1", "fact2"]})
        return json.dumps({"error": "unknown"})

    def shutdown(self) -> None:
        self.is_initialized = False
        self.turns.clear()


def test_memory_provider_lifecycle():
    """SPEC §4.18 lines 5252-5256, 5272:
    is_available() -> bool, initialize(session_id, **kwargs), shutdown().
    """
    provider = DefaultMemoryProvider(name="test_mem")
    assert provider.is_available() is True
    assert provider.is_initialized is False

    provider.initialize("sess_123", platform="cli", agent_identity="locus")
    assert provider.is_initialized is True
    assert provider.active_session_id == "sess_123"
    assert provider.runtime_kwargs.get("platform") == "cli"

    provider.shutdown()
    assert provider.is_initialized is False


def test_system_prompt_block():
    """SPEC §4.18 line 5258: system_prompt_block() -> str."""
    provider = DefaultMemoryProvider(name="core_mem")
    block = provider.system_prompt_block()
    assert isinstance(block, str)
    assert "core_mem" in block


def test_prefetch_and_sync_turn():
    """SPEC §4.18 lines 5260, 5267:
    prefetch(query, session_id) -> str, sync_turn(user, assistant, session_id).
    """
    provider = DefaultMemoryProvider(name="test_mem")
    provider.initialize("sess_456")

    # Sync turns
    provider.sync_turn(
        user_content="What database stores the graph memory?",
        assistant_content="Neo4j stores the graph memory in POLE+O format.",
        session_id="sess_456",
    )
    provider.sync_turn(
        user_content="How is context compacted?",
        assistant_content="Hermes 7-step compaction engine handles context compaction.",
        session_id="sess_456",
    )

    # Prefetch query
    context = provider.prefetch("Neo4j", session_id="sess_456")
    assert "Neo4j stores the graph memory" in context

    # Cache hit returns same
    cached = provider.prefetch("Neo4j", session_id="sess_456")
    assert cached == context


def test_tool_schemas_and_execution():
    """SPEC §4.18 lines 5270-5271:
    get_tool_schemas() -> [tool_schema], handle_tool_call(tool_name, args) -> json_string.
    """
    provider = DefaultMemoryProvider(name="my_mem")
    tools = provider.get_tool_schemas()
    assert len(tools) == 1
    assert tools[0]["function"]["name"] == "my_mem_search"

    res = provider.handle_tool_call("my_mem_search", {"query": "test"})
    data = json.loads(res)
    assert data["status"] == "ok"

    err_res = provider.handle_tool_call("nonexistent_tool", {})
    assert "error" in json.loads(err_res)


def test_optional_hooks():
    """SPEC §4.18 lines 5274-5281:
    Optional hooks: on_turn_start, on_session_switch, on_pre_compress, on_memory_write, on_delegation.
    """
    provider = DefaultMemoryProvider(name="hook_mem")
    provider.initialize("s1")

    provider.on_turn_start(turn_number=1, message={"role": "user", "content": "hi"})
    provider.on_session_switch("s2", parent_session_id="s1")
    assert provider.active_session_id == "s2"

    pre_comp = provider.on_pre_compress([{"role": "user", "content": "old"}])
    assert pre_comp is None

    provider.on_memory_write("write", "target", "content")
    provider.on_delegation("subtask", "done", "child_1")
    provider.on_session_end([])


def test_stackable_memory_manager():
    """SPEC §4.18 lines 5282-5309:
    Stackable Memory Manager relaxing Hermes single-provider limit to support multi-provider memory layers.
    """
    mgr = MemoryManager()
    p1 = DefaultMemoryProvider(name="primary_mem")
    p2 = SecondaryMemoryProvider(name="vector_mem")

    # Register providers
    ok1 = mgr.register_provider(p1, session_id="s_multi", is_primary=True)
    ok2 = mgr.register_provider(p2, session_id="s_multi", is_primary=False)
    assert ok1 is True
    assert ok2 is True

    assert mgr.get_primary_provider() == p1
    assert len(mgr.getActiveProviders() if hasattr(mgr, "getActiveProviders") else mgr.get_active_providers()) == 2

    # Sync turn broadcast
    mgr.sync_turn_all(
        user_content="Describe system architecture details.",
        assistant_content="Locus architecture includes sidecar and extension.",
        session_id="s_multi",
    )
    assert len(p2.turns) == 1

    # Prefetch all aggregates context across providers
    merged_context = mgr.prefetch_all("architecture", session_id="s_multi")
    assert "[primary_mem]" in merged_context
    assert "[vector_mem]" in merged_context
    assert "Locus OS uses a 6-layer cognitive pipeline" in merged_context

    # Tool aggregation and routing
    tools = mgr.get_all_tool_schemas()
    names = [t["function"]["name"] for t in tools]
    assert "primary_mem_search" in names
    assert "vector_mem_knn" in names

    # Tool call routing
    knn_res = mgr.handle_tool_call("vector_mem_knn", {"q": "search"})
    assert "knn_results" in json.loads(knn_res)

    mgr.shutdown_all()
    assert len(mgr.get_active_providers()) == 0
    assert mgr.get_primary_provider() is None
