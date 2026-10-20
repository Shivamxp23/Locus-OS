# US-38 Spec Trace: Image Generation (§2.9)

| Spec Line | Spec Sentence (Verbatim) | Verdict | Implementation File:Line | Test / Status |
|---|---|---|---|---|
| 2648 | `## Feature §2.9: Image Generation` | KEEP-PI / AUGMENT | `sidecar/providers/image_generation.py:1` | `tests/unit/test_image_generation.py:25` |
| 2649 | `- **Verdict**: 📦 KEEP-PI · **Source**: pi/images.ts · **Repo vs .locus**: locus-os (inherited)` | KEEP-PI | `packages/ai/src/image-models.ts:1`, `sidecar/image_generation.py:35` | `tests/unit/test_image_generation.py:40` |
| 2650 | `- **Off state**: Disable via locus.images.enabled` | AUGMENT | `sidecar/image_generation.py:55`, `sidecar/service.py:1560` | `tests/unit/test_image_generation.py:90`, `tests/integration/test_image_generation_service.py:50` |
| 2651 | `- **Scope**: Built-in image provider registry. Inherited unchanged.` | KEEP-PI | `sidecar/image_generation.py:75`, `locus-extension/src/image-generation.ts:30` | `tests/unit/test_image_generation.py:60` |
| Criteria 1 | `Module implementing Image Generation per §2.9: Image Generation created under sidecar/ or locus-extension/.` | LOCUS-NEW | `sidecar/image_generation.py`, `locus-extension/src/image-generation.ts` | `tests/unit/test_image_generation.py:25` |
| Criteria 2 | `Registers as a provider in sidecar/providers/ with modular off-switch locus.image_generation.enabled returning 503.` | LOCUS-NEW | `sidecar/image_generation.py:160`, `sidecar/service.py:1565` | `tests/unit/test_image_generation.py:110`, `tests/integration/test_image_generation_service.py:50` |
| Criteria 3 | `Unit tests in tests/unit/ assert expected logic, boundary conditions, and error containment.` | LOCUS-NEW | `tests/unit/test_image_generation.py` | `tests/unit/test_image_generation.py:25-150` |
