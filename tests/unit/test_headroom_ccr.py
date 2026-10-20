"""
Unit tests for Headroom CCR Token Compression (SPEC §4.17 / F-0026 / US-56).
Asserts:
  - CompressConfig defaults (protect_recent=4, min_tokens_to_compress=250, compress_user_messages=False)
  - ContentRouter classification (PROSE, JSON, CODE)
  - CacheAligner prefix stabilization for KV-cache hits
  - SmartCrusher JSON deduplication and compaction
  - CodeCompressor structural comment and whitespace compression
  - CCRStore caching, retrieval, and TTL behavior
  - Inflation guard prevention of token bloat
  - Pipeline end-to-end compression with CCR marker insertion
  - CompressionProvider interface and configuration
"""
import json
from pathlib import Path
import pytest

from sidecar.context.headroom_pipeline import (
    CacheAligner,
    CCRStore,
    CodeCompressor,
    CompressConfig,
    CompressResult,
    ContentRouter,
    ContentType,
    HeadroomPipeline,
    KompressCompressor,
    SmartCrusher,
)
from sidecar.providers.headroom_ccr import (
    CompressionProvider,
    DefaultHeadroomCCRProvider,
)


def test_compress_config_defaults_and_serialization():
    """SPEC §4.17 lines 680, 690:
    Defaults: protect_recent=4, min_tokens_to_compress=250, compress_user_messages=False
    """
    cfg = CompressConfig()
    assert cfg.protect_recent == 4
    assert cfg.min_tokens_to_compress == 250
    assert cfg.compress_user_messages is False
    assert cfg.frozen_message_count == 0
    assert cfg.enabled is True
    assert cfg.ttl_seconds == 86400.0

    d = cfg.to_dict()
    restored = CompressConfig.from_dict(d)
    assert restored.protect_recent == 4
    assert restored.min_tokens_to_compress == 250
    assert restored.compress_user_messages is False


def test_content_router_classification():
    """SPEC §4.17 lines 665, 681, 694:
    Detects PROSE | JSON | CODE per message content.
    """
    router = ContentRouter()

    # JSON detection
    json_text = json.dumps({"status": "active", "scores": [1, 2, 3, 2, 1], "nested": {"a": "b"}})
    assert router.classify(json_text) == ContentType.JSON

    json_array = json.dumps([{"id": 1}, {"id": 2}])
    assert router.classify(json_array) == ContentType.JSON

    # Code detection (Python & JS blocks or keywords)
    code_block = "```python\ndef calculate_sum(a, b):\n    return a + b\n```"
    assert router.classify(code_block) == ContentType.CODE

    raw_python = "import os\ndef run_pipeline(root):\n    return os.path.exists(root)"
    assert router.classify(raw_python) == ContentType.CODE

    # Prose detection
    prose = "The architecture uses a 6-layer context forge pipeline to assemble retrieved facts into a unified context."
    assert router.classify(prose) == ContentType.PROSE
    assert router.classify("") == ContentType.PROSE


def test_cache_aligner_prefix_preservation():
    """SPEC §4.17 lines 664, 684, 693:
    CacheAligner anchors frozen prefix so provider KV cache still hits.
    """
    aligner = CacheAligner()
    messages = [
        {"role": "system", "content": "You are Locus OS cognitive supervisor."},
        {"role": "user", "content": "Core identity prompt."},
        {"role": "assistant", "content": "Acknowledged."},
        {"role": "user", "content": "Active task query."},
    ]

    # No frozen count
    frozen, active = aligner.align(messages, frozen_message_count=0)
    assert len(frozen) == 0
    assert len(active) == 4

    # Frozen prefix of 2 messages
    frozen, active = aligner.align(messages, frozen_message_count=2)
    assert len(frozen) == 2
    assert frozen == messages[:2]
    assert len(active) == 2
    assert active == messages[2:]


def test_smart_crusher_json_deduplication():
    """SPEC §4.17 lines 666, 681, 695:
    SmartCrusher: array dedup, lossless-first + compact separators.
    """
    crusher = SmartCrusher()
    raw_data = {
        "items": ["apple", "banana", "apple", "cherry", "banana"],
        "metadata": {
            "tags": ["prod", "alpha", "prod"],
            "status": "ready",
        },
    }
    raw_json = json.dumps(raw_data, indent=4)
    crushed = crusher.compress(raw_json)

    # Must be valid json
    parsed = json.loads(crushed)
    # Duplicate array elements removed
    assert parsed["items"] == ["apple", "banana", "cherry"]
    assert parsed["metadata"]["tags"] == ["prod", "alpha"]
    # Compact format (no spaces around separators)
    assert " " not in crushed.replace("ready", "").replace("apple", "").replace("banana", "").replace("cherry", "")
    assert len(crushed) < len(raw_json)


