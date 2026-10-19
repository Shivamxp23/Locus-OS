# US-07 Spec Trace

| spec line / source | the sentence quoted word for word | verdict | mechanism / file:line | test name |
|---|---|---|---|---|
| SPEC §17.1-17.11 line 3950 | "EVERY channel adapter MUST implement: name, initialize, send_message, receive_messages, is_connected, shutdown" | AUGMENT | sidecar/providers/channel.py:11, sidecar/telegram/gateway.py:46 | tests/unit/test_telegram_gateway.py::test_telegram_gateway_implements_channel_provider |
| SPEC §17.1-17.11 line 4000 | "TELEGRAM ADAPTER (Locus primary channel) ... paired owner message gets a Pi turn" | AUGMENT | sidecar/telegram/gateway.py:190 | tests/unit/test_telegram_gateway.py::test_paired_owner_message_triggers_pi_turn_and_replies |
| SPEC §17.1-17.11 line 3975 | "MAX_MESSAGE_LENGTH = 4096 // Telegram limit" | AUGMENT | sidecar/telegram/gateway.py:22, 230 | tests/unit/test_telegram_gateway.py::test_long_message_chunking_under_4096_chars, test_chunk_telegram_text_helper |
| SPEC §10 S-1 line 18 | "Until paired the bot answers every message with one fixed line (\"not configured\") and executes nothing." | AUGMENT | sidecar/telegram/gateway.py:215 | tests/unit/test_telegram_gateway.py::test_stranger_message_gets_fixed_line_and_no_pi_turn, tests/unit/test_telegram_pairing.py::test_stranger_first_message_rejected |
| SPEC §03 / §08 F-0125 | "When a feature's enabled switch is false ... processes no messages" | AUGMENT | sidecar/telegram/gateway.py:75, 155 | tests/unit/test_telegram_gateway.py::test_disabled_telegram_gateway_suppresses_processing |
| SPEC §10 S-1 line 22 | "Messages from other ids, groups, forwards, and inline queries are ignored." | AUGMENT | sidecar/telegram/gateway.py:165-175 | tests/unit/test_telegram_gateway.py::test_filter_groups_and_forwards_and_non_private |
