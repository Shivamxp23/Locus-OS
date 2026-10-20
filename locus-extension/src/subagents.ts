/**
 * SPEC §11.1-11.5 + §3.7: Subagents and AutoResearch client for Locus Extension.
 * Handles subagent spawning with depth bounding (MAX_SPAWN_DEPTH=3),
 * archetype queries, and AutoResearch topic synthesis.
 */

export const MAX_SPAWN_DEPTH = 3;

export type ArchetypeCategory = "faction" | "openhuman" | "custom";

export interface SubagentArchetype {
  name: string;
  description: string;
  category: ArchetypeCategory;
  system_prompt: string;
  allowed_tools: string[];
  default_model: string;
  max_turns: number;
}

export interface SubagentSpawnRequest {
  task: string;
  archetype: string;
  parent_session_id?: string;
  current_depth?: number;
  model_override?: string;
  context_extra?: Record<string, any>;
  max_turns_override?: number;
}

export interface SubagentSpawnResult {
  session_id: string;
  parent_session_id?: string;
  archetype: string;
  depth: number;
  status: string;
  output: string;
  turns_used: number;
  skip_memory: boolean;
  skip_review: boolean;
  delegated_tasks: any[];
  error?: string;
}

export interface AutoResearchRequest {
  topic: string;
  depth_mode?: "quick" | "deep";
  hypotheses?: string[];
  parent_session_id?: string;
}

export interface AutoResearchResult {
  topic: string;
  depth_mode: string;
  summary: string;
  findings: Array<Record<string, any>>;
  subagents_spawned: number;
  status: string;
  error?: string;
}

export class SubagentsClient {
  private baseUrl: string;

  constructor(baseUrl: string = "http://localhost:8000") {
    this.baseUrl = baseUrl.replace(/\/+$/, "");
  }

  /**
   * Spawns an isolated subagent under a parent session.
   * Enforces MAX_SPAWN_DEPTH = 3 before dispatch.
   */
  async spawn(request: SubagentSpawnRequest): Promise<SubagentSpawnResult> {
    const currentDepth = request.current_depth ?? 0;
    if (currentDepth >= MAX_SPAWN_DEPTH) {
      throw new Error(`Maximum subagent depth reached: ${currentDepth} >= ${MAX_SPAWN_DEPTH}`);
    }

    const response = await fetch(`${this.baseUrl}/subagents/spawn`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });

    if (response.status === 503) {
      throw new Error("subagents_autoresearch_disabled");
    }
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(err.detail || `Subagent spawn failed with status ${response.status}`);
    }

    return (await response.json()) as SubagentSpawnResult;
  }

  /**
   * Retrieves list of registered archetypes (factions and OpenHuman).
   */
  async getArchetypes(category?: string): Promise<SubagentArchetype[]> {
    const url = new URL(`${this.baseUrl}/subagents/archetypes`);
    if (category) {
      url.searchParams.set("category", category);
    }
    const response = await fetch(url.toString());
    if (response.status === 503) {
      throw new Error("subagents_autoresearch_disabled");
    }
    if (!response.ok) {
      throw new Error(`Failed to fetch archetypes: ${response.statusText}`);
    }
    const data = await response.json();
    return data.archetypes as SubagentArchetype[];
  }

  /**
   * Retrieves subagents and AutoResearch configuration.
   */
  async getConfig(): Promise<{ status: string; max_spawn_depth: number; enabled: boolean }> {
    const response = await fetch(`${this.baseUrl}/subagents/config`);
    if (response.status === 503) {
      return { status: "disabled", max_spawn_depth: MAX_SPAWN_DEPTH, enabled: false };
    }
    if (!response.ok) {
      throw new Error(`Failed to fetch config: ${response.statusText}`);
    }
    return await response.json();
  }

  /**
   * Executes AutoResearch topic investigation loop.
   */
  async autoResearch(request: AutoResearchRequest): Promise<AutoResearchResult> {
    const response = await fetch(`${this.baseUrl}/subagents/autoresearch`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });

    if (response.status === 503) {
      throw new Error("subagents_autoresearch_disabled");
    }
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(err.detail || `AutoResearch failed with status ${response.status}`);
    }

    return (await response.json()) as AutoResearchResult;
  }
}
