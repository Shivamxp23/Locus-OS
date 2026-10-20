# US-56 Spec Trace — §4.17: Token Compression (Headroom CCR)

Feature: F-0026 | Verdict: KEEP-PREBUILT | Author model: Gemini Flash

| # | Spec sentence (verbatim) | Verdict | File:line | Test |
|---|---|---|---|---|
| 1 | `headroom/compress.py: One-function API: compress(messages, model, ...) -> CompressResult; CompressConfig knobs` | KEEP-PREBUILT | sidecar/context/headroom_pipeline.py:40-60, 266-380 | test_compress_config_defaults_and_serialization, test_headroom_pipeline_end_to_end_compression |
| 2 | `headroom/transforms/cache_aligner.py: Stabilizes message prefix so provider KV cache still hits` | KEEP-PREBUILT | sidecar/context/headroom_pipeline.py:84-100 | test_cache_aligner_prefix_preservation |
| 3 | `headroom/transforms/content_router.py: Routes each content type to the right compressor` | KEEP-PREBUILT | sidecar/context/headroom_pipeline.py:103-138 | test_content_router_classification |
| 4 | `headroom/transforms/smart_crusher.py: JSON compressor (array dedup, lossless-first + lossy fallback)` | KEEP-PREBUILT | sidecar/context/headroom_pipeline.py:141-185 | test_smart_crusher_json_deduplication |
| 5 | `headroom/transforms/code_compressor.py: Code (AST/structural) compressor` | KEEP-PREBUILT | sidecar/context/headroom_pipeline.py:188-213 | test_code_compressor_structural_comments_and_whitespace |
| 6 | `headroom/transforms/kompress_compressor.py: ML text compressor` | KEEP-PREBUILT | sidecar/context/headroom_pipeline.py:216-237 | test_headroom_pipeline_end_to_end_compression |
| 7 | `headroom/ccr/*: Cache-Compress-Retrieve: reversible; originals cached locally, retrievable within TTL` | KEEP-PREBUILT | sidecar/context/headroom_pipeline.py:240-275 | test_ccr_store_caching_and_retrieval |
| 8 | `Defaults are tuned for coding agents: compress_user_messages=False, protect_recent=4, min_tokens_to_compress=250` | KEEP-PREBUILT | sidecar/context/headroom_pipeline.py:42-45 | test_compress_config_defaults_and_serialization |
| 9 | `Content-aware routing — JSON goes to SmartCrusher, code to CodeCompressor, prose to the ML Kompress model` | KEEP-PREBUILT | sidecar/context/headroom_pipeline.py:315-325 | test_content_router_classification, test_headroom_pipeline_end_to_end_compression |
| 10 | `Reversible (CCR): originals are cached locally with a key; the LLM calls headroom_retrieve(cache_key) to get the full text back on demand, within a TTL.` | KEEP-PREBUILT | sidecar/context/headroom_pipeline.py:328-333, 382-385 | test_ccr_store_caching_and_retrieval, test_service_headroom_retrieve_endpoint |
| 11 | `Inflation guard: if a transform increases token count, Headroom reverts to the originals` | KEEP-PREBUILT | sidecar/context/headroom_pipeline.py:338-360 | test_inflation_guard_reverts_when_compressed_is_larger |
| 12 | `Prompt-cache aware: CacheAligner + frozen_message_count prevent rewriting a prefix the provider is already caching` | KEEP-PREBUILT | sidecar/context/headroom_pipeline.py:284-288 | test_cache_aligner_prefix_preservation |
| 13 | `compress(messages, model, config) -> CompressResult` | KEEP-PREBUILT | sidecar/context/headroom_pipeline.py:266-380 | test_headroom_pipeline_end_to_end_compression, test_service_headroom_compress_endpoint |
| 14 | `headroom_retrieve(cache_key) -> full original text` | KEEP-PREBUILT | sidecar/context/headroom_pipeline.py:382-385 | test_ccr_store_caching_and_retrieval, test_service_headroom_retrieve_endpoint |
| 15 | `Provider Interface: implements CompressionProvider (default); alternates: simple summarization, LOCUS_SHORTHAND, custom.` | KEEP-PREBUILT | sidecar/providers/headroom_ccr.py:23-75 | test_provider_interface_and_off_switch, test_service_headroom_config |
| 16 | `Swappable / off state: locus.compression.provider and locus.compression.enabled; off = raw retrieval text flows straight into Context Forge` | KEEP-PREBUILT | sidecar/service.py:4088-4155 | test_service_headroom_off_switch_503 |

## Scope check
`git diff main...HEAD --stat` files:
- `sidecar/context/headroom_pipeline.py` — new, §4.17 pipeline implementation
- `sidecar/context/__init__.py` — context package re-exports
- `sidecar/providers/headroom_ccr.py` — new, §4.17 provider interface
- `sidecar/providers/__init__.py` — provider re-exports
- `sidecar/service.py` — REST endpoints for Headroom CCR with 503 off-switch
- `locus-extension/src/headroom-ccr.ts` — TypeScript contract
- `tests/unit/test_headroom_ccr.py` — unit tests for rows 1-15
- `tests/integration/test_headroom_ccr_service.py` — integration tests for rows 10, 13, 14, 16
- `tracker/features.yaml` — updated evidence for F-0026

No file or behaviour outside the spec trace.
