/**
 * locus-extension/src/life-os/goal-stack.ts - Three-Layer Goal Stack (TS definition).
 *
 * Implements Spec §25.5 & §25.14
 */

export enum Faction {
  HEALTH = "Health",
  LEVERAGE = "Leverage",
  CRAFT = "Craft",
  EXPRESSION = "Expression",
}

export interface Outcome {
  id: string;
  title: string;
  faction: Faction;
  status: "active" | "paused" | "completed" | "archived";
  description?: string;
}

export interface Project {
  id: string;
  outcomeId: string;
  title: string;
  status: "active" | "paused" | "completed" | "archived";
  description?: string;
}

export interface GoalTask {
  id: string;
  projectId: string;
  title: string;
  difficulty: number;
  urgency: number;
  leverage: number;
  consequence: number;
  deferralCount?: number;
  status?: "active" | "paused" | "completed" | "archived";
}

export class GoalStackValidator {
  constructor(
    private outcomes: Map<string, Outcome> = new Map(),
    private projects: Map<string, Project> = new Map(),
  ) {}

  public registerOutcome(outcome: Outcome): void {
    this.outcomes.set(outcome.id, outcome);
  }

  public registerProject(project: Project): void {
    this.projects.set(project.id, project);
  }

  public validateTask(task: GoalTask): { valid: boolean; error?: string } {
    if (!task.projectId) {
      return { valid: false, error: `Task ${task.title} is an orphan (no projectId)` };
    }
    const project = this.projects.get(task.projectId);
    if (!project) {
      return { valid: false, error: `Project ${task.projectId} not found` };
    }
    if (!project.outcomeId) {
      return { valid: false, error: `Project ${project.title} has no parent outcome` };
    }
    const outcome = this.outcomes.get(project.outcomeId);
    if (!outcome) {
      return { valid: false, error: `Outcome ${project.outcomeId} not found` };
    }
    return { valid: true };
  }
}
