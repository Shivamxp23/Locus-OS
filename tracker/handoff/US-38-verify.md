VERDICT: ACCEPT
Verifier: Claude 3.7 Sonnet

## Guard output
```powershell
py -3 tools/guard/check.py --full
PASS: 0 FAIL, 9 WARN, 0 INFO  (2.6s)
```

## Verify line
```powershell
py -3 tools/tracker/verify.py --only F-0098
features 1 | verified avg 85.0% | old claimed avg 0.0% | integrated+ 1 | proven 0 | overclaims 0 | no-evidence 0
by level: {'INTEGRATED': 1}
guard: PASS {'FAIL': 0, 'WARN': 9, 'INFO': 0}
{"id": "F-0098", "label": "INTEGRATED", "pct": 85, "flags": [], "reasons": ["no recorded proof"], "next": "Run tools/tracker/record_proof.py, then the human adds the printed line to tracker/signoff.yaml."}
```

## Criteria table
| Acceptance Criterion | Code Location | Test Location | Status |
| --- | --- | --- | --- |
| Module implementing Image Generation per §2.9 created under sidecar/ or locus-extension/ | `sidecar/image_generation.py:60`, `locus-extension/src/image-generation.ts:40` | `tests/unit/test_image_generation.py:25`, `tests/integration/test_image_generation_service.py:25` | PASS |
| Registers as a provider in sidecar/providers/ with modular off-switch locus.image_generation.enabled returning 503 | `sidecar/providers/image_generation.py:80`, `sidecar/image_generation.py:125`, `sidecar/service.py:1565` | `tests/unit/test_image_generation.py:80`, `tests/integration/test_image_generation_service.py:55` | PASS |
| Unit tests in tests/unit/ assert expected logic, boundary conditions, and error containment | `sidecar/image_generation.py:60-120` | `tests/unit/test_image_generation.py:25-85` (7 tests) | PASS |
| Model catalog queries for DALL-E, Imagen, SD3, and Flux | `sidecar/image_generation.py:25-55` | `tests/unit/test_image_generation.py:25-45` | PASS |
| Input validation enforcing non-empty/non-whitespace prompts | `sidecar/image_generation.py:85-92` | `tests/unit/test_image_generation.py:58-70` | PASS |
| Image size resolution and normalization to model defaults | `sidecar/image_generation.py:95-102` | `tests/unit/test_image_generation.py:72-82` | PASS |
| Off-switch on `locus.image_generation.enabled` returns 503 across all /images/* endpoints | `sidecar/service.py:1565-1630` | `tests/integration/test_image_generation_service.py:55-75` | PASS |

## Test attack result
Created detached scratch worktree at `../verify-tmp`.
Mutated `sidecar/image_generation.py` to bypass prompt validation (`if not prompt:` replaced with `if False:`).
Ran pytest targeted at `test_generate_image_empty_prompt_raises`:
```powershell
pytest tests/unit/test_image_generation.py -k test_generate_image_empty_prompt_raises
FAILED tests/unit/test_image_generation.py::TestImageGenerationProvider::test_generate_image_empty_prompt_raises
Failed: DID NOT RAISE ValueError
1 failed, 6 deselected in 0.40s
```
Mutation test confirmed that prompt validation tests fail when constraints are removed. Worktree was cleanly removed.

## Findings
1. `sidecar/image_generation.py`: Successfully provides image generation provider contract, size normalization, and deterministic base64 image generation for tests.
2. `locus-extension/src/image-generation.ts`: Client wrapper handles request validation, model query endpoints, and HTTP error normalization.
3. `sidecar/service.py`: Enforces modular 503 off-switch across `/images/generate`, `/images/models`, and `/images/config` when `locus.image_generation.enabled` is false.

## Not checked
- External network requests to commercial image generation endpoints (OpenAI DALL-E, Google Vertex AI) requiring active paid API keys were mocked via deterministic synthetic base64 outputs.
