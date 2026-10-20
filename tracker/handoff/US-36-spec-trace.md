# US-36 Spec Trace: Streaming (SSE) (§2.6a)

| Spec Line | Spec Sentence (Verbatim) | Verdict | Implementation File:Line | Test / Status |
|---|---|---|---|---|
| 2644 | `## Feature §2.6a: Streaming (SSE)` | KEEP-PI / AUGMENT | `sidecar/providers/streaming_sse.py:1` | `tests/unit/test_streaming_sse.py:25` |
| 2645 | `- **Verdict**: 📦 KEEP-PI · **Source**: pi/stream.ts · **Repo vs .locus**: locus-os (inherited)` | KEEP-PI | `packages/agent/src/agent-loop.ts:1` & `sidecar/streaming_sse.py:35` | `tests/unit/test_streaming_sse.py:40` |
| 2646 | `- **Off state**: N/A (core Pi functionality)` | AUGMENT | `sidecar/streaming_sse.py:45` | `tests/unit/test_streaming_sse.py:85` |
| 2647 | `- **Scope**: Built-in SSE streaming. Inherited unchanged.` | KEEP-PI | `sidecar/streaming_sse.py:55` | `tests/unit/test_streaming_sse.py:110` |
| Criteria 1 | `Module implementing Streaming (SSE) per §2.6a: Streaming (SSE) created under sidecar/ or locus-extension/.` | LOCUS-NEW | `sidecar/streaming_sse.py`, `locus-extension/src/streaming-sse.ts` | `tests/unit/test_streaming_sse.py:25` |
| Criteria 2 | `Registers as a provider in sidecar/providers/ with modular off-switch locus.streaming_sse.enabled returning 503.` | LOCUS-NEW | `sidecar/streaming_sse.py:200`, `sidecar/service.py:1440` | `tests/unit/test_streaming_sse.py:140`, `tests/integration/test_streaming_sse_service.py:75` |
| Criteria 3 | `Unit tests in tests/unit/ assert expected logic, boundary conditions, and error containment.` | LOCUS-NEW | `tests/unit/test_streaming_sse.py` | `tests/unit/test_streaming_sse.py:25-180` |
