/**
 * locus-extension/src/gateway/lifecycle.ts - Gateway Lifecycle TypeScript client.
 *
 * Implements Spec §17.10
 */

export interface SnapshotPayload {
  timestampIso: string;
  activeSessionIds: string[];
  pendingQueueCount: number;
}

export class GatewayLifecycleClient {
  public static isValidSnapshot(snapshot: SnapshotPayload): boolean {
    return Array.isArray(snapshot.activeSessionIds) && typeof snapshot.pendingQueueCount === "number";
  }
}
