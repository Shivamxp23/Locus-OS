/**
 * Usage / Cost Tracking Engine (§1.10)
 *
 * Granular token measurement and USD expenditure tracking.
 */

export interface CanonicalUsage {
  input_tokens: number;
  output_tokens: number;
  cache_read_tokens?: number;
  cache_write_tokens?: number;
  reasoning_tokens?: number;
}

export interface PricingEntry {
  input_per_million: number;
  output_per_million: number;
  cache_read_per_million?: number;
  cache_write_per_million?: number;
}

export interface CostResult {
  amount_usd: number;
  status: "actual" | "estimated" | "included";
}

export const DEFAULT_PRICING: Record<string, PricingEntry> = {
  "deepseek-chat": { input_per_million: 0.14, output_per_million: 0.28 },
  "gemini-2.5-pro": { input_per_million: 1.25, output_per_million: 5.00 },
  "gemini-2.5-flash": { input_per_million: 0.075, output_per_million: 0.30 },
  "claude-3-5-sonnet": { input_per_million: 3.00, output_per_million: 15.00 },
};

export function calculateRequestCost(usage: CanonicalUsage, pricing: PricingEntry): CostResult {
  const cost =
    (usage.input_tokens / 1000000) * pricing.input_per_million +
    (usage.output_tokens / 1000000) * pricing.output_per_million +
    ((usage.cache_read_tokens || 0) / 1000000) * (pricing.cache_read_per_million || 0) +
    ((usage.cache_write_tokens || 0) / 1000000) * (pricing.cache_write_per_million || 0);

  return {
    amount_usd: Math.round(cost * 1000000) / 1000000,
    status: "actual",
  };
}

export class CostTracker {
  private totalCostUsd: number = 0;
  private pricing: Record<string, PricingEntry>;

  constructor(pricing: Record<string, PricingEntry> = DEFAULT_PRICING) {
    this.pricing = pricing;
  }

  public recordUsage(model: string, usage: CanonicalUsage): CostResult {
    const entry = this.pricing[model] || { input_per_million: 1.0, output_per_million: 3.0 };
    const res = calculateRequestCost(usage, entry);
    this.totalCostUsd = Math.round((this.totalCostUsd + res.amount_usd) * 1000000) / 1000000;
    return res;
  }

  public getTotalCost(): number {
    return this.totalCostUsd;
  }
}
