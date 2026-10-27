/**
 * SPEC §25.14: TypeScript client for Goal Stack Enforcement (F-0115 / US-92).
 */

export interface GoalNodeData {
  id: string;
  title: string;
  level: string;
  parent_id?: string | null;
  faction?: string | null;
  status?: string;
  metadata?: Record<string, unknown>;
}

export interface EnforcementResultData {
  allowed: boolean;
  enforced: boolean;
  valid: boolean;
  reasons: string[];
  details: Record<string, unknown>;
}

export interface BriefingOrphanReportData {
  orphan_count: number;
  orphans: Array<{
    node_id: string;
    title: string;
    level: string;
    issue: string;
  }>;
  briefing_text: string;
}

export interface GoalEnforcementStatusData {
  provider: string;
  master_enabled: boolean;
  master_switch: string;
  subsystem_enabled: boolean;
  subsystem_switch: string;
  total_registered_nodes: number;
}

export interface GoalEnforcementClientOptions {
  sidecarUrl?: string;
}

export class GoalStackEnforcementClient {
  private readonly baseUrl: string;

  constructor(options: GoalEnforcementClientOptions = {}) {
    this.baseUrl = options.sidecarUrl || "http://127.0.0.1:8420";
  }

  async enforceTask(
    taskId: string,
    stackNodes?: GoalNodeData[]
  ): Promise<EnforcementResultData> {
    const res = await fetch(`${this.baseUrl}/goal-enforcement/enforce-task`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        task_id: taskId,
        stack_nodes: stackNodes,
      }),
    });
    if (!res.ok) {
      throw new Error(`Failed to enforce task goal stack: ${res.status}`);
    }
    return res.json();
  }

  async enforceProject(
    projectId: string,
    stackNodes?: GoalNodeData[]
  ): Promise<EnforcementResultData> {
    const res = await fetch(`${this.baseUrl}/goal-enforcement/enforce-project`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        project_id: projectId,
        stack_nodes: stackNodes,
      }),
    });
    if (!res.ok) {
      throw new Error(`Failed to enforce project goal stack: ${res.status}`);
    }
    return res.json();
  }

  async getBriefingOrphans(
    stackNodes?: GoalNodeData[]
  ): Promise<BriefingOrphanReportData> {
    const res = await fetch(`${this.baseUrl}/goal-enforcement/briefing-orphans`, {
      method: stackNodes ? "POST" : "GET",
      headers: { "Content-Type": "application/json" },
      body: stackNodes ? JSON.stringify({ stack_nodes: stackNodes }) : undefined,
    });
    if (!res.ok) {
      throw new Error(`Failed to get briefing orphans: ${res.status}`);
    }
    return res.json();
  }

  async auditStack(
    stackNodes?: GoalNodeData[]
  ): Promise<EnforcementResultData> {
    const res = await fetch(`${this.baseUrl}/goal-enforcement/audit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        stack_nodes: stackNodes,
      }),
    });
    if (!res.ok) {
      throw new Error(`Failed to audit goal stack: ${res.status}`);
    }
    return res.json();
  }

  async getStatus(): Promise<GoalEnforcementStatusData> {
    const res = await fetch(`${this.baseUrl}/goal-enforcement/status`, {
      method: "GET",
    });
    if (!res.ok) {
      throw new Error(`Failed to fetch goal enforcement status: ${res.status}`);
    }
    return res.json();
  }
}