def test_code_compressor_structural_comments_and_whitespace():
    """SPEC §4.17 lines 667, 681, 695:
    CodeCompressor: structural comment removal and whitespace compaction.
    """
    compressor = CodeCompressor()
    code = (
        "def execute_task(param):   \n"
        "    # This is an explanatory comment that can be safely compressed\n"
        "    result = param * 2\n"
        "\n"
        "\n"
        "    // Another comment in javascript style\n"
        "    return result\n"
    )
    compressed = compressor.compress(code)
    assert "# This is an explanatory comment" not in compressed
    assert "// Another comment" not in compressed
    assert "result = param * 2" in compressed
    assert "return result" in compressed
    assert "\n\n\n" not in compressed


def test_ccr_store_caching_and_retrieval(tmp_path: Path):
    """SPEC §4.17 lines 669, 682, 701:
    CCR: reversible originals cached locally with key; headroom_retrieve(cache_key) -> full original.
    """
    store = CCRStore(cache_dir=tmp_path, ttl_seconds=3600.0)
    original_text = "Original uncompressed context containing detailed architectural specification sentences."
    key = store.store(original_text)
    assert len(key) == 16

    # In-memory retrieval
    retrieved = store.retrieve(key)
    assert retrieved == original_text

    # Disk cache retrieval after clearing memory cache
    store.clear()
    retrieved_from_disk = store.retrieve(key)
    assert retrieved_from_disk == original_text

    # Missing key
    assert store.retrieve("nonexistent_key_123") is None


def test_inflation_guard_reverts_when_compressed_is_larger():
    """SPEC §4.17 lines 683, 697:
    Inflation guard: if transform increases token count, revert to originals.
    """
    pipeline = HeadroomPipeline()
    tiny_msg = [{"role": "assistant", "content": "Ok"}]
    # Compressing a single tiny message should never inflate tokens
    res = pipeline.compress(tiny_msg)
    assert res.tokens_after <= res.tokens_before
    assert res.messages[0]["content"] == "Ok"


def test_headroom_pipeline_end_to_end_compression(tmp_path: Path):
    """SPEC §4.17 lines 674-702:
    End-to-end pipeline:
    - Anchors frozen prefix
    - Leaves user messages untouched
    - Compresses large assistant messages via SmartCrusher/CodeCompressor/Kompress
    - Protects 4 recent messages
    - Generates CCR cache key and retrieval marker
    """
    pipeline = HeadroomPipeline(cache_dir=tmp_path)
    large_json_assistant_content = json.dumps(
        {
            "analysis": "Extensive system analysis for Locus OS cognitive state evaluation. " * 15,
            "redundant_tags": ["tag1", "tag2", "tag1", "tag3", "tag2", "tag4"] * 10,
            "history": [{"step": i, "result": "step evaluation detail " * 8} for i in range(20)],
        },
        indent=4,
    )
    assert pipeline.estimate_tokens(large_json_assistant_content) > 300

    messages = [
        {"role": "system", "content": "Frozen system instructions for cognitive kernel."},
        {"role": "user", "content": "User request for system analysis."},
        {"role": "assistant", "content": large_json_assistant_content},
        # 4 recent messages protected by default
        {"role": "user", "content": "Recent question 1"},
        {"role": "assistant", "content": "Recent answer 1"},
        {"role": "user", "content": "Recent question 2"},
        {"role": "assistant", "content": "Recent answer 2"},
    ]

    cfg = CompressConfig(
        protect_recent=4,
        min_tokens_to_compress=200,
        compress_user_messages=False,
        frozen_message_count=1,
    )

    res = pipeline.compress(messages, config=cfg)
    assert isinstance(res, CompressResult)
    assert res.tokens_saved > 0
    assert res.ratio < 1.0
    assert len(res.cached_keys) >= 1
    assert "SmartCrusher" in res.transforms_applied
    assert "CCR" in res.transforms_applied

    # First frozen message is preserved
    assert res.messages[0]["content"] == messages[0]["content"]
    # User message untouched
    assert res.messages[1]["content"] == messages[1]["content"]
    # Assistant message has CCR marker
    assistant_msg = res.messages[2]
    assert "[CCR:" in assistant_msg["content"]
    assert "headroom_retrieve" in assistant_msg["content"]

    # 4 recent messages preserved verbatim
    assert res.messages[-4:] == messages[-4:]

    # Retrieve original from CCR store using cache key
    key = res.cached_keys[0]
    retrieved = pipeline.headroom_retrieve(key)
    assert retrieved == large_json_assistant_content


def test_provider_interface_and_off_switch():
    """SPEC §4.17 lines 707, 711:
    CompressionProvider interface and modular off-switch.
    """
    provider = DefaultHeadroomCCRProvider()
    assert isinstance(provider, CompressionProvider)
    assert provider.is_enabled() is True

    cfg_dict = provider.get_config()
    assert cfg_dict["provider"] == "headroom-ccr"
    assert cfg_dict["protect_recent"] == 4
    assert cfg_dict["min_tokens_to_compress"] == 250
    assert cfg_dict["compress_user_messages"] is False
