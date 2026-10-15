/**
 * locus-extension/src/mcp/client.ts - MCP TypeScript client.
 *
 * Implements Spec §18.1-18.5
 */

export interface McpJsonRpcRequest {
  jsonrpc: "2.0";
  id: number;
  method: string;
  params?: Record<string, unknown>;
}

export class McpClientProtocol {
  public static createToolCallRequest(id: number, toolName: string, args: Record<string, unknown>): McpJsonRpcRequest {
    return {
      jsonrpc: "2.0",
      id,
      method: "tools/call",
      params: {
        name: toolName,
        arguments: args,
      },
    };
  }
}
