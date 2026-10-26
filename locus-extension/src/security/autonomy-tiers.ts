/**
 * SPEC §13.4 lines 3308-3332:
 * Autonomy Tiers Client (F-0108 / US-70).
 * TypeScript contract and client for tier configuration, tool classification,
 * permission evaluation, and Pi beforeToolCall hook adaptation.
 */

export type AutonomyTier = "readonly" | "supervised" | "full";
export type ToolCategory = "read" | "write" | "terminal" | "system";

export interface TierEvaluationDecision {
  allowed: boolean;
  requires_approval: boolean;
  tier: string;
  tool_name: string;
  category: string;
  reason?: string | null;
}

export interface TierInfo {
  tier: string;
  description: string;
  allowed_categories: string[];
  requires_approval: string[];
}

export interface BeforeToolCallContextLike {
  toolCall: {
    id?: string;
    name: string;
  };
  args?: unknown;
}

export interface BeforeToolCallResultLike {
  block?: boolean;
  reason?: string;
  terminate?: boolean;
}

export class AutonomyTiersClient {
  private baseUrl: string;

  constructor(baseUrl: string = "http://127.0.0.1:8420") {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  /**
   * SPEC §13.4: Get current autonomy tier.
   */
  async getTier(): Promise<AutonomyTier> {
    const url = `${this.baseUrl}/security/autonomy/tier`;
    const resp = await fetch(url, { method: "GET" });
    if (resp.status === 503) {
      // Off switch fallback: treated as full (trusted)
      return "full";
    }
    if (!resp.ok) {
      throw new Error(`Failed to get autonomy tier: ${resp.status}`);
    }
    const data = (await resp.json()) as { status: string; tier: AutonomyTier };
    return data.tier;
  }

  /**
   * SPEC §13.4: Set active autonomy tier.
   */
  async setTier(tier: AutonomyTier): Promise<{ status: string; tier: string }> {
    const url = `${this.baseUrl}/security/autonomy/tier`;
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tier }),
    });
    if (resp.status === 503) {
      return { status: "disabled", tier: "full" };
    }
    if (!resp.ok) {
      throw new Error(`Failed to set autonomy tier: ${resp.status}`);
    }
    return (await resp.json()) as { status: string; tier: string };
  }

  /**
   * SPEC §13.4: Classify tool category.
   */
  async classify(
    toolName: string,
    category?: ToolCategory
  ): Promise<{ status: string; tool_name: string; category: string }> {
    const url = `${this.baseUrl}/security/autonomy/classify`;
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tool_name: toolName, category }),
    });
    if (resp.status === 503) {
      return { status: "disabled", tool_name: toolName, category: "read" };
    }
    if (!resp.ok) {
      throw new Error(`Failed to classify tool: ${resp.status}`);
    }
    return (await resp.json()) as { status: string; tool_name: string; category: string };
  }

  /**
   * SPEC §13.4: Evaluate tool call against autonomy tier permissions.
   */
  async evaluate(
    toolName: string,
    hasApproval: boolean = false,
    category?: ToolCategory,
    tier?: AutonomyTier
  ): Promise<TierEvaluationDecision> {
    const url = `${this.baseUrl}/security/autonomy/evaluate`;
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tool_name: toolName,
        has_approval: hasApproval,
        category,
        tier,
      }),
    });
    if (resp.status === 503) {
      // Off switch: allow all tools
      return {
        allowed: true,
        requires_approval: false,
        tier: "full",
        tool_name: toolName,
        category: category || "read",
        reason: "Autonomy tier enforcement disabled (off-switch)",
      };
    }
    if (!resp.ok) {
      throw new Error(`Failed to evaluate autonomy tool call: ${resp.status}`);
    }
    const data = (await resp.json()) as { status: string; decision: TierEvaluationDecision };
    return data.decision;
  }

  /**
   * SPEC §13.4: List all available autonomy tiers.
   */
  async getTiers(): Promise<TierInfo[]> {
    const url = `${this.baseUrl}/security/autonomy/tiers`;
    const resp = await fetch(url, { method: "GET" });
    if (resp.status === 503) {
      return [];
    }
    if (!resp.ok) {
      throw new Error(`Failed to fetch tiers info: ${resp.status}`);
    }
    const data = (await resp.json()) as { status: string; tiers: TierInfo[] };
    return data.tiers;
  }

  /**
   * SPEC §13.4: Creates a beforeToolCall hook for Pi's agent loop.
   */
  createBeforeToolCallHook(
    approvalProvider?: (toolName: string, reason: string) => Promise<boolean>
  ): (context: BeforeToolCallContextLike) => Promise<BeforeToolCallResultLike | undefined> {
    return async (context: BeforeToolCallContextLike): Promise<BeforeToolCallResultLike | undefined> => {
      const toolName = context.toolCall?.name || "";
      const decision = await this.evaluate(toolName, false);

      if (decision.allowed) {
        return undefined; // Allowed to proceed
      }

      if (decision.requires_approval && approvalProvider) {
        const approved = await approvalProvider(toolName, decision.reason || "Approval required");
        if (approved) {
          return undefined; // Approved
        }
        return {
          block: true,
          reason: `Execution of tool '${toolName}' was rejected by user approval gate.`,
        };
      }

      return {
        block: true,
        reason: decision.reason || `Execution of tool '${toolName}' is blocked by autonomy tier policy.`,
      };
    };
  }
}
