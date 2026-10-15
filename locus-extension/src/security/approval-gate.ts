/**
 * Approval Gate Engine (§13.5)
 *
 * 10-minute TTL approval store for mutating tool calls in SUPERVISED autonomy mode.
 */

export interface ApprovalRequest {
  task_id: string;
  tool_name: string;
  params: Record<string, unknown>;
  status: "pending" | "approved" | "rejected" | "expired";
  created_at: number;
  expires_at: number;
}

export class ApprovalGate {
  private requests: Map<string, ApprovalRequest> = new Map();
  private defaultTtlSeconds: number = 600;

  public queueApproval(toolName: string, params: Record<string, unknown> = {}): ApprovalRequest {
    const tid = "appr_" + Math.random().toString(36).substring(2, 8);
    const now = Date.now();
    const req: ApprovalRequest = {
      task_id: tid,
      tool_name: toolName,
      params,
      status: "pending",
      created_at: now,
      expires_at: now + this.defaultTtlSeconds * 1000,
    };
    this.requests.set(tid, req);
    return req;
  }

  public approve(taskId: string): boolean {
    const req = this.requests.get(taskId);
    if (!req) return false;
    if (Date.now() > req.expires_at) {
      req.status = "expired";
      return false;
    }
    if (req.status === "pending") {
      req.status = "approved";
      return true;
    }
    return false;
  }

  public reject(taskId: string): boolean {
    const req = this.requests.get(taskId);
    if (!req) return false;
    if (req.status === "pending") {
      req.status = "rejected";
      return true;
    }
    return false;
  }

  public getStatus(taskId: string): string {
    const req = this.requests.get(taskId);
    if (!req) return "not_found";
    if (req.status === "pending" && Date.now() > req.expires_at) {
      req.status = "expired";
    }
    return req.status;
  }
}
