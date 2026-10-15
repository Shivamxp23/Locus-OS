import pytest
import json
from sidecar.memory.headroom_ccr import (
    CompressConfig,
    CCRCache,
    SmartCrusher,
    CodeCompressor,
    TextCompressor,
    HeadroomCompressor,
    compress,
)


def test_smart_crusher_json():
    # Long JSON with repeated elements and formatting whitespace
    data = [{"id": i, "val": "item"} for i in range(10)]
    pretty = json.dumps(data, indent=4)
    crushed = SmartCrusher.compress(pretty)
    assert len(crushed) < len(pretty)
    # Valid json check
    assert json.loads(crushed) == data


def test_code_compressor_redundant_newlines():
    code = """
def my_func():

    
    print('hello')



    return True
"""
    cleaned = CodeCompressor.compress(code)
    assert "\n\n\n" not in cleaned
    assert "print('hello')" in cleaned


def test_ccr_cache_and_reversible_retrieval():
    cache = CCRCache(default_ttl=10)
    original = "This is a detailed payload that was compressed."
    key = cache.put(original)
    assert key.startswith("ccr_")
    assert cache.get(key) == original
    assert cache.get("non_existent") is None


def test_headroom_compressor_pipeline():
    cfg = CompressConfig(
        protect_recent=2,
        min_tokens_to_compress=50,
        frozen_message_count=1,
    )
    long_content = "def calculate():\n\n\n    x = 10\n\n\n    return x\n" * 20
    messages = [
        {"role": "system", "content": "You are Locus OS."},
        {"role": "assistant", "content": long_content},
        {"role": "user", "content": "Recent question?"},
        {"role": "assistant", "content": "Recent response."},
    ]

    result = compress(messages, config=cfg)
    assert len(result.compressed_messages) == 4
    assert result.compressed_token_estimate < result.original_token_estimate
    assert result.compression_ratio < 1.0

    # System message (frozen) is untouched
    assert result.compressed_messages[0]["content"] == "You are Locus OS."
    # Compressible middle message is compressed
    assert result.compressed_messages[1].get("headroom_compressed") is True
    # Recent suffix messages are untouched
    assert result.compressed_messages[2]["content"] == "Recent question?"
    assert result.compressed_messages[3]["content"] == "Recent response."
