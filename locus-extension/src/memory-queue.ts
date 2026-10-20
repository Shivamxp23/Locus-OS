/**
 * locus-extension/src/memory-queue.ts
 *
 * TypeScript client for Memory Queue (Async Job Pipeline).
 * Implements Spec §4.8:
 * - Async pipeline driving extraction, scoring, summarisation, and digesting off ingest hot path.
 * - Enqueue with dedupe suppression, atomic claim pattern with lease tokens.
 * - Settlement guards (mark_done / mark_failed), stale lock recovery, and scheduler helpers.
 */

export type JobKind =
  | "extract_chunk"
  | "append_buffer"
  | "seal"
  | "topic_route"
  | "digest_daily"
  | "flush_stale";

export type JobStatus = "ready" | "running" | "done" | "failed";

export interface JobRecord {
  id: number;
  kind: JobKind;
  payload: Record<string, any>;
  status: JobStatus;
  dedupe_key?: string | null;
  created_at: string;
  claimed_at?: string | null;
  claim_token?: string | null;
  completed_at?: string | null;
  error_message?: string | null;
  retry_count: number;
}

export interface QueueStats {
  total: number;
  ready: number;
  running: number;
  done: number;
  failed: number;
  llm_concurrency: number;
  workers: number;
}

export interface MemoryQueueConfig {
  workers: number;
  enabled: boolean;
  db_path?: string;
  lock_duration_ms: number;
  llm_concurrency: number;
  throttle_gate_enabled: boolean;
}

export class MemoryQueueClient {
  private readonly baseUrl: string;

  constructor(baseUrl: string = "http://127.0.0.1:8000") {
    this.baseUrl = baseUrl.replace(/\/+$/, "");
  }

  /**
   * Retrieve Memory Queue configuration and health.
   */
  public async getConfig(): Promise<Record<string, any>> {
    const res = await fetch(`${this.baseUrl}/memory/queue/config`);
    if (!res.ok) {
      throw new Error(`Failed to get queue config: ${res.statusText} (${res.status})`);
    }
    return res.json();
  }

  /**
   * Get queue status counts and concurrency stats.
   */
  public async getStats(): Promise<QueueStats> {
    const res = await fetch(`${this.baseUrl}/memory/queue/stats`);
    if (!res.ok) {
      throw new Error(`Failed to get queue stats: ${res.statusText} (${res.status})`);
    }
    const data = await res.json();
    return data.stats as QueueStats;
  }

  /**
   * List jobs in queue, optionally filtered by status.
   */
  public async listJobs(status?: JobStatus, limit: number = 50): Promise<JobRecord[]> {
    const params = new URLSearchParams();
    if (status) params.set("status", status);
    params.set("limit", String(limit));
    const res = await fetch(`${this.baseUrl}/memory/queue/jobs?${params.toString()}`);
    if (!res.ok) {
      throw new Error(`Failed to list jobs: ${res.statusText} (${res.status})`);
    }
    const data = await res.json();
    return (data.jobs as JobRecord[]) || [];
  }

  /**
   * Get single job by ID.
   */
  public async getJob(jobId: number): Promise<JobRecord | null> {
    const res = await fetch(`${this.baseUrl}/memory/queue/jobs/${jobId}`);
    if (res.status === 404) return null;
    if (!res.ok) {
      throw new Error(`Failed to get job ${jobId}: ${res.statusText} (${res.status})`);
    }
    const data = await res.json();
    return data.job as JobRecord;
  }

  /**
   * Enqueue a new memory processing job with optional deduplication key.
   */
  public async enqueueJob(
    kind: JobKind,
    payload: Record<string, any>,
    dedupeKey?: string
  ): Promise<{ job_id: number | null; suppressed: boolean }> {
    const res = await fetch(`${this.baseUrl}/memory/queue/enqueue`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ kind, payload, dedupe_key: dedupeKey }),
    });
    if (!res.ok) {
      throw new Error(`Failed to enqueue job: ${res.statusText} (${res.status})`);
    }
    return res.json();
  }

  /**
   * Claim next ready job atomically.
   */
  public async claimNext(workerId: string): Promise<JobRecord | null> {
    const res = await fetch(`${this.baseUrl}/memory/queue/claim`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ worker_id: workerId }),
    });
    if (!res.ok) {
      throw new Error(`Failed to claim job: ${res.statusText} (${res.status})`);
    }
    const data = await res.json();
    return (data.job as JobRecord) || null;
  }

  /**
   * Settle job with token guard (done or failed).
   */
  public async settleJob(
    jobId: number,
    claimToken: string,
    success: boolean,
    errorMessage?: string
  ): Promise<boolean> {
    const res = await fetch(`${this.baseUrl}/memory/queue/settle`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        job_id: jobId,
        claim_token: claimToken,
        success,
        error_message: errorMessage,
      }),
    });
    if (!res.ok) {
      throw new Error(`Failed to settle job: ${res.statusText} (${res.status})`);
    }
    const data = await res.json();
    return Boolean(data.settled);
  }

  /**
   * Reset stale running locks whose leases have expired.
   */
  public async recoverStaleLocks(lockDurationMs?: number): Promise<number> {
    const res = await fetch(`${this.baseUrl}/memory/queue/recover_stale`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lock_duration_ms: lockDurationMs }),
    });
    if (!res.ok) {
      throw new Error(`Failed to recover stale locks: ${res.statusText} (${res.status})`);
    }
    const data = await res.json();
    return Number(data.recovered_count || 0);
  }

  /**
   * Trigger single daily digest.
   */
  public async triggerDigest(dateStr: string): Promise<number | null> {
    const res = await fetch(`${this.baseUrl}/memory/queue/trigger_digest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ date: dateStr }),
    });
    if (!res.ok) {
      throw new Error(`Failed to trigger digest: ${res.statusText} (${res.status})`);
    }
    const data = await res.json();
    return data.job_id ?? null;
  }

  /**
   * Backfill missing digests across a date range.
   */
  public async backfillDigests(fromDate: string, toDate: string): Promise<number[]> {
    const res = await fetch(`${this.baseUrl}/memory/queue/backfill_digests`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ from_date: fromDate, to_date: toDate }),
    });
    if (!res.ok) {
      throw new Error(`Failed to backfill digests: ${res.statusText} (${res.status})`);
    }
    const data = await res.json();
    return (data.enqueued_ids as number[]) || [];
  }

  /**
   * Enqueue stale buffer flush for a given date.
   */
  public async flushStale(dateStr: string): Promise<number | null> {
    const res = await fetch(`${this.baseUrl}/memory/queue/flush_stale`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ date: dateStr }),
    });
    if (!res.ok) {
      throw new Error(`Failed to flush stale: ${res.statusText} (${res.status})`);
    }
    const data = await res.json();
    return data.job_id ?? null;
  }
}
