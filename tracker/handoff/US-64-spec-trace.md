# US-64 Spec Trace — §9.4: Agent Communication Protocol (ACP Client & Transport)

Feature: F-0033 | Verdict: LOCUS-NEW | Author model: Claude Opus 4.6

| # | Spec sentence (verbatim) | Verdict | File:line | Test |
|---|---|---|---|---|
| 1 | `CLASS ACPClient: transport: StdioTransport | WebSocketTransport, session_id: string, request_id: int = 0, pending_requests: Dict[int -> Future]` | LOCUS-NEW | sidecar/acp_server.py:114-177, locus-extension/src/protocols/acp/client.ts:31-95 | test_acp_client_initialize_and_dispatch |
| 2 | `FUNCTION initialize(client_info: Dict) -> Dict: payload = { "jsonrpc": "2.0", "id": self.next_id(), "method": "initialize", "params": { "protocolVersion": "1.0", "clientInfo": { "name": "locus-os", "version": "1.0.0" }, "capabilities": { "tools": True, "sampling": True, "cancellation": True } } }` | LOCUS-NEW | sidecar/acp_server.py:64-92, 126-150 | test_acp_server_handle_initialize, test_service_acp_initialize |
| 3 | `FUNCTION dispatch_agent_task(target_agent_id: string, prompt: string, tools: List) -> AsyncIterator[ACPEvent]:` | LOCUS-NEW | sidecar/acp_server.py:94-123, 152-171 | test_acp_server_handle_execute, test_service_acp_execute_and_cancel |
| 4 | `IF response.method == "$/progress": YIELD ACPEvent.PROGRESS(response.params); ELIF response.method == "$/streamText": YIELD ACPEvent.TEXT(response.params.chunk); ELIF response.method == "$/toolCall": YIELD ACPEvent.TOOL_CALL(response.params)` | LOCUS-NEW | sidecar/acp_server.py:108-112 | test_acp_server_handle_execute |
| 5 | `FUNCTION cancel_request(req_id: int): notification = { "jsonrpc": "2.0", "method": "$/cancelRequest", "params": { "requestId": req_id } }` | LOCUS-NEW | sidecar/acp_server.py:125-132, 173-177 | test_acp_server_handle_cancel, test_service_acp_execute_and_cancel |
| 6 | `Component: locus-os/src/protocols/acp/client.ts -> locus-extension/src/protocols/acp/client.ts` | LOCUS-NEW | locus-extension/src/protocols/acp/client.ts:1-96 | test_service_acp_initialize |
| 7 | `Provider Interface: ACPClientProvider` | LOCUS-NEW | sidecar/providers/acp_protocol.py:17-45 | test_acp_provider_off_switch |
| 8 | `Swappable / off state: locus.acp_protocol.enabled. Off -> 503 HTTP off-switch on ACP endpoints.` | LOCUS-NEW | sidecar/providers/acp_protocol.py:47-92, sidecar/service.py:4945-5020 | test_acp_provider_off_switch, test_service_acp_off_switch_503 |

## Scope check
`git diff main...HEAD --stat` files:
- `sidecar/acp_server.py` — §9.4 ACPServer, ACPClient, and ACPEvent
- `sidecar/providers/acp_protocol.py` — BaseACPClientProvider & DefaultACPClientProvider
- `sidecar/providers/__init__.py` — provider module re-exports
- `locus-extension/src/protocols/acp/client.ts` — TypeScript ACPClient contract
- `sidecar/service.py` — REST endpoints (`/protocols/acp/initialize`, `/execute`, `/cancel`) with 503 off-switch
- `tests/unit/test_acp_protocol.py` — unit tests for rows 1-5, 7, 8
- `tests/integration/test_acp_protocol_service.py` — integration tests for rows 2, 3, 5, 6, 8
- `tracker/features.yaml` — updated evidence for F-0033

No file or behaviour outside the spec trace.
