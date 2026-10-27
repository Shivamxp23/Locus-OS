/**
 * SPEC §18.1-18.4 lines 4112-4216: MCP Registry & Lifecycle Supervisor.
 * Manages registered servers, connection state, and secret ref lifecycle.
 */

export interface McpServerEntry {
  server_id: string;
  name: string;
  transport: "stdio" | "http_remote";
  enabled: boolean;
  connected: boolean;
  reconnect_stats?: {
    attempts: number;
    last_attempt: number;
    backoff: number;
  };
}

export class McpRegistryClient {
  constructor(private readonly baseUrl: string = "http://127.0.0.1:8420") {}

  async listServers(): Promise<McpServerEntry[]> {
    const res = await fetch(`${this.baseUrl}/mcp/servers/list`);
    if (res.status === 503) {
      throw new Error("MCP feature is disabled");
    }
    const data = await res.json();
    return data.servers || [];
  }

  async connectServer(serverId: string): Promise<boolean> {
    const res = await fetch(`${this.baseUrl}/mcp/servers/connect`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ server_id: serverId }),
    });
    if (res.status === 503) {
      throw new Error("MCP feature is disabled");
    }
    const data = await res.json();
    return data.connected === true;
  }

  async disconnectServer(serverId: string): Promise<boolean> {
    const res = await fetch(`${this.baseUrl}/mcp/servers/disconnect`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ server_id: serverId }),
    });
    if (res.status === 503) {
      throw new Error("MCP feature is disabled");
    }
    const data = await res.json();
    return data.disconnected === true;
  }

  async getStatus(): Promise<Record<string, unknown>> {
    const res = await fetch(`${this.baseUrl}/mcp/status`);
    if (res.status === 503) {
      throw new Error("MCP feature is disabled");
    }
    return await res.json();
  }
}
