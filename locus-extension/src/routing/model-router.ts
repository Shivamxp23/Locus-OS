/**
 * locus-extension/src/routing/model-router.ts - Intelligent Model Router
 *
 * Implements Spec §2.7-2.8 (Intelligent Model Routing + Quality Fallback).
 */

export type TaskCategory = "LIGHTWEIGHT" | "MEDIUM" | "HEAVY";
export type RouteTarget = "LOCAL" | "REMOTE";

export interface RoutingHints {
  latencyBudget?: "Low" | "Medium" | "High";
  costSensitivity?: "Low" | "Medium" | "High";
  privacyRequired?: boolean;
  hasTools?: boolean;
}

export interface ModelRouterProvider {
  classify(hintOrModel: string): TaskCategory;
  decide(category: TaskCategory, hints: RoutingHints): [RouteTarget, RouteTarget | null];
}

export class LocalModelRouter implements ModelRouterProvider {
  private enabled: boolean;

  constructor(options: { enabled?: boolean } = {}) {
    this.enabled = options.enabled ?? true;
  }

  public classify(hintOrModel: string): TaskCategory {
    const s = hintOrModel.toLowerCase().trim();
    if (s.includes("quick") || s.includes("fast")) return "LIGHTWEIGHT";
    if (s.includes("medium")) return "MEDIUM";
    return "HEAVY";
  }

  public decide(category: TaskCategory, hints: RoutingHints): [RouteTarget, RouteTarget | null] {
    if (!this.enabled) return ["REMOTE", null];
    if (hints.privacyRequired) return ["LOCAL", null];
    if (hints.hasTools) return ["REMOTE", null];

    if (category === "LIGHTWEIGHT") {
      return ["LOCAL", "REMOTE"];
    } else if (category === "MEDIUM") {
      if (hints.latencyBudget === "Low" || hints.costSensitivity === "High") {
        return ["LOCAL", "REMOTE"];
      }
      return ["REMOTE", "LOCAL"];
    } else {
      return ["REMOTE", null];
    }
  }

  public isLowQuality(response: string): boolean {
    const s = response.trim();
    if (s.length < 20) return true;
    if (s === "..." || s === "I" || s === "?") return true;
    const refusals = ["i cannot", "i can't", "i am unable", "i apologize but", "as an ai"];
    const lower = s.toLowerCase();
    return refusals.some((r) => lower.includes(r));
  }
}
