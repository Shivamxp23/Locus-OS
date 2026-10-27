/**
 * SPEC §23.1-23.5 lines 8440-8490: CI/CD, Docker Deployment & Batch Runner.
 * Client library for inspecting container topology, systemd units, and batch evaluation.
 */

export interface DockerTopologyResult {
  status: string;
  valid: boolean;
  service_count: number;
  security_violations: string[];
  errors: string[];
  services: Record<string, { image: string; ports: string[]; restart: string }>;
}

export interface SystemdGenerateResult {
  status: string;
  service_type: string;
  unit_content: string;
}

export interface RunResult {
  run_index: number;
  duration_sec: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  tool_calls: string[];
  output_text: string;
  status: string;
}

export interface BatchReport {
  prompt: string;
  n_runs: number;
  successful_runs: number;
  mean_duration_sec: number;
  mean_tokens: number;
  total_tokens_consumed: number;
  unique_tool_calls: string[];
  consistency_score: number;
  runs: RunResult[];
}

export class DeploymentClient {
  constructor(private readonly baseUrl: string = "http://127.0.0.1:8420") {}

  async inspectDockerTopology(): Promise<DockerTopologyResult> {
    const res = await fetch(`${this.baseUrl}/deployment/docker/status`);
    if (res.status === 503) {
      throw new Error("Deployment service is disabled (HTTP 503)");
    }
    return res.json();
  }

  async generateSystemdUnit(
    service_type = "sidecar",
    working_dir = "/opt/locus/locus-os",
    user = "locus",
    env_file = "/opt/locus/.locus/.env"
  ): Promise<SystemdGenerateResult> {
    const res = await fetch(`${this.baseUrl}/deployment/systemd/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ service_type, working_dir, user, env_file }),
    });
    if (res.status === 503) {
      throw new Error("Deployment service is disabled (HTTP 503)");
    }
    return res.json();
  }

  async evaluateBatch(prompt: string, n_runs = 3): Promise<{ status: string; report: BatchReport }> {
    const res = await fetch(`${this.baseUrl}/deployment/batch/evaluate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt, n_runs }),
    });
    if (res.status === 503) {
      throw new Error("Deployment service is disabled (HTTP 503)");
    }
    return res.json();
  }

  async getStatus(): Promise<{ compose_file: string; compose_exists: boolean; runner_ready: boolean }> {
    const res = await fetch(`${this.baseUrl}/deployment/status`);
    if (res.status === 503) {
      throw new Error("Deployment service is disabled (HTTP 503)");
    }
    return res.json();
  }
}
