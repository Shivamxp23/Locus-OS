/**
 * SPEC §10.9 lines 6356-6430:
 * Agent Experience Tracking (Procedural Memory) Client (F-0121 / US-67).
 * TypeScript contract and client for recording tool execution experiences,
 * querying procedural memories, and rendering context injection blocks.
 */

export type ExperienceSource = "ToolLoop" | "AgentReflection" | "Manual" | "WorkflowCandidate";
export type ExperienceOutcome = "Success" | "Failure" | "Partial";

export interface AgentExperience {
  id: string;
  source: ExperienceSource;
  agent_id: string;
  entrypoint: string;
  task_fingerprint: string;
  task_summary: string;
  tools_used: string[];
  tool_sequence: string[];
  outcome: ExperienceOutcome;
  lesson: string;
  confidence: number;
  reuse_hint?: string | null;
  avoid_hint?: string | null;
  error_class?: string | null;
  tags: string[];
  dismissed: boolean;
  created_at: string;
}

export interface CaptureTurnContext {
  task_summary: string;
  task_fingerprint?: string;
  agent_id?: string;
  entrypoint?: string;
  tool_calls: Array<{
    name: string;
    status?: "success" | "ok" | "error" | "failed";
    error?: string;
    output_summary?: string;
  }>;
}

export interface RenderBlockResult {
  status: "ok" | "disabled";
  hits_count: number;
  block: string;
  prepended_message: string;
}

export class AgentExperienceClient {
  private baseUrl: string;

  constructor(baseUrl: string = "http://127.0.0.1:8420") {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  /**
   * SPEC §10.9 lines 6386-6415:
   * Post-turn capture hook: record tool execution candidates.
   */
  async record(turnContext: CaptureTurnContext): Promise<{ status: string; extracted_count: number; experiences: AgentExperience[] }> {
    const url = `${this.baseUrl}/experience/record`;
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(turnContext),
    });
    if (resp.status === 503) {
      return { status: "disabled", extracted_count: 0, experiences: [] };
    }
    if (!resp.ok) {
      throw new Error(`Agent experience record failed with status ${resp.status}`);
    }
    return (await resp.json()) as { status: string; extracted_count: number; experiences: AgentExperience[] };
  }

  /**
   * SPEC §10.9 lines 6417-6425:
   * Query procedural memories by task fingerprint or keywords.
   */
  async query(taskFingerprint: string, limit: number = 5): Promise<AgentExperience[]> {
    const url = `${this.baseUrl}/experience/query`;
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task_fingerprint: taskFingerprint, limit }),
    });
    if (resp.status === 503) {
      return [];
    }
    if (!resp.ok) {
      throw new Error(`Agent experience query failed with status ${resp.status}`);
    }
    const data = (await resp.json()) as { status: string; experiences: AgentExperience[] };
    return data.experiences || [];
  }

  /**
   * SPEC §10.9 lines 6417-6425:
   * Render compact Relevant Operating Experience block prepended to message.
   */
  async render(taskFingerprint: string, message: string = "", limit: number = 5): Promise<RenderBlockResult> {
    const url = `${this.baseUrl}/experience/render`;
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task_fingerprint: taskFingerprint, message, limit }),
    });
    if (resp.status === 503) {
      return {
        status: "disabled",
        hits_count: 0,
        block: "",
        prepended_message: message,
      };
    }
    if (!resp.ok) {
      throw new Error(`Agent experience render failed with status ${resp.status}`);
    }
    return (await resp.json()) as RenderBlockResult;
  }

  /**
   * SPEC §10.9 lines 6370-6385:
   * List stored experiences.
   */
  async list(limit: number = 50): Promise<AgentExperience[]> {
    const url = `${this.baseUrl}/experience/list?limit=${limit}`;
    const resp = await fetch(url, {
      method: "GET",
    });
    if (resp.status === 503) {
      return [];
    }
    if (!resp.ok) {
      throw new Error(`Agent experience list failed with status ${resp.status}`);
    }
    const data = (await resp.json()) as { status: string; experiences: AgentExperience[] };
    return data.experiences || [];
  }
}
