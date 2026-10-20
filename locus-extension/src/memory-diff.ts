/**
 * locus-extension/src/memory-diff.ts
 *
 * TypeScript client for Memory Diff (Snapshot-Based Change Tracking).
 * Implements Spec §4.9:
 * - Snapshot-based change tracking for memory sources.
 * - Captures chunk store state after sync, diffs against previous snapshots (added, removed, modified).
 * - Named checkpoints and cross-source diffing.
 * - Agent tool what_changed action.
 */

export type SnapshotTrigger = "auto_post_sync" | "manual" | "checkpoint";

export type ChangeKind = "added" | "removed" | "modified" | "unchanged";

export interface SnapshotItem {
  chunk_id: string;
  content_hash: string;
  title?: string | null;
  token_count: number;
}

export interface Snapshot {
  id: string;
  source_scope: string;
  trigger: SnapshotTrigger;
  items: SnapshotItem[];
  created_at: string;
}

export interface ItemChange {
  kind: ChangeKind;
  chunk_id: string;
  title?: string | null;
  old_hash?: string | null;
  new_hash?: string | null;
}

export interface DiffSummary {
  added: number;
  removed: number;
  modified: number;
  unchanged: number;
}

export interface DiffResult {
  source_scope: string;
  from_snapshot: string;
  to_snapshot: string;
  changes: ItemChange[];
  summary: DiffSummary;
}

export interface Checkpoint {
  name: string;
  snapshot_ids: Record<string, string>;
  created_at: string;
}

export interface CrossSourceDiff {
  checkpoint_name: string;
  diffs: Record<string, DiffResult>;
  total_summary: DiffSummary;
}

export interface MemoryDiffConfig {
  enabled: boolean;
  db_path?: string;
  auto_snapshot_post_sync: boolean;
}

export class MemoryDiffClient {
  private readonly baseUrl: string;

  constructor(baseUrl: string = "http://127.0.0.1:8000") {
    this.baseUrl = baseUrl.replace(/\/+$/, "");
  }

  /**
   * Retrieve Memory Diff subsystem configuration.
   */
  public async getConfig(): Promise<Record<string, any>> {
    const res = await fetch(`${this.baseUrl}/memory/diff/config`);
    if (!res.ok) {
      throw new Error(`Failed to get diff config: ${res.statusText} (${res.status})`);
    }
    return res.json();
  }

  /**
   * List snapshots for a source scope.
   */
  public async listSnapshots(sourceScope?: string, limit: number = 50): Promise<Snapshot[]> {
    const params = new URLSearchParams();
    if (sourceScope) params.set("source_scope", sourceScope);
    params.set("limit", String(limit));
    const res = await fetch(`${this.baseUrl}/memory/diff/snapshots?${params.toString()}`);
    if (!res.ok) {
      throw new Error(`Failed to list snapshots: ${res.statusText} (${res.status})`);
    }
    const data = await res.json();
    return (data.snapshots as Snapshot[]) || [];
  }

  /**
   * Get single snapshot by ID.
   */
  public async getSnapshot(snapshotId: string): Promise<Snapshot | null> {
    const res = await fetch(`${this.baseUrl}/memory/diff/snapshots/${snapshotId}`);
    if (res.status === 404) return null;
    if (!res.ok) {
      throw new Error(`Failed to get snapshot ${snapshotId}: ${res.statusText} (${res.status})`);
    }
    const data = await res.json();
    return data.snapshot as Snapshot;
  }

  /**
   * Take a new snapshot of memory chunk items.
   */
  public async takeSnapshot(
    sourceScope: string,
    trigger: SnapshotTrigger = "manual",
    items?: Array<Record<string, any>>
  ): Promise<Snapshot> {
    const res = await fetch(`${this.baseUrl}/memory/diff/snapshot`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        source_scope: sourceScope,
        trigger,
        items,
      }),
    });
    if (!res.ok) {
      throw new Error(`Failed to take snapshot: ${res.statusText} (${res.status})`);
    }
    const data = await res.json();
    return data.snapshot as Snapshot;
  }

  /**
   * Compare two snapshots to calculate item additions, removals, and modifications.
   */
  public async compareSnapshots(
    sourceScope: string,
    fromSnapshotId: string,
    toSnapshotId: string
  ): Promise<DiffResult> {
    const res = await fetch(`${this.baseUrl}/memory/diff/compare`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        source_scope: sourceScope,
        from_snapshot_id: fromSnapshotId,
        to_snapshot_id: toSnapshotId,
      }),
    });
    if (!res.ok) {
      throw new Error(`Failed to compare snapshots: ${res.statusText} (${res.status})`);
    }
    const data = await res.json();
    return data.diff as DiffResult;
  }

  /**
   * Create a named baseline checkpoint across active source scopes.
   */
  public async createCheckpoint(
    name: string,
    scopes?: string[],
    scopeItems?: Record<string, any[]>
  ): Promise<Checkpoint> {
    const res = await fetch(`${this.baseUrl}/memory/diff/checkpoint`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name,
        scopes,
        scope_items: scopeItems,
      }),
    });
    if (!res.ok) {
      throw new Error(`Failed to create checkpoint: ${res.statusText} (${res.status})`);
    }
    const data = await res.json();
    return data.checkpoint as Checkpoint;
  }

  /**
   * Compute cross-source diff since a named checkpoint.
   */
  public async diffSinceCheckpoint(
    name: string,
    currentScopeItems?: Record<string, any[]>
  ): Promise<CrossSourceDiff> {
    const res = await fetch(`${this.baseUrl}/memory/diff/checkpoint/diff`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name,
        current_scope_items: currentScopeItems,
      }),
    });
    if (!res.ok) {
      throw new Error(`Failed to diff since checkpoint: ${res.statusText} (${res.status})`);
    }
    const data = await res.json();
    return data.cross_diff as CrossSourceDiff;
  }

  /**
   * Get human-readable summary of memory changes for agent tools.
   */
  public async whatChanged(checkpointName?: string, sourceScope?: string): Promise<string> {
    const params = new URLSearchParams();
    if (checkpointName) params.set("checkpoint_name", checkpointName);
    if (sourceScope) params.set("source_scope", sourceScope);
    const res = await fetch(`${this.baseUrl}/memory/diff/what_changed?${params.toString()}`);
    if (!res.ok) {
      throw new Error(`Failed to get what_changed: ${res.statusText} (${res.status})`);
    }
    const data = await res.json();
    return data.summary as string;
  }
}
