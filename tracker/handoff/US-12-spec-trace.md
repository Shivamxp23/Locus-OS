# US-12 Spec Trace

| spec line / source | the sentence quoted word for word | verdict | mechanism / file:line | test name |
|---|---|---|---|---|
| User requirement R2 | "First question: mode local, vm, or hybrid (backend on a VM, TUI on this computer). The mode only changes config and which services start" | LOCUS-NEW | locus_cli/install.py:226-241 | tests/unit/test_install.py::test_interactive_mode_and_masked_keys |
| User requirement R3 | "API keys: asks for each LLM provider key, the Telegram bot token, and any channel token. Validates each with one cheap live call before saving. Writes only to LOCUS_HOME/.env (file mode 0600). Never to the repo, a log, a prompt, or terminal history (input is masked)." | LOCUS-NEW | locus_cli/install.py:98-162, 197-224, 243-287 | tests/unit/test_install.py::test_key_validation_live_and_mock, test_interactive_mode_and_masked_keys |
| User requirement R8 | "Re-running is safe: existing config and keys are kept; --reconfigure <section> changes one section; nothing is overwritten without a prompt." | LOCUS-NEW | locus_cli/install.py:290-394 | tests/unit/test_install.py::test_safe_reconfigure_topology_and_keys |
| User requirement R8 / demo | "Run py -3 -m locus_cli.install --reconfigure topology --target-dir <temp_dir>: prompts for mode, records updated topology to config.yaml, and preserves existing .env keys." | LOCUS-NEW | locus_cli/install.py:408-450 | tests/unit/test_install.py::test_cli_reconfigure_invocation |
