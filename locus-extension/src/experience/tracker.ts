/**
 * Locus Agent Experience Tracking (Procedural Memory) (§10.9) TypeScript companion.
 */

export interface ProceduralTrajectory {
  trajectoryId: string;
  taskGoal: string;
  actionSequence: string[];
  success: boolean;
  confidenceScore: number;
  durationSeconds: number;
  errorRecoveryCount?: number;
  tags?: string[];
}

export class AgentExperienceTracker {
  private trajectories: ProceduralTrajectory[] = [];

  recordTrajectory(
    taskGoal: string,
    actionSequence: string[],
    success: boolean = true,
    durationSeconds: number = 1.0
  ): ProceduralTrajectory {
    const traj: ProceduralTrajectory = {
      trajectoryId: `traj_${Math.random().toString(36).substring(2, 9)}`,
      taskGoal,
      actionSequence,
      success,
      confidenceScore: success ? 0.95 : 0.2,
      durationSeconds,
    };
    this.trajectories.push(traj);
    return traj;
  }

  findSimilarTrajectories(taskGoal: string): ProceduralTrajectory[] {
    const qWords = new Set(taskGoal.toLowerCase().split(/\s+/));
    return this.trajectories.filter((t) => {
      const words = new Set(t.taskGoal.toLowerCase().split(/\s+/));
      for (const w of qWords) {
        if (words.has(w)) return true;
      }
      return false;
    });
  }
}
