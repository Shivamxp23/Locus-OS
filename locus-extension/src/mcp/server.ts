/**
 * SPEC §18.1-18.4 lines 4217-4296: Locus-as-MCP-Server client interface.
 * Dispatches JSON-RPC 2.0 requests to the sidecar's Locus MCP server endpoint.
 */

export interface JsonRpcRequest {
  jsonrpc: "2.0";
  id: string | number;
  method: string;
  params?: Record<string, unknown>;
}

export interface JsonRpcResponse<T = unknown> {
  jsonrpc: "2.0";
  id: string | number;
  result?: T;
  error?: {
    code: number;
    message: string;
    data?: unknown;
  };
}

export class LocusMcpServerClient {
  constructor(private readonly baseUrl: string = "http://127.0.0.1:8420") {}

  async dispatch<T = unknown>(req: JsonRpcRequest): Promise<JsonRpcResponse<T>> {
    const res = await fetch(`${this.baseUrl}/mcp/server/jsonrpc`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
    if (res.status === 503) {
      throw new Error("MCP feature is disabled");
    }
    return (await res.json()) as JsonRpcResponse<T>;
  }

  async ping(): Promise<boolean> {
    const res = await this.dispatch({ jsonrpc: "2.0", id: 1, method: "ping" });
    return !res.error;
  }
}
