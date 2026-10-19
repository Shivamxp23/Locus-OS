# 07 - Tracker and evidence (how "how complete is it?" gets answered without anyone's opinion)

## The one rule
Nobody types a status. `python tools/tracker/verify.py` computes a level per feature from evidence it can check and writes
`tracker/status.json`, `tracker/STATUS.md`, and one line to `tracker/history.jsonl`. The Excel file is a GENERATED view
(`python tools/tracker/export_xlsx.py`); editing it changes nothing and is detected (hash in its `_meta` sheet).
What each feature must do comes from the spec (`show.py F-xxxx --spec`), never from the tracker's own text.

## Levels
| Level | Name | % | What the verifier must see |
|---|---|---|---|
| L0 | NO_EVIDENCE | 0 | nothing named, or the named files are missing |
| L1 | FILES_PRESENT | 15 | every file in `evidence.files` exists |
| L2 | IMPLEMENTED | 40 | every `evidence.symbols` name is defined in real code (not in a comment), no stub body, no `STUB(F-xxxx)` left |
| L3 | UNIT_VERIFIED | 65 | a command in `evidence.unit` with a recognised runner (pytest, unittest, vitest, jest, node --test) whose test file exists, mentions what the feature implements, has real assertions, and passes; or the guard ids in `evidence.guard` pass |
| L4 | INTEGRATED | 85 | a DIFFERENT command in `evidence.integration` that meets the same rules |
| L5 | PROVEN | 100 | a current proof file (`record_proof.py`) AND the owner's entry in `tracker/signoff.yaml` naming that proof |
| - | INHERITED_OK | 100 | KEEP-PI feature, all evidence files under `packages/`, upstream unmodified |
Flags: OVERCLAIM (old workbook claimed 25+ points more than proven), CLAIMED_FILES_MISSING, NO_FILES_NAMED, VACUOUS_TESTS,
PROOF_STALE and SIGNOFF_STALE (code changed after the proof), SPEC_CHANGED, SPEC_REF_DANGLING, INHERITED_INVALID, CAPPED_BY_HUMAN,
LOW_CONFIDENCE_MAPPING (the legacy row only loosely matched a spec section).

## Adding evidence (agents ADD only; never delete or weaken). In `tracker/features.yaml`, under the feature:
~~~yaml
evidence:
  files: [sidecar/vault/livesync_bridge.py]
  symbols:
    - {file: sidecar/vault/livesync_bridge.py, contains: [LiveSyncBridge, resolve_conflict]}
  guard: []
  unit:
    - python -m pytest tests/vault/test_livesync_bridge.py -q
  integration:
    - {cmd: "python -m pytest tests/integration/test_livesync_roundtrip.py -q"}
~~~
A command that is not a recognised runner needs `expect_regex` (text its output must contain). The integration command must differ
from every unit command. A test counts only if the names you built (class, function, route) appear in the test file and it asserts
behaviour. `assert True`, an empty body, a test that only imports, or a test that mocks the function under test = VACUOUS_TESTS.

## Wrong evidence (all seen or one step away)
- A test that still passes when the feature is deleted. Check: break the code on purpose; the test must fail.
- A report saying "done", a screenshot of nothing, or someone else's passing test.
- Listing `packages/` files as evidence for a feature Locus adds. Pointing `files:` at a README.
- Editing `tracker/status.json`, the xlsx, or a feature's `claimed:` block to change a number.

## Commands (repo root)
- `python tools/tracker/show.py F-0007 [--spec]` card for one feature (+ the verbatim spec text); `--find <text>` searches titles.
- `python tools/tracker/verify.py --only F-0007` the line to quote in your handoff. No `--only` = every feature.
  `--static` skips running tests (fast, used by CI). `--fail-on-regression` / `--fail-on-guard` for scripts.
- `python tools/tracker/export_xlsx.py` rewrites the workbook from `status.json`. The first export copies the old workbook to
  `tracker/legacy/replaced-<time>-<name>`.
- `python tools/tracker/record_proof.py F-0007 --note "what I watched"`: OWNER only, after watching the feature work for real; paste the
  printed line into `tracker/signoff.yaml`. `tracker/overrides.yaml` lets the owner cap a level with a written reason.

## Honest limits
The verifier cannot read intent. An agent set on cheating could write a test that passes and means nothing. That is why `tools/`
and the tests of the guard are human-owned, why the owner reads test diffs, why a second model re-checks read-only (prompt P2), and
why only the owner can reach L5. L3 and L4 mean "a real-looking test passes", never "the feature is good".
