/**
 * Coding Context Engine Contract (SPEC §6.3: Coding Context Engine (Repo Map, AST Index, Active Diff)).
 * Maps to canonical locus-extension/src/context/coding-context.ts and sidecar endpoints:
 *   GET /context/coding/config
 *   POST /context/coding/state
 *   POST /context/coding/format
 */

export interface WorkspaceCodingState {
  repo_root: string;
  active_branch: string;
  dirty_files: string[];
  staged_diff_stat: string;
  unstaged_diff_stat: string;
  repo_map_snippet: string;
  recent_edits: string[];
}

export interface CodingContextConfig {
  status: string;
  enabled: boolean;
  provider: string;
}

export class CodingContextProviderClient {
  private baseUrl: string;

  constructor(baseUrl: string = "http://127.0.0.1:8000") {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  async getConfig(): Promise<CodingContextConfig> {
    const res = await fetch(`${this.baseUrl}/context/coding/config`);
    if (!res.ok) {
      throw new Error(`getConfig failed with status ${res.status}`);
    }
    return (await res.json()) as CodingContextConfig;
  }

  async getCodingContext(tokenBudget: number = 500): Promise<WorkspaceCodingState> {
    const res = await fetch(`${this.baseUrl}/context/coding/state`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token_budget: tokenBudget }),
    });
    if (!res.ok) {
      throw new Error(`getCodingContext failed with status ${res.status}`);
    }
    const data = (await res.json()) as { status: string; state: WorkspaceCodingState };
    return data.state;
  }

  async formatLayer(state: WorkspaceCodingState): Promise<string> {
    const res = await fetch(`${this.baseUrl}/context/coding/format`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ state }),
    });
    if (!res.ok) {
      throw new Error(`formatLayer failed with status ${res.status}`);
    }
    const data = (await res.json()) as { status: string; formatted_layer: string };
    return data.formatted_layer;
  }
}
