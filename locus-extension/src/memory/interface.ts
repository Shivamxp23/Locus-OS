/**
 * Memory Provider Interface & Stackable Memory Manager (SPEC §4.18: Memory Provider Interface).
 * Maps to Hermes agent/memory_provider.py + agent/memory_manager.py adapted for Locus OS.
 * Sidecar endpoints:
 *   GET /memory/provider/config
 *   POST /memory/provider/prefetch
 *   POST /memory/provider/sync-turn
 *   GET /memory/provider/tools
 *   POST /memory/provider/tool-call
 */

export interface ToolDefinition {
  type: string;
  function: {
    name: string;
    description: string;
    parameters: Record<string, any>;
  };
}

export interface MemoryProvider {
  name: string;
  isAvailable(): Promise<boolean>;
  initialize(sessionId: string, runtimeKwargs?: Record<string, any>): Promise<void>;
  systemPromptBlock(): Promise<string>;
  prefetch(query: string, sessionId?: string): Promise<string>;
  queuePrefetch(query: string, sessionId?: string): Promise<void>;
  syncTurn(
    userContent: string,
    assistantContent: string,
    sessionId?: string,
    messages?: Array<Record<string, any>>
  ): Promise<void>;
  getToolSchemas(): Promise<ToolDefinition[]>;
  handleToolCall(toolName: string, args: Record<string, any>): Promise<string>;
  shutdown(): Promise<void>;

  // Optional lifecycle hooks
  onTurnStart?(turnNumber: number, message: Record<string, any>): Promise<void>;
  onSessionEnd?(messages: Array<Record<string, any>>): Promise<void>;
  onSessionSwitch?(newSessionId: string, parentSessionId?: string): Promise<void>;
  onPreCompress?(messages: Array<Record<string, any>>): Promise<string | null>;
  onMemoryWrite?(action: string, target: string, content: any, metadata?: Record<string, any>): Promise<void>;
  onDelegation?(task: string, result: any, childSessionId: string): Promise<void>;
}

export interface MemoryManager {
  registerProvider(
    provider: MemoryProvider,
    sessionId?: string,
    isPrimary?: boolean,
    runtimeKwargs?: Record<string, any>
  ): Promise<boolean>;
  getPrimaryProvider(): MemoryProvider | null;
  getActiveProviders(): MemoryProvider[];
  prefetchAll(query: string, sessionId?: string): Promise<string>;
  queuePrefetchAll(query: string, sessionId?: string): Promise<void>;
  syncTurnAll(
    userContent: string,
    assistantContent: string,
    sessionId?: string,
    messages?: Array<Record<string, any>>
  ): Promise<void>;
  getAllToolSchemas(): Promise<ToolDefinition[]>;
  handleToolCall(toolName: string, args: Record<string, any>): Promise<string>;
  shutdownAll(): Promise<void>;
}

export class MemoryProviderClient {
  private baseUrl: string;

  constructor(baseUrl: string = "http://127.0.0.1:8000") {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  async getConfig(): Promise<Record<string, any>> {
    const res = await fetch(`${this.baseUrl}/memory/provider/config`);
    if (res.status === 503) {
      throw new Error("Memory provider is disabled by configuration");
    }
    if (!res.ok) {
      throw new Error(`Failed to get memory provider config: ${res.status}`);
    }
    return res.json();
  }

  async prefetch(query: string, sessionId?: string): Promise<string> {
    const res = await fetch(`${this.baseUrl}/memory/provider/prefetch`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, session_id: sessionId }),
    });
    if (res.status === 503) {
      throw new Error("Memory provider is disabled by configuration");
    }
    if (!res.ok) {
      throw new Error(`Prefetch failed with status ${res.status}`);
    }
    const data = await res.json();
    return data.context ?? "";
  }

  async syncTurn(
    userContent: string,
    assistantContent: string,
    sessionId?: string,
    messages?: Array<Record<string, any>>
  ): Promise<void> {
    const res = await fetch(`${this.baseUrl}/memory/provider/sync-turn`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_content: userContent,
        assistant_content: assistantContent,
        session_id: sessionId,
        messages,
      }),
    });
    if (res.status === 503) {
      throw new Error("Memory provider is disabled by configuration");
    }
    if (!res.ok) {
      throw new Error(`Sync turn failed with status ${res.status}`);
    }
  }

  async getTools(): Promise<ToolDefinition[]> {
    const res = await fetch(`${this.baseUrl}/memory/provider/tools`);
    if (res.status === 503) {
      throw new Error("Memory provider is disabled by configuration");
    }
    if (!res.ok) {
      throw new Error(`Get tools failed with status ${res.status}`);
    }
    const data = await res.json();
    return data.tools ?? [];
  }

  async handleToolCall(toolName: string, args: Record<string, any>): Promise<string> {
    const res = await fetch(`${this.baseUrl}/memory/provider/tool-call`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tool_name: toolName, args }),
    });
    if (res.status === 503) {
      throw new Error("Memory provider is disabled by configuration");
    }
    if (!res.ok) {
      throw new Error(`Tool call failed with status ${res.status}`);
    }
    const data = await res.json();
    return data.result ?? "";
  }
}
