/**
 * SPEC §18.1-18.4 lines 4060-4111: MCP Client transport interfaces.
 * Connects to external MCP servers (stdio or streamable HTTP) with sanitized tool definitions.
 */

export interface McpTool {
  name: string;
  description: string;
  inputSchema: Record<string, unknown>;
  serverId?: string;
}

export interface McpToolCallResult {
  content: Array<{
    type: string;
    text?: string;
    data?: string;
    mimeType?: string;
  }>;
  isError?: boolean;
}

export interface McpClient {
  name: string;
  isConnected: boolean;
  initialize(): Promise<{ protocolVersion: string; serverInfo: { name: string; version: string } }>;
  listTools(): Promise<McpTool[]>;
  callTool(name: string, args?: Record<string, unknown>): Promise<McpToolCallResult>;
  disconnect(): Promise<void>;
}

export class LocusMcpClient implements McpClient {
  public isConnected = false;

  constructor(
    public readonly name: string,
    private readonly baseUrl: string = "http://127.0.0.1:8420"
  ) {}

  async initialize(): Promise<{ protocolVersion: string; serverInfo: { name: string; version: string } }> {
    this.isConnected = true;
    return {
      protocolVersion: "2025-11-25",
      serverInfo: { name: this.name, version: "1.0.0" },
    };
  }

  async listTools(): Promise<McpTool[]> {
    const res = await fetch(`${this.baseUrl}/mcp/tools/list`);
    if (res.status === 503) {
      throw new Error("MCP feature is disabled");
    }
    const data = await res.json();
    return data.tools || [];
  }

  async callTool(name: string, args?: Record<string, unknown>): Promise<McpToolCallResult> {
    const res = await fetch(`${this.baseUrl}/mcp/tools/call`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ server_id: this.name, tool_name: name, arguments: args || {} }),
    });
    if (res.status === 503) {
      throw new Error("MCP feature is disabled");
    }
    const data = await res.json();
    return data.result || { content: [], isError: true };
  }

  async disconnect(): Promise<void> {
    this.isConnected = false;
  }
}
