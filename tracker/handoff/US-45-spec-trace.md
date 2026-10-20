# US-45 Spec Trace: Custom Locus Tools (§3.12)

| Spec Line | Spec Sentence (Verbatim) | Verdict | Implementation File:Line | Test / Status |
|---|---|---|---|---|
| 2706 | `## Feature §3.12: Custom Locus Tools` | LOCUS-NEW / AUGMENT | `sidecar/providers/custom_locus_tools.py:1` | `tests/unit/test_custom_locus_tools.py:18` |
| 2707 | `- **Verdict**: 🆕 LOCUS-NEW · **Source**: Locus-unique · **Repo vs .locus**: locus-os/tools/` | LOCUS-NEW | `sidecar/custom_locus_tools.py:25`, `locus-extension/src/custom-locus-tools.ts:35` | `tests/unit/test_custom_locus_tools.py:75`, `tests/integration/test_custom_locus_tools_service.py:40` |
| 2708 | `- **Swappable / off state**: Individual tools toggleable via locus.tools.<name>.enabled` | LOCUS-NEW | `sidecar/custom_locus_tools.py:175`, `sidecar/service.py:2370` | `tests/unit/test_custom_locus_tools.py:45`, `tests/integration/test_custom_locus_tools_service.py:65` |
| 2709 | `- **Scope**: See §1.3 for the 8 custom Locus tools.` | LOCUS-NEW | `sidecar/custom_locus_tools.py:20`, `locus-extension/src/custom-locus-tools.ts:25` | `tests/unit/test_custom_locus_tools.py:20`, `tests/integration/test_custom_locus_tools_service.py:20` |
| Criteria 1 | `Module implementing Custom Locus Tools per §3.12: Custom Locus Tools created under sidecar/ or locus-extension/.` | LOCUS-NEW | `sidecar/custom_locus_tools.py`, `locus-extension/src/custom-locus-tools.ts` | `tests/unit/test_custom_locus_tools.py:20` |
| Criteria 2 | `Registers as a provider in sidecar/providers/ with modular off-switch locus.custom_locus_tools.enabled returning 503.` | LOCUS-NEW | `sidecar/providers/custom_locus_tools.py:1`, `sidecar/service.py:2352` | `tests/unit/test_custom_locus_tools.py:160`, `tests/integration/test_custom_locus_tools_service.py:90` |
| Criteria 3 | `Unit tests in tests/unit/ assert expected logic, boundary conditions, and error containment.` | LOCUS-NEW | `tests/unit/test_custom_locus_tools.py` | `tests/unit/test_custom_locus_tools.py:18-180` |
