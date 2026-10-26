# US-74 Spec Traceability Matrix

## Feature
- ID: F-0042
- Title: Think Token Scrubbing
- Spec Reference: §13.9 lines 3513-3598

## Traceability Mapping

| Spec Requirement | Spec Line | Implementation | Test Coverage |
|------------------|-----------|----------------|---------------|
| `SUPPORTED_TAGS`: ["think", "thinking", "reasoning", "thought", "REASONING_SCRATCHPAD"] | 3532 | `sidecar/security/think_scrubber.py:SUPPORTED_TAGS`, `locus-extension/src/security/think-scrubber.ts:SUPPORTED_TAGS` | `tests/unit/test_think_scrubber.py:test_streaming_scrubber_all_supported_tags`, `tests/integration/test_think_scrubber_service.py:test_service_think_scrubber_tags` |
| Streaming state machine (`ScrubState`: NORMAL, PENDING_TAG, INSIDE_BLOCK) | 3534-3536 | `sidecar/security/think_scrubber.py:ScrubState`, `StreamingThinkScrubber` | `tests/unit/test_think_scrubber.py:test_streaming_scrubber_removes_think_block` |
| `feed(delta_text) -> visible_text`: streaming delta feed across chunk boundaries | 3538-3566 | `sidecar/security/think_scrubber.py:StreamingThinkScrubber.feed` | `tests/unit/test_think_scrubber.py:test_streaming_scrubber_partial_tags_across_deltas`, `tests/integration/test_think_scrubber_service.py:test_service_think_scrubber_feed_and_flush` |
| Block-boundary rule: `is_block_boundary()` (start of stream, newline, whitespace) | 3554-3556 | `sidecar/security/think_scrubber.py:StreamingThinkScrubber._is_block_boundary` | `tests/unit/test_think_scrubber.py:test_block_boundary_newline_triggers_block` |
| Prose mention preservation (emit tag as text if not at block boundary) | 3557-3561 | `sidecar/security/think_scrubber.py:StreamingThinkScrubber.feed` | `tests/unit/test_think_scrubber.py:test_block_boundary_prose_mention_preserved` |
| Closing tag matching and unclosed block suppression at stream termination | 3563-3566 | `sidecar/security/think_scrubber.py:StreamingThinkScrubber.feed` | `tests/unit/test_think_scrubber.py:test_unclosed_block_at_end_of_stream` |
| `flush() -> visible_text`: emit held-back non-tag buffer | 3568-3574 | `sidecar/security/think_scrubber.py:StreamingThinkScrubber.flush` | `tests/unit/test_think_scrubber.py:test_incomplete_tag_flushed_as_plain_text`, `tests/integration/test_think_scrubber_service.py:test_service_think_scrubber_feed_and_flush` |
| `reset()`: reset state per turn | 3576-3579 | `sidecar/security/think_scrubber.py:StreamingThinkScrubber.reset` | `tests/unit/test_think_scrubber.py:test_streaming_scrubber_all_supported_tags`, `tests/integration/test_think_scrubber_service.py:test_service_think_scrubber_feed_and_flush` |
| Modular Off-switches (`locus.think_token_scrubbing.enabled`, `locus.security.think_scrubbing.enabled`) | 3591 | `sidecar/providers/think_scrubber.py:DefaultThinkScrubberProvider`, `sidecar/service.py` | `tests/unit/test_think_scrubber.py:test_provider_modular_off_switches`, `tests/integration/test_think_scrubber_service.py:test_service_think_scrubber_off_switches` |
| Service Routes (`/security/think_scrubber/feed`, `/flush`, `/scrub_complete`, `/reset`, `/tags`) | 3590-3595 | `sidecar/service.py` | `tests/integration/test_think_scrubber_service.py` |
| Extension Client Contract | 3588 | `locus-extension/src/security/think-scrubber.ts:ThinkScrubberClient` | TypeScript contract and client |
