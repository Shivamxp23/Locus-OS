# US-11 Spec Trace

| spec line / source | the sentence quoted word for word | verdict | mechanism / file:line | test name |
|---|---|---|---|---|
| User requirement R1 / R9 | "install.ps1 and install.sh are thin launchers; one Python installer" | LOCUS-NEW | install.ps1:1-20, install.sh:1-15, locus_cli/install.py:1-200 | tests/unit/test_install.py::test_launchers_exist_at_repo_root_and_reference_installer |
| User requirement R10 | "Validates prerequisites: Python 3, Node 18+, Docker (if mode requires it), and git." | LOCUS-NEW | locus_cli/install.py:33-85 | tests/unit/test_install.py::test_prerequisites_validation |
| User requirement R10 | "locus_cli/install.py supports non-interactive mode via --yes --answers <file.json>." | LOCUS-NEW | locus_cli/install.py:87-190 | tests/unit/test_install.py::test_non_interactive_install_creates_directories_and_config |
| User requirement R1 | "Run the installer twice and show both outputs; the second run must change nothing." | LOCUS-NEW | locus_cli/install.py:140-170 | tests/unit/test_install.py::test_installer_is_idempotent |
| User requirement R1 / demo | "Run py -3 -m locus_cli.install --yes --answers tests/fixtures/install_answers.json --target-dir <temp_dir>: creates config.yaml and exits 0." | LOCUS-NEW | locus_cli/install.py:192-235 | tests/unit/test_install.py::test_cli_invocation_with_answers_file |
