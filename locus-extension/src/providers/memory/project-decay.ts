/**
 * Project-Specific Memory Decay Engine (§4.14)
 *
 * Status-based exponential memory retention and cold-storage transitions.
 */

export const HALF_LIFE_DAYS: Record<string, number> = {
  ACTIVE: 90.0,
  PAUSED: 30.0,
  BACKLOG: 14.0,
  ARCHIVED: 7.0,
};

export const DEFAULT_HALF_LIFE = 30.0;
export const COLD_STORAGE_THRESHOLD = 0.10;

export function calculateRetentionStrength(projectState: string, daysSinceLastTouch: number): number {
  if (daysSinceLastTouch <= 0) return 1.0;
  const halfLife = HALF_LIFE_DAYS[projectState.toUpperCase()] ?? DEFAULT_HALF_LIFE;
  const strength = 1.0 * Math.pow(2.0, -daysSinceLastTouch / halfLife);
  return Math.round(Math.max(0.0, Math.min(1.0, strength)) * 10000) / 10000;
}

export interface ProjectMemoryCluster {
  project_id: string;
  status: string;
  last_touched_at: string;
  nodes: Record<string, unknown>[];
  retention_strength: number;
  is_cold_archived: boolean;
}

export class ProjectDecayManager {
  private clusters: Map<string, ProjectMemoryCluster> = new Map();
  private coldArchive: Map<string, Record<string, unknown>> = new Map();

  public registerProject(
    projectId: string,
    status: string = "ACTIVE",
    nodes: Record<string, unknown>[] = []
  ): ProjectMemoryCluster {
    const cluster: ProjectMemoryCluster = {
      project_id: projectId,
      status: status.toUpperCase(),
      last_touched_at: new Date().toISOString(),
      nodes,
      retention_strength: 1.0,
      is_cold_archived: false,
    };
    this.clusters.set(projectId, cluster);
    return cluster;
  }

  public touchProject(projectId: string): ProjectMemoryCluster | null {
    const cluster = this.clusters.get(projectId);
    if (!cluster) return null;
    cluster.last_touched_at = new Date().toISOString();
    cluster.retention_strength = 1.0;
    if (cluster.is_cold_archived) {
      cluster.is_cold_archived = false;
      this.coldArchive.delete(projectId);
    }
    return cluster;
  }

  public sweepProjectMemories(currentTime?: Date): { total_swept: number; newly_archived: number } {
    const now = currentTime || new Date();
    let swept = 0;
    let newlyArchived = 0;

    for (const cluster of this.clusters.values()) {
      const lt = new Date(cluster.last_touched_at).getTime();
      const daysInactive = Math.max(0, (now.getTime() - lt) / (1000 * 86400));
      const strength = calculateRetentionStrength(cluster.status, daysInactive);
      cluster.retention_strength = strength;
      swept++;

      if (strength < COLD_STORAGE_THRESHOLD && !cluster.is_cold_archived) {
        cluster.is_cold_archived = true;
        this.coldArchive.set(cluster.project_id, {
          project_id: cluster.project_id,
          archived_at: now.toISOString(),
          cluster,
        });
        newlyArchived++;
      }
    }

    return { total_swept: swept, newly_archived: newlyArchived };
  }
}
