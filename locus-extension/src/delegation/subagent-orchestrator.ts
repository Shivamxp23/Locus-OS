/**
 * Locus Subagent Orchestrator (§3.7, §11.1-11.5) TypeScript companion.
 */

export enum SubagentArchetype {
  RESEARCHER = 'researcher',
  CODER = 'coder',
  CRITIC = 'critic',
  PLANNER = 'planner',
}

export enum SubagentState {
  IDLE = 'idle',
  RUNNING = 'running',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled',
}

export interface SubagentTask {
  taskId: string;
  archetype: SubagentArchetype;
  prompt: string;
  depth: number;
  maxDepth: number;
  state: SubagentState;
  result?: string;
}

export class SubagentOrchestrator {
  private activeTasks: Map<string, SubagentTask> = new Map();

  constructor(public globalMaxDepth: number = 3, public maxConcurrent: number = 5) {}

  spawnSubagent(archetype: SubagentArchetype, prompt: string, parentDepth: number = 0): SubagentTask {
    const newDepth = parentDepth + 1;
    if (newDepth > this.globalMaxDepth) {
      throw new Error(`Recursion depth limit exceeded: ${newDepth} > ${this.globalMaxDepth}`);
    }
    if (this.activeTasks.size >= this.maxConcurrent) {
      throw new Error('Maximum concurrent subagent quota reached');
    }

    const taskId = `sub_${archetype}_${Math.random().toString(36).substring(2, 9)}`;
    const task: SubagentTask = {
      taskId,
      archetype,
      prompt,
      depth: newDepth,
      maxDepth: this.globalMaxDepth,
      state: SubagentState.IDLE,
    };
    this.activeTasks.set(taskId, task);
    return task;
  }

  async executeSubagent(
    task: SubagentTask,
    executor?: (t: SubagentTask) => Promise<string>
  ): Promise<string> {
    task.state = SubagentState.RUNNING;
    try {
      const output = executor
        ? await executor(task)
        : `[${task.archetype.toUpperCase()}] completed task: ${task.prompt.slice(0, 40)}`;
      task.result = output;
      task.state = SubagentState.COMPLETED;
      return output;
    } catch (err: any) {
      task.state = SubagentState.FAILED;
      throw err;
    } finally {
      this.activeTasks.delete(task.taskId);
    }
  }
}
