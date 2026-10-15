/**
 * Locus Subconscious Background Processing Engine (§29.7) TypeScript companion.
 */

export enum SubconsciousTaskState {
  PENDING = 'pending',
  RUNNING = 'running',
  COMPLETED = 'completed',
  FAILED = 'failed',
}

export interface SubconsciousTask {
  taskId: string;
  name: string;
  priority: number;
  intervalSeconds: number;
  lastRunTimestamp: number;
  state: SubconsciousTaskState;
  executionCount: number;
  action?: () => any;
  lastError?: string;
}

export class SubconsciousEngine {
  private idleThresholdMs: number;
  private lastUserActivity: number = Date.now();
  private tasks: Map<string, SubconsciousTask> = new Map();

  constructor(idleThresholdSeconds: number = 5.0) {
    this.idleThresholdMs = idleThresholdSeconds * 1000;
  }

  recordActivity(): void {
    this.lastUserActivity = Date.now();
  }

  isIdle(): boolean {
    return (Date.now() - this.lastUserActivity) >= this.idleThresholdMs;
  }

  registerTask(
    taskId: string,
    name: string,
    intervalSeconds: number,
    action: () => any,
    priority: number = 5
  ): SubconsciousTask {
    const task: SubconsciousTask = {
      taskId,
      name,
      priority,
      intervalSeconds,
      lastRunTimestamp: 0,
      state: SubconsciousTaskState.PENDING,
      executionCount: 0,
      action,
    };
    this.tasks.set(taskId, task);
    return task;
  }

  step(): string[] {
    if (!this.isIdle()) return [];

    const now = Date.now();
    const executed: string[] = [];
    const taskList = Array.from(this.tasks.values()).sort((a, b) => b.priority - a.priority);

    for (const task of taskList) {
      if ((now - task.lastRunTimestamp) >= (task.intervalSeconds * 1000)) {
        task.state = SubconsciousTaskState.RUNNING;
        try {
          if (task.action) task.action();
          task.state = SubconsciousTaskState.COMPLETED;
          task.executionCount++;
        } catch (err: any) {
          task.state = SubconsciousTaskState.FAILED;
          task.lastError = err?.message || String(err);
        } finally {
          task.lastRunTimestamp = now;
          executed.push(task.taskId);
        }
      }
    }

    return executed;
  }
}
