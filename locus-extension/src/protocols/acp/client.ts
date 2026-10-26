/**
 * SPEC §9.4: Agent Communication Protocol (ACP Client & Transport) (F-0033 / US-64).
 * TypeScript client for JSON-RPC 2.0 ACP task delegation and event streaming.
 */

export interface ACPEvent {
  event_type: "progress" | "text" | "tool_call" | "completed" | "error";
  data: Record<string, any>;
}

export interface ACPInitializeResult {
  protocolVersion: string;
  sessionId: string;
  serverInfo: {
    name: string;
    version: string;
  };
  capabilities: {
    tools: boolean;
    sampling: boolean;
    cancellation: boolean;
    streaming: boolean;
  };
}

export interface ACPExecuteResult {
  status: string;
  target: string;
  session_id: string;
  events: ACPEvent[];
}

export class ACPClient {
  private baseUrl: string;
  private sessionId: string;
  private requestId: number = 0;

  constructor(baseUrl: string = "http://127.0.0.1:8420", sessionId: string = "default-session") {
    this.baseUrl = baseUrl;
    this.sessionId = sessionId;
  }

  private nextId(): number {
    this.requestId += 1;
    return this.requestId;
  }

  async initialize(clientInfo?: Record<string, any>): Promise<ACPInitializeResult> {
    const res = await fetch(`${this.baseUrl}/protocols/acp/initialize`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        client_info: clientInfo || { name: "locus-extension", version: "1.0.0" },
      }),
    });
    if (!res.ok) {
      throw new Error(`ACP initialization failed: ${res.statusText}`);
    }
    const data = await res.json();
    if (data.result?.sessionId) {
      this.sessionId = data.result.sessionId;
    }
    return data.result;
  }

  async dispatchAgentTask(
    targetAgentId: string,
    prompt: string,
    tools?: string[]
  ): Promise<ACPExecuteResult> {
    const res = await fetch(`${this.baseUrl}/protocols/acp/execute`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        target_agent_id: targetAgentId,
        prompt,
        tools: tools || [],
      }),
    });
    if (!res.ok) {
      throw new Error(`ACP task dispatch failed: ${res.statusText}`);
    }
    return await res.json();
  }

  async cancelRequest(requestId: number): Promise<Record<string, any>> {
    const res = await fetch(`${this.baseUrl}/protocols/acp/cancel`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ request_id: requestId }),
    });
    if (!res.ok) {
      throw new Error(`ACP cancellation failed: ${res.statusText}`);
    }
    return await res.json();
  }
}
