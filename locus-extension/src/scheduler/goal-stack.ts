/**
 * SPEC §25.5-25.8 & §25.12: TypeScript client for Operating Modes & Scheduler.
 */

export interface GoalNode {
  id: string;
  title: string;
  level: "vision" | "milestone" | "daily";
  parent_id?: string;
  faction?: string;
  status?: string;
  metadata?: Record<string, unknown>;
}

export interface FactionActionGap {
  faction: string;
  declared_priority: number;
  actual_hours: number;
  target_hours: number;
  action_gap: number;
  alert: boolean;
  message: string;
}

export interface ScheduledBlock {
  block_type: string;
  duration_minutes: number;
  task_id?: string;
  task_title?: string;
  faction?: string;
  tws: number;
}

export interface SchedulerOptions {
  sidecarUrl?: string;
}

export class SchedulerClient {
  private readonly baseUrl: string;

  constructor(options: SchedulerOptions = {}) {
    this.baseUrl = options.sidecarUrl || "http://127.0.0.1:8420";
  }

  async validateGoalStack(): Promise<{
    valid: boolean;
    total_nodes: number;
    orphan_count: number;
    orphans: unknown[];
  }> {
    const res = await fetch(`${this.baseUrl}/scheduler/goal-stack/validate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
    if (!res.ok) {
      throw new Error(`Failed to validate goal stack: ${res.status}`);
    }
    return res.json();
  }

  async getOrphans(): Promise<{
    status: string;
    orphan_count: number;
    orphans: unknown[];
  }> {
    const res = await fetch(`${this.baseUrl}/scheduler/goal-stack/orphans`);
    if (!res.ok) {
      throw new Error(`Failed to retrieve orphan tasks: ${res.status}`);
    }
    return res.json();
  }

  async evaluateActionGaps(
    factions: Record<string, { declared_priority: number; actual_hours: number; target_hours: number }>
  ): Promise<{
    status: string;
    reports: FactionActionGap[];
    alerts_count: number;
  }> {
    const res = await fetch(`${this.baseUrl}/scheduler/action-gap/evaluate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ factions }),
    });
    if (!res.ok) {
      throw new Error(`Failed to evaluate action gaps: ${res.status}`);
    }
    return res.json();
  }

  async recordDeferral(
    taskId: string,
    reason: string = ""
  ): Promise<{
    status: string;
    record: {
      task_id: string;
      deferral_count: number;
      action: string;
      is_parked: boolean;
      message: string;
    };
  }> {
    const res = await fetch(`${this.baseUrl}/scheduler/deferral/record`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task_id: taskId, reason }),
    });
    if (!res.ok) {
      throw new Error(`Failed to record deferral: ${res.status}`);
    }
    return res.json();
  }

  async computeLagBonus(lagHours: number): Promise<{
    status: string;
    lag_hours: number;
    tws_lag_bonus: number;
    is_crisis: boolean;
    is_ahead: boolean;
  }> {
    const res = await fetch(`${this.baseUrl}/scheduler/lag/bonus`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lag_hours: lagHours }),
    });
    if (!res.ok) {
      throw new Error(`Failed to compute lag bonus: ${res.status}`);
    }
    return res.json();
  }

  async generateSchedule(
    dcs: number,
    tasks: unknown[],
    enforceGoalStack: boolean = true
  ): Promise<{
    status: string;
    mode: string;
    timeline: ScheduledBlock[];
    total_work_minutes: number;
    total_buffer_minutes: number;
  }> {
    const res = await fetch(`${this.baseUrl}/scheduler/schedule/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        dcs,
        tasks,
        enforce_goal_stack: enforceGoalStack,
      }),
    });
    if (!res.ok) {
      throw new Error(`Failed to generate schedule: ${res.status}`);
    }
    return res.json();
  }

  async getStatus(): Promise<{
    status: string;
    provider: string;
    goal_stack_nodes_count: number;
    parked_tasks_count: number;
  }> {
    const res = await fetch(`${this.baseUrl}/scheduler/status`);
    if (!res.ok) {
      throw new Error(`Failed to get scheduler status: ${res.status}`);
    }
    return res.json();
  }
}
