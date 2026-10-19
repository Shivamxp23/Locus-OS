# US-17 Spec Trace

| spec line / source | the sentence quoted word for word | verdict | mechanism / file:line | test name |
|---|---|---|---|---|
| SPEC §19.2 line 10 | "TRAJECTORY RECORDING — Full conversation recording for batch evaluation" | AUGMENT | sidecar/learning/trajectory.py:70-280, sidecar/providers/trajectory.py:15-65 | tests/unit/test_trajectory.py::test_trajectory_recorder_implements_interface |
| SPEC §19.2 line 15 | "FOR EACH turn IN session.turns: trajectory.messages.append(...); write_json(session.trajectory_path, compressed)" | AUGMENT | sidecar/learning/trajectory.py:145-215, sidecar/providers/trajectory.py:15-50 | tests/unit/test_trajectory.py::test_trajectory_record_turns_and_flush |
| SPEC §19.2 line 25 | "Trajectory recording writes one record per turn, redacted" | AUGMENT | sidecar/learning/trajectory.py:27-65, 150-170, locus-extension/src/trajectory.ts:38-50 | tests/unit/test_trajectory.py::test_trajectory_redacts_sensitive_keys_and_tokens |
| SPEC §19.2 line 22 | "Compress for storage: compressed = trajectory_compressor.compress(trajectory)" | AUGMENT | sidecar/learning/trajectory.py:180-220 | tests/unit/test_trajectory.py::test_trajectory_compression |
| SPEC §19.2 line 35 | "BATCH EVALUATION: FUNCTION batch_evaluate(trajectories, eval_prompt)" | AUGMENT | sidecar/learning/trajectory.py:235-305 | tests/unit/test_trajectory.py::test_trajectory_batch_evaluation_metrics |
| SPEC §03 line 35 | "a disabled feature's HTTP routes answer 503 with {'disabled': '<config key>'}" | LOCUS-NEW | sidecar/service.py:130-205 | tests/unit/test_trajectory.py::test_trajectory_off_switch, tests/integration/test_trajectory_service.py::test_trajectory_service_off_switch_returns_503 |
