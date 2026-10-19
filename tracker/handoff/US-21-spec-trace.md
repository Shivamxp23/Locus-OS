# US-21 Spec Trace (§1.2: System Prompt Construction)

Feature: `F-0002` (System Prompt Construction)
Source: `packages/coding-agent/src/core/system-prompt.ts`
Canonical Targets: `locus-extension/src/prompt-builder.ts`, `sidecar/prompt_builder.py`, `sidecar/providers/prompt_builder.py`

| Spec Line | Exact Spec Sentence / Pseudocode | Verdict | Target File & Mechanism | Test Name |
| :--- | :--- | :--- | :--- | :--- |
| Line 366 | `promptCwd = options.cwd.replace("\\", "/")` | AUGMENT | `sidecar/prompt_builder.py:build_system_prompt` normalizes backward slashes to forward slashes. | `test_system_prompt_cwd_normalization` |
| Line 367 | `date = formatDate(now())` | AUGMENT | `sidecar/prompt_builder.py:build_system_prompt` formats current date into prompt. | `test_system_prompt_date_formatting` |
| Line 370 | `IF options.customPrompt: prompt = options.customPrompt` | AUGMENT | `sidecar/prompt_builder.py:build_system_prompt` overrides base prompt if customPrompt provided. | `test_system_prompt_custom_prompt_override` |
| Line 372 | `IF options.appendSystemPrompt: prompt += options.appendSystemPrompt` | AUGMENT | `sidecar/prompt_builder.py:build_system_prompt` appends state engine / extra prompt text. | `test_system_prompt_append_system_prompt` |
| Line 375 | `IF options.contextFiles.length > 0: prompt += "<project_context>"` | AUGMENT | `sidecar/prompt_builder.py:build_system_prompt` wraps context files in XML tags. | `test_system_prompt_context_files_xml` |
| Line 381 | `IF "read" tool available AND options.skills.length > 0: prompt += formatSkillsForPrompt(options.skills)` | AUGMENT | `sidecar/prompt_builder.py:format_skills_for_prompt` formats skills when read tool available. | `test_system_prompt_skills_formatting` |
| Line 383 | `prompt += "Current date: {date}\nCurrent working directory: {promptCwd}"` | AUGMENT | `sidecar/prompt_builder.py:build_system_prompt` appends date and CWD footers. | `test_system_prompt_metadata_footers` |
| Line 409 | `Replace the coding-agent system prompt body with Locus's SOUL.md personality context` | LOCUS-NEW | `sidecar/prompt_builder.py:load_personality_context` reads SOUL.md personality context. | `test_system_prompt_soul_personality` |
| Line 412 | `Add Context Forge injection point: the system prompt gets the 800-token assembled context appended` | LOCUS-NEW | `sidecar/prompt_builder.py:inject_context_forge` injects assembled context tokens. | `test_system_prompt_context_forge_injection` |
| Line 413 | `The appendSystemPrompt hook is WHERE the State Engine injects current DCS, operating mode, faction status` | LOCUS-NEW | `sidecar/prompt_builder.py:inject_state_engine` formats DCS, operating mode, and faction metrics. | `test_system_prompt_state_engine_injection` |
| Line 415 | `Lives in locus/core/prompt-builder.ts. Implements Pi's BuildSystemPromptOptions but overrides customPrompt with Locus's personality.` | AUGMENT | `locus-extension/src/prompt-builder.ts` and `sidecar/providers/prompt_builder.py` implement `BasePromptBuilderProvider`. | `test_prompt_builder_provider_interface` |
| Line 35 | `Off state: Modular off-switch locus.prompt_builder.enabled returns 503` | AUGMENT | `sidecar/service.py` returns 503 on `/prompt/*` endpoints when disabled. | `test_prompt_builder_off_switch_503` |
