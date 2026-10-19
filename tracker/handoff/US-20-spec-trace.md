# US-20 Spec Trace

| spec line / source | the sentence quoted word for word | verdict | mechanism / file:line | test name |
|---|---|---|---|---|
| SPEC §03 line 18 | "HarnessProvider registered behind BaseHarnessProvider interface." | LOCUS-NEW | sidecar/harness/delegation.py:30-70, sidecar/providers/harness.py:55-95 | tests/unit/test_harness_delegation.py::test_base_harness_provider_interface |
| SPEC §3.7 line 2760 | "Select harness based on availability and task type (Antigravity, Claude Code, OpenCode, Pi)" | LOCUS-NEW | sidecar/harness/delegation.py:75-95 | tests/unit/test_harness_delegation.py::test_harness_selection_matrix |
| SPEC §3.7 line 2765 | "Build CLI command arguments for selected harness." | LOCUS-NEW | sidecar/harness/delegation.py:97-125 | tests/unit/test_harness_delegation.py::test_format_command_args_construction |
| SPEC §10 line 45 / S-3 | "--dangerously-skip-permissions is rejected per security policy." | LOCUS-NEW | sidecar/harness/delegation.py:102-125 | tests/unit/test_harness_delegation.py::test_forbidden_permission_flag_rejection |
| SPEC §3.7 line 2785 | "Execute harness as subprocess in scratch worktree and capture diffs." | LOCUS-NEW | sidecar/harness/delegation.py:127-230 | tests/unit/test_harness_delegation.py::test_execute_delegation_in_scratch_worktree, tests/integration/test_harness_service.py::test_harness_service_endpoints |
| SPEC §3.7 line 2800 | "Return error and stderr when harness subprocess exits non-zero." | LOCUS-NEW | sidecar/harness/delegation.py:200-240 | tests/unit/test_harness_delegation.py::test_execute_delegation_subprocess_failure |
| SPEC §3.7 line 2810 | "InterHarnessBridge delegates task via active provider." | LOCUS-NEW | sidecar/inter_harness_bridge.py:20-65 | tests/unit/test_harness_delegation.py::test_inter_harness_bridge_integration |
| SPEC §03 line 35 | "a disabled feature's HTTP routes answer 503 with {'disabled': '<config key>'}" | LOCUS-NEW | sidecar/service.py:330-385 | tests/unit/test_harness_delegation.py::test_harness_delegation_off_switch, tests/integration/test_harness_service.py::test_harness_service_modular_off_switch |
