/**
 * SPEC §25.9: TypeScript client for Emergency Task Injection.
 */

export interface EmergencyTaskInput {
  id: string;
  title: string;
  faction: string;
  difficulty?: number;
  tws?: number;
  is_emergency?: boolean;
  estimated_minutes?: number;
  metadata?: Record<string, unknown>;
}

export interface EmergencyInjectionOptions {
  sidecarUrl?: string;
}

export class EmergencyTaskClient {
  private readonly baseUrl: string;

  constructor(options: EmergencyInjectionOptions = {}) {
    this.baseUrl = options.sidecarUrl || "http://127.0.0.1:8420";
  }

  async prioritizeTasks(
    tasks: EmergencyTaskInput[],
    bypassTws?: boolean
  ): Promise<{
    status: string;
    bypass_tws: boolean;
    total_tasks: number;
    emergency_tasks_count: number;
    tasks: EmergencyTaskInput[];
  }> {
    const res = await fetch(`${this.baseUrl}/emergency/prioritize`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tasks, bypass_tws: bypassTws }),
    });
    if (!res.ok) {
      throw new Error(`Failed to prioritize tasks: ${res.status}`);
    }
    return res.json();
  }

  async injectTask(
    timeline: unknown[],
    task: EmergencyTaskInput,
    atIndex: number = 0
  ): Promise<{
    status: string;
    injected_task_id: string;
    timeline_length: number;
    timeline: unknown[];
  }> {
    const res = await fetch(`${this.baseUrl}/emergency/inject`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ timeline, task, at_index: atIndex }),
    });
    if (!res.ok) {
      throw new Error(`Failed to inject emergency task: ${res.status}`);
    }
    return res.json();
  }

  async getStatus(): Promise<{
    status: string;
    provider: string;
    crisis_hierarchy: string[];
  }> {
    const res = await fetch(`${this.baseUrl}/emergency/status`);
    if (!res.ok) {
      throw new Error(`Failed to get emergency status: ${res.status}`);
    }
    return res.json();
  }
}
