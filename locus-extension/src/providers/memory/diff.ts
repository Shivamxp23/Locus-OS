/**
 * Memory Diff (Snapshot-Based Change Tracking) (§4.9)
 *
 * Tracks chunk-level diffs across sync events and checkpoint windows.
 */

export type SnapshotTrigger = "AutoPostSync" | "Manual" | "Checkpoint";
export type ChangeKind = "Added" | "Removed" | "Modified";

export interface SnapshotItem {
  chunk_id: string;
  content_hash: string;
  title?: string;
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
  title?: string;
  old_hash?: string;
  new_hash?: string;
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

export class MemoryDiffManager {
  private snapshotsByScope: Map<string, Snapshot[]> = new Map();
  private checkpointsByScope: Map<string, Snapshot> = new Map();

  public recordSnapshot(
    sourceScope: string,
    items: SnapshotItem[],
    trigger: SnapshotTrigger = "AutoPostSync"
  ): Snapshot {
    const snap: Snapshot = {
      id: "snap-" + Math.random().toString(36).substring(2, 10),
      source_scope: sourceScope,
      trigger,
      items,
      created_at: new Date().toISOString(),
    };
    const list = this.snapshotsByScope.get(sourceScope) || [];
    list.push(snap);
    this.snapshotsByScope.set(sourceScope, list);
    return snap;
  }

  public createCheckpoint(sourceScope: string, items?: SnapshotItem[]): Snapshot {
    let snap: Snapshot;
    if (items) {
      snap = this.recordSnapshot(sourceScope, items, "Checkpoint");
    } else {
      const list = this.snapshotsByScope.get(sourceScope) || [];
      snap = list.length > 0 ? list[list.length - 1] : this.recordSnapshot(sourceScope, [], "Checkpoint");
    }
    this.checkpointsByScope.set(sourceScope, snap);
    return snap;
  }

  public diff(
    sourceScope: string,
    fromSnap: Snapshot | undefined,
    toSnap: Snapshot
  ): DiffResult {
    const fromMap = new Map<string, SnapshotItem>();
    if (fromSnap) {
      for (const item of fromSnap.items) {
        fromMap.set(item.chunk_id, item);
      }
    }
    const toMap = new Map<string, SnapshotItem>();
    for (const item of toSnap.items) {
      toMap.set(item.chunk_id, item);
    }

    const allKeys = new Set<string>([...fromMap.keys(), ...toMap.keys()]);
    const changes: ItemChange[] = [];
    const summary: DiffSummary = { added: 0, removed: 0, modified: 0, unchanged: 0 };

    for (const cid of Array.from(allKeys).sort()) {
      const inFrom = fromMap.get(cid);
      const inTo = toMap.get(cid);

      if (inTo && !inFrom) {
        changes.push({
          kind: "Added",
          chunk_id: cid,
          title: inTo.title,
          new_hash: inTo.content_hash,
        });
        summary.added++;
      } else if (inFrom && !inTo) {
        changes.push({
          kind: "Removed",
          chunk_id: cid,
          title: inFrom.title,
          old_hash: inFrom.content_hash,
        });
        summary.removed++;
      } else if (inFrom && inTo) {
        if (inFrom.content_hash !== inTo.content_hash) {
          changes.push({
            kind: "Modified",
            chunk_id: cid,
            title: inTo.title || inFrom.title,
            old_hash: inFrom.content_hash,
            new_hash: inTo.content_hash,
          });
          summary.modified++;
        } else {
          summary.unchanged++;
        }
      }
    }

    return {
      source_scope: sourceScope,
      from_snapshot: fromSnap ? fromSnap.id : "empty",
      to_snapshot: toSnap.id,
      changes,
      summary,
    };
  }

  public diffSinceCheckpoint(sourceScope: string, currentItems?: SnapshotItem[]): DiffResult {
    const ckpt = this.checkpointsByScope.get(sourceScope);
    const toSnap: Snapshot = currentItems
      ? {
          id: "snap-eval",
          source_scope: sourceScope,
          trigger: "Manual",
          items: currentItems,
          created_at: new Date().toISOString(),
        }
      : (this.snapshotsByScope.get(sourceScope) || []).slice(-1)[0] || {
          id: "snap-empty",
          source_scope: sourceScope,
          trigger: "Manual",
          items: [],
          created_at: new Date().toISOString(),
        };
    return this.diff(sourceScope, ckpt, toSnap);
  }
}
