/**
 * Locus Agent Communication Protocol (ACP) Transport (§9.4) TypeScript companion.
 */

export interface ACPMessage {
  jsonrpc?: string;
  id?: string | number | null;
  method?: string;
  params?: Record<string, any>;
  result?: any;
  error?: { code: number; message: string; data?: any };
}

export class ACPClient {
  private nextId = 1;

  createRequest(method: string, params: Record<string, any>): string {
    const msg: ACPMessage = {
      jsonrpc: '2.0',
      id: this.nextId++,
      method,
      params,
    };
    return JSON.stringify(msg);
  }

  parseResponse(responseStr: string): ACPMessage {
    return JSON.parse(responseStr);
  }
}
