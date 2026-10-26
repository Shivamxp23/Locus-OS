/**
 * SPEC §13.5 lines 3333-3365:
 * Approval Gate Client (F-0109 / US-71).
 * TypeScript contract and client for 10-minute TTL approval gating,
 * queueing approval requests, polling status, and user resolution.
 */

export type ApprovalStatus = "pending" | "approved" | "rejected" | "expired";

export interface ApprovalRequest {
  task_id: string;
  changes: unknown;
  status: ApprovalStatus;
  created_at: number;
  expires_at: number;
  resolved_at?: number | null;
  resolved_by?: string | null;
}

export class ApprovalGateClient {
  private baseUrl: string;

  constructor(baseUrl: string = "http://127.0.0.1:8420") {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  /**
   * SPEC §13.5: FUNCTION queue_approval(task_id, changes, ttl=600)
   */
  async queueApproval(
    taskId: string,
    changes: unknown,
    ttl: number = 600
  ): Promise<ApprovalRequest> {
    const url = `${this.baseUrl}/security/approval/request`;
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task_id: taskId, changes, ttl }),
    });
    if (resp.status === 503) {
      // Off switch: auto-approve
      return {
        task_id: taskId,
        changes,
        status: "approved",
        created_at: Date.now() / 1000,
        expires_at: Date.now() / 1000 + ttl,
        resolved_at: Date.now() / 1000,
        resolved_by: "off_switch_auto_approved",
      };
    }
    if (!resp.ok) {
      throw new Error(`Failed to queue approval request: ${resp.status}`);
    }
    const data = (await resp.json()) as { status: string; request: ApprovalRequest };
    return data.request;
  }

  /**
   * SPEC §13.5: Get approval request status.
   */
  async getStatus(taskId: string): Promise<ApprovalRequest | null> {
    const url = `${this.baseUrl}/security/approval/status?task_id=${encodeURIComponent(taskId)}`;
    const resp = await fetch(url, { method: "GET" });
    if (resp.status === 503) {
      return null;
    }
    if (!resp.ok) {
      throw new Error(`Failed to get approval status: ${resp.status}`);
    }
    const data = (await resp.json()) as { status: string; request?: ApprovalRequest };
    return data.request || null;
  }

  /**
   * SPEC §13.5: Resolve approval (approve or reject).
   */
  async resolve(
    taskId: string,
    status: "approved" | "rejected",
    resolvedBy?: string
  ): Promise<ApprovalRequest | null> {
    const url = `${this.baseUrl}/security/approval/resolve`;
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task_id: taskId, status, resolved_by: resolvedBy }),
    });
    if (resp.status === 503) {
      return null;
    }
    if (!resp.ok) {
      throw new Error(`Failed to resolve approval: ${resp.status}`);
    }
    const data = (await resp.json()) as { status: string; request?: ApprovalRequest };
    return data.request || null;
  }

  /**
   * SPEC §13.5: FUNCTION wait_for_approval(task_id, ttl)
   */
  async waitForApproval(
    taskId: string,
    timeoutSeconds: number = 600,
    pollIntervalMs: number = 2000
  ): Promise<boolean> {
    const deadline = Date.now() + timeoutSeconds * 1000;
    while (Date.now() < deadline) {
      const req = await this.getStatus(taskId);
      if (!req) {
        return false;
      }
      if (req.status === "approved") {
        return true;
      }
      if (req.status === "rejected" || req.status === "expired") {
        return false;
      }
      await new Promise((resolve) => setTimeout(resolve, pollIntervalMs));
    }
    return false; // TTL expired = auto-reject
  }

  /**
   * SPEC §13.5: List active pending approvals.
   */
  async listPending(): Promise<ApprovalRequest[]> {
    const url = `${this.baseUrl}/security/approval/pending`;
    const resp = await fetch(url, { method: "GET" });
    if (resp.status === 503) {
      return [];
    }
    if (!resp.ok) {
      throw new Error(`Failed to list pending approvals: ${resp.status}`);
    }
    const data = (await resp.json()) as { status: string; pending: ApprovalRequest[] };
    return data.pending || [];
  }

  /**
   * Creates an approval provider callback for AutonomyTiersClient.
   */
  createApprovalProvider(ttlSeconds: number = 600): (toolName: string, reason: string) => Promise<boolean> {
    return async (toolName: string, reason: string): Promise<boolean> => {
      const taskId = `approval-${Date.now()}-${Math.random().toString(36).substring(2, 8)}`;
      await this.queueApproval(taskId, { tool: toolName, reason }, ttlSeconds);
      return await this.waitForApproval(taskId, ttlSeconds, 1000);
    };
  }
}
