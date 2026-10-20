/**
 * SPEC §4.1-4.2: Graph-Native Memory Client.
 * Bridges TypeScript agent loop and Context Forge with Locus Neo4j Memory Provider,
 * implementing the POLE+O taxonomy and reasoning audit traces.
 */

export type EntityType = "Person" | "Object" | "Location" | "Event" | "Organization" | "Custom";

export interface POLEEntity {
  id: string;
  name: string;
  type: EntityType;
  properties?: Record<string, any>;
  user_identifier?: string;
}

export interface Relationship {
  source_id: string;
  target_id: string;
  type: string;
  properties?: Record<string, any>;
  weight: number;
}

export interface MemoryEntry {
  entry_id: string;
  content: string;
  entry_type: string;
  entities: POLEEntity[];
  timestamp?: string;
  metadata?: Record<string, any>;
}

export interface GraphQueryResult {
  query: string;
  entities: POLEEntity[];
  relationships: Relationship[];
  context_string: string;
  latency_ms: number;
}

export interface MemoryConfig {
  enabled: boolean;
  provider: string;
  uri: string;
  user: string;
  database: string;
  default_depth: number;
  max_context_tokens: number;
}

export class Neo4jMemoryClient {
  private baseUrl: string;

  constructor(baseUrl: string = "http://localhost:8420") {
    this.baseUrl = baseUrl.replace(/\/+$/, "");
  }

  /**
   * Store a conversation turn, fact, or reflection into graph memory.
   */
  async store(
    content: string,
    entryType: string = "long_term",
    metadata?: Record<string, any>,
  ): Promise<MemoryEntry> {
    const url = `${this.baseUrl}/memory/store`;
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        content,
        entry_type: entryType,
        metadata,
      }),
    });

    if (response.status === 503) {
      throw new Error("Graph memory subsystem is disabled via locus.memory.enabled");
    }

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`Failed to store memory entry (${response.status}): ${errText}`);
    }

    const data = await response.json();
    return data.entry;
  }

  /**
   * Execute hybrid search and graph traversal over POLE+O entities and relationships.
   */
  async query(
    queryText: string,
    limit: number = 10,
    depth: number = 2,
  ): Promise<GraphQueryResult> {
    const url = `${this.baseUrl}/memory/query`;
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query: queryText,
        limit,
        depth,
      }),
    });

    if (response.status === 503) {
      return {
        query: queryText,
        entities: [],
        relationships: [],
        context_string: "Graph memory subsystem is disabled.",
        latency_ms: 0,
      };
    }

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`Failed to query graph memory (${response.status}): ${errText}`);
    }

    const data = await response.json();
    return data.result;
  }

  /**
   * Retrieve formatted graph context block for Context Forge Layer 4 (Graph, 150t).
   */
  async getContext(queryText: string, maxTokens: number = 150): Promise<string> {
    const url = `${this.baseUrl}/memory/context`;
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query: queryText,
        max_tokens: maxTokens,
      }),
    });

    if (response.status === 503) {
      return "Graph memory subsystem disabled.";
    }

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`Failed to fetch graph context (${response.status}): ${errText}`);
    }

    const data = await response.json();
    return data.context || "";
  }

  /**
   * Create or merge a POLE+O entity node.
   */
  async addEntity(entity: POLEEntity): Promise<boolean> {
    const url = `${this.baseUrl}/memory/entity`;
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(entity),
    });

    if (response.status === 503) return false;

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`Failed to add entity (${response.status}): ${errText}`);
    }

    const data = await response.json();
    return Boolean(data.success);
  }

  /**
   * Retrieve entity by ID or name.
   */
  async getEntity(entityIdOrName: string): Promise<POLEEntity | null> {
    const url = `${this.baseUrl}/memory/entity/${encodeURIComponent(entityIdOrName)}`;
    const response = await fetch(url, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    if (response.status === 404 || response.status === 503) {
      return null;
    }

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`Failed to get entity (${response.status}): ${errText}`);
    }

    const data = await response.json();
    return data.entity || null;
  }

  /**
   * Record a reasoning trace and create :TOUCHED audit edges.
   */
  async recordReasoningStep(
    stepName: string,
    touchedEntities: string[],
    toolCalls?: any[],
  ): Promise<string> {
    const url = `${this.baseUrl}/memory/reasoning`;
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        step_name: stepName,
        touched_entities: touchedEntities,
        tool_calls: toolCalls,
      }),
    });

    if (response.status === 503) return "";

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`Failed to record reasoning step (${response.status}): ${errText}`);
    }

    const data = await response.json();
    return data.step_id || "";
  }

  /**
   * Retrieve graph memory diagnostics and schema health.
   */
  async getConfig(): Promise<Record<string, any>> {
    const url = `${this.baseUrl}/memory/config`;
    const response = await fetch(url, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    if (response.status === 503) {
      return { enabled: false, status: "disabled" };
    }

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`Failed to get memory config (${response.status}): ${errText}`);
    }

    return await response.json();
  }
}
