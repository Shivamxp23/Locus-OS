/**
 * SPEC §1.10 / F-0010 / US-29: TypeScript Model Pricing Resolution.
 */
export interface PricingEntry {
  inputCostPerMillion: number;
  outputCostPerMillion: number;
  cacheReadCostPerMillion: number;
  cacheWriteCostPerMillion: number;
  requestCost: number;
  source: string;
}

export const OFFICIAL_PRICING_SNAPSHOT: Record<string, { input: number; output: number; cacheRead?: number; cacheWrite?: number }> = {
  "claude-3-5-sonnet": { input: 3.00, output: 15.00, cacheRead: 0.30, cacheWrite: 3.75 },
  "claude-3-7-sonnet": { input: 3.00, output: 15.00, cacheRead: 0.30, cacheWrite: 3.75 },
  "claude-3-opus": { input: 15.00, output: 75.00, cacheRead: 1.50, cacheWrite: 18.75 },
  "claude-3-5-haiku": { input: 0.80, output: 4.00, cacheRead: 0.08, cacheWrite: 1.00 },
  "claude-3-haiku": { input: 0.25, output: 1.25, cacheRead: 0.03, cacheWrite: 0.30 },
  "gpt-4o": { input: 2.50, output: 10.00, cacheRead: 1.25 },
  "gpt-4o-mini": { input: 0.15, output: 0.60, cacheRead: 0.075 },
  "o1": { input: 15.00, output: 60.00, cacheRead: 7.50 },
  "o1-mini": { input: 1.10, output: 4.40, cacheRead: 0.55 },
  "o3-mini": { input: 1.10, output: 4.40, cacheRead: 0.55 },
  "gemini-1.5-pro": { input: 3.50, output: 10.50, cacheRead: 0.875 },
  "gemini-1.5-flash": { input: 0.075, output: 0.30, cacheRead: 0.01875 },
  "gemini-2.0-flash": { input: 0.10, output: 0.40, cacheRead: 0.025 },
  "gemini-2.0-pro": { input: 2.50, output: 10.00, cacheRead: 0.625 },
};

/**
 * SPEC §1.10 line 2322:
 * Priority: user_override > provider_cost_api > official_docs_snapshot > unknown.
 */
export function resolvePricing(
  model: string,
  provider: string = "",
  userOverrides?: Record<string, PricingEntry>
): PricingEntry {
  const normModel = (model || "").trim().toLowerCase();

  if (userOverrides && normModel in userOverrides) {
    return userOverrides[normModel];
  }

  if (normModel in OFFICIAL_PRICING_SNAPSHOT) {
    const data = OFFICIAL_PRICING_SNAPSHOT[normModel];
    return {
      inputCostPerMillion: data.input,
      outputCostPerMillion: data.output,
      cacheReadCostPerMillion: data.cacheRead || 0,
      cacheWriteCostPerMillion: data.cacheWrite || 0,
      requestCost: 0,
      source: "official_docs_snapshot",
    };
  }

  for (const [key, data] of Object.entries(OFFICIAL_PRICING_SNAPSHOT)) {
    if (normModel.startsWith(key) || normModel.includes(key)) {
      return {
        inputCostPerMillion: data.input,
        outputCostPerMillion: data.output,
        cacheReadCostPerMillion: data.cacheRead || 0,
        cacheWriteCostPerMillion: data.cacheWrite || 0,
        requestCost: 0,
        source: "official_docs_snapshot",
      };
    }
  }

  return {
    inputCostPerMillion: 0,
    outputCostPerMillion: 0,
    cacheReadCostPerMillion: 0,
    cacheWriteCostPerMillion: 0,
    requestCost: 0,
    source: "unknown",
  };
}
