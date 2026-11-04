/**
 * Code Graph Analysis Client (SPEC §29.6 / F-0069 / US-107).
 *
 * Communicates with Sidecar `/codegraph/*` endpoints for codebase dependency
 * analysis, PageRank importance, and harness task scoping.
 */

export interface DependencyEdge {
  source: string;
  target: string;
  type: string;
  raw?: string;
}

export interface CodeGraph {
  files: string[];
  edges: DependencyEdge[];
  clusters: string[][];
  importance: Record<string, number>;
  entry_points: string[];
  source: string;
  status?: string;
  provider?: string;
  error?: string;
  status_code?: number;
}

export interface TaskScopeResult {
  task_description: string;
  seed_files: string[];
  expanded_files: string[];
  depth: number;
  total_scoped: number;
  status?: string;
  provider?: string;
  error?: string;
  status_code?: number;
}

export interface CodeGraphStatus {
  status: string;
  provider: string;
  prefix: string;
  enabled: boolean;
  supported_extensions: string[];
  excluded_directories: string[];
  error?: string;
  status_code?: number;
}

export class CodeGraphClient {
  private baseUrl: string;

  constructor(baseUrl: string = "http://127.0.0.1:8420") {
    this.baseUrl = baseUrl.replace(/\/+$/, "");
  }

  async analyzeCodebase(projectPath: string = "."): Promise<CodeGraph> {
    try {
      const response = await fetch(`${this.baseUrl}/codegraph/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_path: projectPath }),
      });
      if (response.status === 503) {
        return {
          files: [],
          edges: [],
          clusters: [],
          importance: {},
          entry_points: [],
          source: "disabled",
          error: "Code Graph feature is disabled",
          status_code: 503,
        };
      }
      return (await response.json()) as CodeGraph;
    } catch (err: any) {
      return {
        files: [],
        edges: [],
        clusters: [],
        importance: {},
        entry_points: [],
        source: "error",
        error: String(err?.message || err),
        status_code: 500,
      };
    }
  }

  async scopeTask(
    taskDescription: string,
    projectPath: string = ".",
    depth: number = 2
  ): Promise<TaskScopeResult> {
    try {
      const response = await fetch(`${this.baseUrl}/codegraph/scope`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          task_description: taskDescription,
          project_path: projectPath,
          depth,
        }),
      });
      if (response.status === 503) {
        return {
          task_description: taskDescription,
          seed_files: [],
          expanded_files: [],
          depth,
          total_scoped: 0,
          error: "Code Graph feature is disabled",
          status_code: 503,
        };
      }
      return (await response.json()) as TaskScopeResult;
    } catch (err: any) {
      return {
        task_description: taskDescription,
        seed_files: [],
        expanded_files: [],
        depth,
        total_scoped: 0,
        error: String(err?.message || err),
        status_code: 500,
      };
    }
  }

  async getGraph(
    projectPath: string = ".",
    maxAgeHours: number = 24.0
  ): Promise<CodeGraph> {
    try {
      const response = await fetch(`${this.baseUrl}/codegraph/graph`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_path: projectPath,
          max_age_hours: maxAgeHours,
        }),
      });
      if (response.status === 503) {
        return {
          files: [],
          edges: [],
          clusters: [],
          importance: {},
          entry_points: [],
          source: "disabled",
          error: "Code Graph feature is disabled",
          status_code: 503,
        };
      }
      return (await response.json()) as CodeGraph;
    } catch (err: any) {
      return {
        files: [],
        edges: [],
        clusters: [],
        importance: {},
        entry_points: [],
        source: "error",
        error: String(err?.message || err),
        status_code: 500,
      };
    }
  }

  async getStatus(): Promise<CodeGraphStatus> {
    try {
      const response = await fetch(`${this.baseUrl}/codegraph/status`, {
        method: "GET",
      });
      if (response.status === 503) {
        return {
          status: "disabled",
          provider: "unknown",
          prefix: "locus.code_graph",
          enabled: false,
          supported_extensions: [],
          excluded_directories: [],
          error: "Code Graph feature is disabled",
          status_code: 503,
        };
      }
      return (await response.json()) as CodeGraphStatus;
    } catch (err: any) {
      return {
        status: "error",
        provider: "unknown",
        prefix: "locus.code_graph",
        enabled: false,
        supported_extensions: [],
        excluded_directories: [],
        error: String(err?.message || err),
        status_code: 500,
      };
    }
  }
}
