/**
 * SPEC §1.10 / F-0010 / US-29: TypeScript Usage / Cost Tracking.
 */
import { isEnabled } from "../config";
import { PricingEntry, resolvePricing } from "./pricing";

export interface CanonicalUsage {
  inputTokens: number;
  outputTokens: number;
  cacheReadTokens: number;
  cacheWriteTokens: number;
  reasoningTokens: number;
  requestCount: number;
  promptTokens: number;
  totalTokens: number;
}

export interface CostResult {
  amountUsd: number;
  status: string;
  source: string;
  label: string;
}

/**
 * Compute prompt and total tokens from components.
 */
export function computeCanonicalUsage(
  inputTokens: number,
  outputTokens: number,
  cacheReadTokens: number = 0,
  cacheWriteTokens: number = 0,
  reasoningTokens: number = 0,
  requestCount: number = 1
): CanonicalUsage {
  const promptTokens = inputTokens + cacheReadTokens + cacheWriteTokens;
  const totalTokens = promptTokens + outputTokens;
  return {
    inputTokens,
    outputTokens,
    cacheReadTokens,
    cacheWriteTokens,
    reasoningTokens,
    requestCount,
    promptTokens,
    totalTokens,
  };
}

/**
 * SPEC §1.10 line 2314:
 * Extract canonical usage from provider raw response.
 */
export function extractCanonicalUsage(
  rawResponse: any,
  provider: string = ""
): CanonicalUsage {
  if (!rawResponse || typeof rawResponse !== "object") {
    return computeCanonicalUsage(0, 0);
  }

  const usage = rawResponse.usage || rawResponse.usageMetadata || rawResponse.usage_metadata || rawResponse;

  let input = 0;
  let output = 0;
  let cacheRead = 0;
  let cacheWrite = 0;
  let reasoning = 0;

  if (usage && typeof usage === "object") {
    // Anthropic
    if ("input_tokens" in usage || "output_tokens" in usage) {
      input = Number(usage.input_tokens) || 0;
      output = Number(usage.output_tokens) || 0;
      cacheWrite = Number(usage.cache_creation_input_tokens) || 0;
      cacheRead = Number(usage.cache_read_input_tokens) || 0;
    }
    // OpenAI
    else if ("prompt_tokens" in usage || "completion_tokens" in usage) {
      const rawPrompt = Number(usage.prompt_tokens) || 0;
      output = Number(usage.completion_tokens) || 0;
      if (usage.prompt_tokens_details) {
        cacheRead = Number(usage.prompt_tokens_details.cached_tokens) || 0;
      }
      if (usage.completion_tokens_details) {
        reasoning = Number(usage.completion_tokens_details.reasoning_tokens) || 0;
      }
      input = Math.max(0, rawPrompt - cacheRead);
    }
    // Google
    else if ("promptTokenCount" in usage || "prompt_token_count" in usage) {
      input = Number(usage.promptTokenCount || usage.prompt_token_count) || 0;
      output = Number(usage.candidatesTokenCount || usage.candidates_token_count) || 0;
      cacheRead = Number(usage.cachedContentTokenCount || usage.cached_content_token_count) || 0;
      if (cacheRead > 0 && input >= cacheRead) {
        input = Math.max(0, input - cacheRead);
      }
    }
    // Pi
    else if ("input" in usage || "output" in usage) {
      input = Number(usage.input) || 0;
      output = Number(usage.output) || 0;
      cacheRead = Number(usage.cacheRead) || 0;
      cacheWrite = Number(usage.cacheWrite) || 0;
    }
  }

  return computeCanonicalUsage(input, output, cacheRead, cacheWrite, reasoning, 1);
}

/**
 * SPEC §1.10 line 2329:
 * Calculate cost from usage and pricing rates.
 */
export function calculateCost(
  usage: CanonicalUsage,
  pricing: PricingEntry
): CostResult {
  let cost = 0;
  cost += (usage.inputTokens / 1_000_000) * pricing.inputCostPerMillion;
  cost += (usage.outputTokens / 1_000_000) * pricing.outputCostPerMillion;
  if (pricing.cacheReadCostPerMillion > 0) {
    cost += (usage.cacheReadTokens / 1_000_000) * pricing.cacheReadCostPerMillion;
  }
  if (pricing.cacheWriteCostPerMillion > 0) {
    cost += (usage.cacheWriteTokens / 1_000_000) * pricing.cacheWriteCostPerMillion;
  }
  if (pricing.requestCost > 0) {
    cost += pricing.requestCost * usage.requestCount;
  }

  const rounded = Math.round(cost * 1_000_000) / 1_000_000;
  const label = `$${rounded.toFixed(4)}`;
  const status =
    pricing.source === "user_override" || pricing.source === "official_docs_snapshot"
      ? "actual"
      : "estimated";

  return {
    amountUsd: rounded,
    status,
    source: pricing.source,
    label,
  };
}

/**
 * SPEC §1.10 line 2346:
 * Format usage display string.
 */
export function formatUsageDisplay(
  sessionUsd: number,
  dailyUsd: number,
  totalTokens: number
): string {
  return `Session: $${sessionUsd.toFixed(4)} | Today: $${dailyUsd.toFixed(4)} | Tokens: ${totalTokens.toLocaleString()}`;
}

/**
 * Singleton UsageTracker per session.
 */
export class UsageTracker {
  private static instance: UsageTracker | null = null;
  private sessionUsd: number = 0;
  private sessionTokens: number = 0;
  private dailyUsd: number = 0;

  public static getInstance(): UsageTracker {
    if (!UsageTracker.instance) {
      UsageTracker.instance = new UsageTracker();
    }
    return UsageTracker.instance;
  }

  public isEnabled(): boolean {
    return (
      isEnabled("locus.usage_cost_tracking.enabled") ||
      isEnabled("locus.tracking.cost.enabled")
    );
  }

  public recordResponseUsage(
    rawResponse: any,
    model: string,
    provider: string = ""
  ): CostResult | null {
    if (!this.isEnabled()) return null;
    const usage = extractCanonicalUsage(rawResponse, provider);
    const pricing = resolvePricing(model, provider);
    const cost = calculateCost(usage, pricing);

    this.sessionUsd += cost.amountUsd;
    this.sessionTokens += usage.totalTokens;
    this.dailyUsd += cost.amountUsd;

    return cost;
  }

  public getSummary(): { sessionUsd: number; dailyUsd: number; totalTokens: number; display: string } {
    return {
      sessionUsd: this.sessionUsd,
      dailyUsd: this.dailyUsd,
      totalTokens: this.sessionTokens,
      display: formatUsageDisplay(this.sessionUsd, this.dailyUsd, this.sessionTokens),
    };
  }

  public reset(): void {
    this.sessionUsd = 0;
    this.sessionTokens = 0;
  }
}
