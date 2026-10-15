/**
 * Autonomy Tiers Engine (§13.4)
 *
 * Enforces READONLY, SUPERVISED, and FULL autonomy tiers in beforeToolCall.
 */

export type AutonomyTier = "readonly" | "supervised" | "full";

export const READ_ONLY_TOOLS = new Set([
  "read",
  "grep",
  "find",
  "ls",
  "locus_memory",
  "locus_doctor",
  "locus_pageindex",
  "locus_diagram",
  "locus_research",
]);

export const MUTATING_TOOLS = new Set([
  "write",
  "edit",
  "bash",
  "terminal",
  "locus_vault",
  "locus_delegate_code",
]);

export class AutonomyManager {
  private tier: AutonomyTier;

  constructor(initialTier: AutonomyTier = "supervised") {
    this.tier = initialTier;
  }

  public setTier(tier: AutonomyTier): void {
    this.tier = tier;
  }

  public getTier(): AutonomyTier {
    return this.tier;
  }

  public canExecuteTool(toolName: string): { allowed: boolean; requiresApproval: boolean; reason: string } {
    const clean = toolName.toLowerCase().trim();

    if (this.tier === "full") {
      return { allowed: true, requiresApproval: false, reason: "Full autonomy: all tools permitted" };
    }

    if (READ_ONLY_TOOLS.has(clean)) {
      return { allowed: true, requiresApproval: false, reason: "Read-only tool permitted" };
    }

    if (this.tier === "readonly") {
      return { allowed: false, requiresApproval: false, reason: `Tool ${clean} denied in READONLY mode` };
    }

    // Supervised mode: mutating tools require approval
    return { allowed: true, requiresApproval: true, reason: `Tool ${clean} requires approval in SUPERVISED mode` };
  }
}
