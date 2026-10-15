/**
 * locus-extension/src/providers/memory/queue.ts - Memory Queue Client
 *
 * Implements Spec §4.8 (Async Memory Job Pipeline).
 */

export type JobKind = "ExtractChunk" | "AppendBuffer" | "Seal" | "TopicRoute" | "DigestDaily" | "FlushStale";
export type JobStatus = "Ready" | "Running" | "Done" | "Failed";

export interface MemoryJob {
  id: string;
  kind: JobKind;
  payload: Record<string, unknown>;
  dedupe_key: string;
  status: JobStatus;
  claim_token?: string;
  created_at: number;
}

export interface MemoryQueueProvider {
  enqueue(kind: JobKind, payload: Record<string, unknown>, dedupeKey: string): Promise<MemoryJob | null>;
  claimNext(): Promise<MemoryJob | null>;
  markDone(jobId: string, claimToken: string): Promise<boolean>;
}

export class RemoteMemoryQueueProvider implements MemoryQueueProvider {
  private endpoint: string;
  private enabled: boolean;

  constructor(options: { endpoint?: string; enabled?: boolean } = {}) {
    this.endpoint = options.endpoint ?? "http://127.0.0.1:8420/memory/queue";
    this.enabled = options.enabled ?? true;
  }

  public isEnabled(): boolean {
    return this.enabled;
  }

  public async enqueue(kind: JobKind, payload: Record<string, unknown>, dedupeKey: string): Promise<MemoryJob | null> {
    if (!this.enabled) return null;
    try {
      const res = await fetch(`${this.endpoint}/enqueue`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ kind, payload, dedupe_key: dedupeKey }),
      });
      if (!res.ok) return null;
      return (await res.json()) as MemoryJob;
    } catch {
      return null;
    }
  }

  public async claimNext(): Promise<MemoryJob | null> {
    if (!this.enabled) return null;
    try {
      const res = await fetch(`${this.endpoint}/claim`, { method: "POST" });
      if (!res.ok) return null;
      return (await res.json()) as MemoryJob;
    } catch {
      return null;
    }
  }

  public async markDone(jobId: string, claimToken: string): Promise<boolean> {
    if (!this.enabled) return false;
    try {
      const res = await fetch(`${this.endpoint}/done`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_id: jobId, claim_token: claimToken }),
      });
      return res.ok;
    } catch {
      return false;
    }
  }
}
