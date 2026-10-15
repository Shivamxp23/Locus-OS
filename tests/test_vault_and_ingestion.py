"""tests/test_vault_and_ingestion.py - Test suite for Cluster B features.

Tests:
- LocusShorthandCompressor (§27.3)
- RoughNoteParser (§27.5)
- LinkDumpLogger (§27.6)
- ExcalidrawDiagramBuilder (§27.7)
- DocumentChunker (§30.1)
- LightRAGBridge (§30.10)
- ContextReferenceResolver (§6.2)
- CodingContextEngine (§6.3)
- GatewayLifecycleManager (§17.10)
- MCPServer & MCPClient (§18.1-18.5)
- RedisStateManager (§30.9)
"""

import json
import pytest
from pathlib import Path

from sidecar.compression.shorthand import LocusShorthandCompressor, CompressionStats
from sidecar.ingestion.rough_note_parser import RoughNoteParser, ParsedIdea
from sidecar.ingestion.link_logger import LinkDumpLogger, LoggedResource
from sidecar.tools.excalidraw_builder import ExcalidrawDiagramBuilder
from sidecar.crawlers.chunker import DocumentChunker, DocumentChunk
from sidecar.vault.lightrag_bridge import LightRAGBridge, QueryMode
from sidecar.context.references import ContextReferenceResolver
from sidecar.context.coding_context import CodingContextEngine
from sidecar.gateway.lifecycle import GatewayLifecycleManager, GatewayStateSnapshot
from sidecar.mcp.server import MCPServer
from sidecar.mcp.client import MCPClient
from sidecar.state.redis_manager import RedisStateManager
from sidecar.life_os.factions import Faction


# -----------------------------------------------------------------------------
# F-0122: LOCUS_SHORTHAND
# -----------------------------------------------------------------------------
def test_shorthand_compression():
    compressor = LocusShorthandCompressor()
    text = "The asynchronous function will execute database initialization with repository configuration."
    compressed, stats = compressor.compress(text)
    assert "fn" in compressed
    assert "db" in compressed
    assert "repo" in compressed
    assert stats.savings_pct > 10.0


def test_shorthand_integration():
    compressor = LocusShorthandCompressor()
    text = "function execution repository context"
    compressed, _ = compressor.compress(text)
    decompressed = compressor.decompress(compressed)
    assert "function" in decompressed
    assert "repository" in decompressed


# -----------------------------------------------------------------------------
# F-0061: Rough Note Parser
# -----------------------------------------------------------------------------
def test_rough_note_parser():
    parser = RoughNoteParser()
    raw = """
    - Workout at gym 7am #health
    - Refactor scheduler engine #craft
    - Todo review monthly taxes and investment returns #leverage
    - Write essay on AI cognition #expression
    """
    ideas = parser.parse_note(raw)
    assert len(ideas) == 4
    assert ideas[0].detected_faction == Faction.HEALTH
    assert ideas[1].detected_faction == Faction.CRAFT
    assert ideas[2].detected_faction == Faction.LEVERAGE
    assert ideas[3].detected_faction == Faction.EXPRESSION


def test_rough_note_integration():
    parser = RoughNoteParser()
    ideas = parser.parse_note("- Todo fix broken link dump parser #bug")
    assert len(ideas) == 1
    assert ideas[0].is_actionable is True
    assert "#bug" in ideas[0].detected_tags


# -----------------------------------------------------------------------------
# F-0062: Link Dump Logger
# -----------------------------------------------------------------------------
def test_link_dump_logger():
    logger = LinkDumpLogger()
    text = "Check this article: https://github.com/Shivamxp23/Locus-OS?utm_source=twitter&utm_medium=social"
    resources = logger.process_text(text)
    assert len(resources) == 1
    assert "utm_source" not in resources[0].clean_url
    assert resources[0].domain == "github.com"


def test_link_dump_integration():
    logger = LinkDumpLogger()
    resources = logger.process_text("Links: https://example.com/a and https://example.com/b")
    assert len(resources) == 2
    for r in resources:
        assert r.markdown_entry.startswith("- [example.com]")


# -----------------------------------------------------------------------------
# F-0063: Excalidraw MCP Skill
# -----------------------------------------------------------------------------
def test_excalidraw_builder():
    builder = ExcalidrawDiagramBuilder()
    n1 = builder.add_node("Pi Agent Core", 100, 100)
    n2 = builder.add_node("Python Sidecar", 300, 100)
    a1 = builder.add_arrow(n1, n2, "RPC HTTP")
    doc_json = builder.to_json()
    parsed = json.loads(doc_json)
    assert parsed["type"] == "excalidraw"
    assert len(parsed["elements"]) == 3


def test_excalidraw_integration():
    builder = ExcalidrawDiagramBuilder()
    builder.add_node("Neo4j", 50, 50, shape="ellipse")
    doc = json.loads(builder.to_json())
    assert doc["elements"][0]["type"] == "ellipse"


