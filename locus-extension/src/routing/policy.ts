/**
 * SPEC §2.7-2.8 / F-0096 / US-37: Intelligent Model Routing Policy Engine.
 * Implements task classification and routing decision logic.
 */

import {
  CostSensitivity,
  LatencyBudget,
  RoutingConfig,
  RoutingDecision,
  RoutingHints,
  TargetBackend,
  TaskCategory,
  DEFAULT_ROUTING_CONFIG,
} from "./types";

export const MODEL_REASONING_V1 = "google/gemini-2.5-pro";
export const MODEL_CHAT_V1 = "deepseek/deepseek-chat";
export const MODEL_AGENTIC_V1 = "deepseek/deepseek-chat";
export const MODEL_CODING_V1 = "deepseek/deepseek-chat";
export const MODEL_LOCAL_DEFAULT = "ollama/llama3.2:3b";

/**
 * SPEC §2.7-2.8 TASK CLASSIFICATION (policy.rs):
 * "hint:quick", "hint:fast" -> Lightweight
 * "hint:medium"             -> Medium
 * "hint:reasoning", "hint:agentic", "hint:coding", "hint:chat" -> Heavy
 * explicit model name or unknown -> Heavy
 *
 * GOTCHA: "hint:chat" goes remote despite being conversational.
 * classify() maps it to Heavy because local model TTFT is too slow.
 */
export function classify(modelString: string): TaskCategory {
  const ms = (modelString || "").trim().toLowerCase();
  if (ms.startsWith("hint:")) {
    const hint = ms.slice(5);
    if (hint === "quick" || hint === "fast") {
      return "lightweight";
    }
    if (hint === "medium") {
      return "medium";
    }
    if (["reasoning", "agentic", "coding", "chat"].includes(hint)) {
      return "heavy";
    }
    return "heavy";
  }

  // Explicit model names or unknown strings default to Heavy
  return "heavy";
}

/**
 * Normalizes hint strings to concrete backend models.
 */
export function normalizeModelId(hintOrModel: string): string {
  const h = (hintOrModel || "").trim();
  switch (h) {
    case "hint:reasoning":
      return MODEL_REASONING_V1;
    case "hint:chat":
    case "hint:agentic":
    case "hint:coding":
    case "hint:medium":
      return MODEL_CHAT_V1;
    case "hint:quick":
    case "hint:fast":
      return MODEL_LOCAL_DEFAULT;
    default:
      return h;
  }
}

/**
 * SPEC §2.7-2.8 ROUTING DECISION (policy.rs):
 * Computes (primary, fallback) target backend given task category, local server health,
 * and request routing hints.
 */
export function decide(
  category: TaskCategory,
  localHealthy: boolean,
  hints: RoutingHints = {},
  hasTools = false,
  config: Partial<RoutingConfig> = {}
): RoutingDecision {
  const mergedConfig = { ...DEFAULT_ROUTING_CONFIG, ...config };

  // If routing is globally disabled, send all requests to remote primary
  if (!mergedConfig.enabled) {
    return {
      category,
      primary: "remote",
      fallback: null,
      supportsStreaming: true,
      resolvedModel: MODEL_CHAT_V1,
      reason: "Routing globally disabled; default remote primary",
    };
  }

  // PRIVACY_REQUIRED: forces local for all categories, fails closed with no fallback
  const privacyRequired = Boolean(hints.privacyRequired || mergedConfig.privacyMode);
  if (privacyRequired) {
    return {
      category,
      primary: "local",
      fallback: null,
      supportsStreaming: false,
      resolvedModel: MODEL_LOCAL_DEFAULT,
      reason: "Privacy required: local execution forced, fail-closed without remote fallback",
    };
  }

  let primary: TargetBackend = "remote";
  let fallback: TargetBackend | null = null;
  let reason = "Default remote execution";

  if (category === "lightweight") {
    if (localHealthy) {
      primary = "local";
      fallback = "remote";
      reason = "Lightweight task routed to local model server";
    } else {
      primary = "remote";
      fallback = null;
      reason = "Lightweight task routed to remote due to unhealthy local server";
    }
  } else if (category === "medium") {
    if (
      localHealthy &&
      (hints.latencyBudget === "low" || hints.costSensitivity === "high")
    ) {
      primary = "local";
      fallback = "remote";
      reason = "Medium task routed to local due to Low latency budget or High cost sensitivity";
    } else {
      primary = "remote";
      fallback = localHealthy ? "local" : null;
      reason = "Medium task routed to remote backend by default";
    }
  } else if (category === "heavy") {
    primary = "remote";
    fallback = null;
    reason = "Heavy task routed to remote backend";
  }

  // TOOLS FORCE REMOTE:
  // If request carries tools and policy chose local -> override to remote
  if (hasTools && primary === "local") {
    primary = "remote";
    fallback = null;
    reason = "Tools present: overridden to remote (local lacks native tool calling)";
  }

  const resolvedModel = primary === "local" ? MODEL_LOCAL_DEFAULT : MODEL_CHAT_V1;

  return {
    category,
    primary,
    fallback,
    supportsStreaming: true,
    resolvedModel,
    reason,
  };
}
