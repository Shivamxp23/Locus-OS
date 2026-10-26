# US-67 Spec Traceability Matrix

## Feature
- ID: F-0121
- Title: Agent Experience Tracking (Procedural Memory)
- Spec Reference: §10.9 lines 6356-6430

## Traceability Mapping

| Spec Requirement | Spec Line | Implementation | Test Coverage |
|------------------|-----------|----------------|---------------|
| AgentExperience record structure | 6368-6379 | `sidecar/experience/procedural.py:AgentExperience` | `tests/unit/test_agent_experience.py:test_experience_store_upsert_and_redaction` |
| Deterministic dedupe (`stable_experience_id`) | 6380-6383 | `sidecar/experience/procedural.py:stable_experience_id` | `tests/unit/test_agent_experience.py:test_stable_experience_id` |
| Text redaction for keys & secrets | 6384-6385 | `sidecar/experience/procedural.py:redact_text` | `tests/unit/test_agent_experience.py:test_redact_text_scrubbing` |
| Candidate extractor: Multi-tool success (>=2 calls, conf 0.72) | 6389-6390 | `sidecar/experience/procedural.py:AgentExperienceCaptureHook` | `tests/unit/test_agent_experience.py:test_candidate_extraction_success_sequence` |
| Candidate extractor: Repeated failure (>=2 failures, conf 0.68) | 6391-6392 | `sidecar/experience/procedural.py:AgentExperienceCaptureHook` | `tests/unit/test_agent_experience.py:test_candidate_extraction_repeated_failure` |
| Candidate extractor: Partial success (recovery, conf 0.62) | 6393-6394 | `sidecar/experience/procedural.py:AgentExperienceCaptureHook` | `tests/unit/test_agent_experience.py:test_candidate_extraction_partial_success` |
| ExperienceStore upsert and query | 6380-6385 | `sidecar/experience/procedural.py:ExperienceStore` | `tests/unit/test_agent_experience.py:test_experience_store_upsert_and_redaction` |
| Context injection rendering and prepend | 6395-6398 | `sidecar/experience/procedural.py:render_experience_hits`, `prepend_experience_block` | `tests/unit/test_agent_experience.py:test_render_and_prepend_experience_block` |
| Modular off-switches (503) | 6407-6409 | `sidecar/providers/agent_experience.py:DefaultAgentExperienceProvider`, `sidecar/service.py` | `tests/unit/test_agent_experience.py:test_provider_off_switches`, `tests/integration/test_agent_experience_service.py:test_service_experience_off_switches` |
| Service routes (`/experience/record`, `/query`, `/render`, `/list`) | 6386-6425 | `sidecar/service.py` | `tests/integration/test_agent_experience_service.py` |
| Extension client contract | 6399-6401 | `locus-extension/src/experience/client.ts:AgentExperienceClient` | TypeScript contract |