# -----------------------------------------------------------------------------
# F-0072: Collector + Chunker
# -----------------------------------------------------------------------------
def test_document_chunker():
    chunker = DocumentChunker(target_chunk_size=120, overlap=20)
    doc = """# Introduction
This is the introduction section detailing system architecture.

## Details
Here are granular implementation parameters for the memory engine and indexing cascade.
"""
    chunks = chunker.chunk_markdown(doc, "system.md")
    assert len(chunks) >= 2
    assert "Introduction" in chunks[0].heading_path or "Details" in chunks[-1].heading_path


def test_document_chunker_integration():
    chunker = DocumentChunker(target_chunk_size=80)
    chunks = chunker.chunk_markdown("Short doc with minimal lines.", "short.md")
    assert len(chunks) == 1
    assert chunks[0].source_file == "short.md"


# -----------------------------------------------------------------------------
# F-0081: Obsidian/LightRAG Bridge
# -----------------------------------------------------------------------------
def test_lightrag_bridge():
    bridge = LightRAGBridge()
    content = "This document connects [[MemoryEngine]] and [[Neo4jGraph]] for persistent entity retention."
    count = bridge.index_document("vault/01-Projects/Engine.md", content)
    assert count == 2
    assert "MemoryEngine" in bridge.entities


def test_lightrag_integration():
    bridge = LightRAGBridge()
    bridge.index_document("vault/01-Projects/CouchDB.md", "Notes on [[CouchDBSync]] replication.")
    res = bridge.query("Tell me about CouchDBSync", mode=QueryMode.HYBRID)
    assert "CouchDBSync" in res.relevant_nodes
    assert res.confidence_score > 0.8


# -----------------------------------------------------------------------------
# F-0028: Context References
# -----------------------------------------------------------------------------
def test_context_references():
    resolver = ContextReferenceResolver()
    prompt = "Review @file(tracker/STATUS.md) and @symbol(LocusDoctor)"
    _, resolved = resolver.inject_references(prompt)
    assert len(resolved) == 2
    assert resolved[0].ref_type == "file"
    assert resolved[0].is_resolved is True


def test_context_references_integration():
    resolver = ContextReferenceResolver()
    _, resolved = resolver.inject_references("Check @git(status) and @diff(active)")
    assert len(resolved) == 2
    assert resolved[0].ref_type == "git"


# -----------------------------------------------------------------------------
# F-0029: Coding Context
# -----------------------------------------------------------------------------
def test_coding_context():
    engine = CodingContextEngine()
    symbols = engine.extract_python_symbols("sidecar/health.py")
    assert any(s.name == "HealthMonitor" for s in symbols)


def test_coding_context_integration():
    engine = CodingContextEngine()
    repo_map = engine.build_repo_map(max_files=5)
    assert len(repo_map) > 0
    assert any("sidecar" in item.rel_path for item in repo_map)


# -----------------------------------------------------------------------------
# F-0047: Graceful Restart
# -----------------------------------------------------------------------------
def test_gateway_lifecycle(tmp_path):
    snap_path = tmp_path / "snapshot.json"
    mgr = GatewayLifecycleManager(snapshot_path=snap_path)
    mgr.create_snapshot(["sess-1", "sess-2"], pending_queue_count=3, gateway_port=8080)

    restored = mgr.restore_snapshot()
    assert restored is not None
    assert restored.active_session_ids == ["sess-1", "sess-2"]
    assert restored.pending_queue_count == 3


def test_gateway_lifecycle_integration(tmp_path):
    snap_path = tmp_path / "snapshot_int.json"
    mgr = GatewayLifecycleManager(snapshot_path=snap_path)
    mgr.create_snapshot(["sess-x"])
    assert mgr.clear_snapshot() is True
    assert mgr.restore_snapshot() is None


# -----------------------------------------------------------------------------
# F-0048: MCP Server & Client
# -----------------------------------------------------------------------------
def test_mcp_server_and_client():
    server = MCPServer()
    server.register_tool(
        name="vault_search",
        description="Search vault notes",
        input_schema={"type": "object"},
        handler=lambda args: f"Found note for query: {args.get('q')}",
    )

    client = MCPClient(server)
    assert client.initialize() is True
    tools = client.list_tools()
    assert len(tools) == 1
    assert tools[0]["name"] == "vault_search"


def test_mcp_integration():
    server = MCPServer()
    server.register_tool("add", "Add", {}, lambda a: a["x"] + a["y"])
    client = MCPClient(server)
    res = client.call_tool("add", {"x": 5, "y": 7})
    assert "12" in res["result"]["content"][0]["text"]


# -----------------------------------------------------------------------------
# F-0080: Redis Integration
# -----------------------------------------------------------------------------
def test_redis_state_manager():
    mgr = RedisStateManager()
    mgr.set("user_session", {"id": "123"}, ttl_seconds=60)
    assert mgr.get("user_session") == {"id": "123"}
    mgr.delete("user_session")
    assert mgr.get("user_session") is None


def test_redis_integration():
    mgr = RedisStateManager()
    assert mgr.acquire_lock("scheduler_lock") is True
    # Cannot acquire same lock twice
    assert mgr.acquire_lock("scheduler_lock") is False
    assert mgr.release_lock("scheduler_lock") is True
    assert mgr.acquire_lock("scheduler_lock") is True
