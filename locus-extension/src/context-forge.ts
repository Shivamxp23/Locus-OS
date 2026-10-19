/**
 * SPEC §2.5 / F-0094 / US-34: Context Forge (Stage 6) — The 6-Layer Assembler.
 * Consolidates parallel retrieval results, calculates global relevance scoring,
 * enforces layer token budgets, applies Headroom CCR compression, and prepends
 * identity system instructions and anti-hallucination directives.
 */
import { isEnabled } from "./config";

export interface LayerBudgetConfig {
  identity_limit: number;
  temporal_limit: number;
  events_limit: number;
  neo4j_limit: number;
  semantic_limit: number;
  web_limit: number;
  total_limit: number;
}

export const DEFAULT_LAYER_BUDGETS: LayerBudgetConfig = {
  identity_limit: 80,
  temporal_limit: 60,
  events_limit: 180,
  neo4j_limit: 150,
  semantic_limit: 200,
  web_limit: 100,
  total_limit: 800,
};

export interface AssembledLayer {
  layer_num: number;
  name: string;
  content: string;
  token_count: number;
}

export interface RetrievalInput {
  identity?: Record<string, any>;
  temporal?: Record<string, any>;
  events?: Array<Record<string, any>>;
  neo4j_paths?: Array<Record<string, any>>;
  semantic_snippets?: Array<Record<string, any>>;
  web_results?: Array<Record<string, any>>;
  intent_requires_web?: boolean;
}

export interface ContextForgeResult {
  assembled_prompt: string;
  layers: AssembledLayer[];
  total_tokens: number;
  compression_applied: boolean;
  hebbian_updates: Array<Record<string, any>>;
  metadata: Record<string, any>;
}

export interface ContextAssembler {
  assembleContext(
    input: RetrievalInput,
    budgetOverride?: Partial<LayerBudgetConfig>
  ): Promise<ContextForgeResult>;
  isFeatureEnabled(): boolean;
  calculateRelevanceScore(
    semanticSimilarity: number,
    recencyWeight: number,
    sourcePriority: number
  ): number;
}

export class ContextForge implements ContextAssembler {
  private sidecarBaseUrl: string;

  constructor(sidecarBaseUrl: string = "http://127.0.0.1:8420") {
    this.sidecarBaseUrl = sidecarBaseUrl;
  }

  public isFeatureEnabled(): boolean {
    const brainToggle = isEnabled("locus.brain.context_forge.enabled");
    if (!brainToggle) {
      return false;
    }
    return isEnabled("locus.context_forge.enabled");
  }

  /**
   * SPEC §2.5 STEP 2: Global Relevance Scoring
   * Unified Score = (semantic_similarity × 0.6) + (recency_weight × 0.25) + (source_priority × 0.15)
   */
  public calculateRelevanceScore(
    semanticSimilarity: number,
    recencyWeight: number,
    sourcePriority: number
  ): number {
    const sem = Math.max(0, Math.min(1, semanticSimilarity));
    const rec = Math.max(0, Math.min(1, recencyWeight));
    const src = Math.max(0, Math.min(1, sourcePriority));
    const score = sem * 0.6 + rec * 0.25 + src * 0.15;
    return Math.round(score * 10000) / 10000;
  }

  /**
   * Assemble 6-layer context block via sidecar HTTP endpoint,
   * falling back to local deterministic assembly if sidecar is unreachable.
   */
  public async assembleContext(
    input: RetrievalInput,
    budgetOverride?: Partial<LayerBudgetConfig>
  ): Promise<ContextForgeResult> {
    if (!this.isFeatureEnabled()) {
      throw new Error("Context Forge is disabled by configuration (503)");
    }

    try {
      const response = await fetch(`${this.sidecarBaseUrl}/forge/assemble`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          retrieval_input: input,
          budget_override: budgetOverride,
        }),
      });

      if (response.status === 503) {
        throw new Error("Context Forge is disabled by configuration (503)");
      }

      if (response.ok) {
        const data = (await response.json()) as { status: string; result: ContextForgeResult };
        return data.result;
      }
    } catch (err: any) {
      if (err.message && err.message.includes("503")) {
        throw err;
      }
      // Fall through to local fallback assembly
    }

    return this.localAssembleContext(input, budgetOverride);
  }

  /**
   * Local deterministic assembly fallback.
   */
  public localAssembleContext(
    input: RetrievalInput,
    budgetOverride?: Partial<LayerBudgetConfig>
  ): ContextForgeResult {
    const budgets: LayerBudgetConfig = {
      ...DEFAULT_LAYER_BUDGETS,
      ...(budgetOverride || {}),
    };

    const estimateTokens = (text: string): number => {
      if (!text) return 0;
      return Math.max(1, Math.floor(text.length / 4));
    };

    const truncateTokens = (text: string, maxTokens: number): string => {
      if (!text || maxTokens <= 0) return "";
      const maxChars = maxTokens * 4;
      if (text.length <= maxChars) return text;
      const sub = text.substring(0, maxChars);
      const lastSpace = sub.lastIndexOf(" ");
      return (lastSpace > 0 ? sub.substring(0, lastSpace) : sub).trim();
    };

    // Layer 1
    const idParts: string[] = [];
    if (input.identity?.life_goals) {
      idParts.push(`Goals: ${JSON.stringify(input.identity.life_goals)}`);
    }
    const l1Content = truncateTokens(
      idParts.join(" | ") || "Identity: Standard Baseline",
      budgets.identity_limit
    );
    const l1: AssembledLayer = {
      layer_num: 1,
      name: "User Identity",
      content: l1Content,
      token_count: estimateTokens(l1Content),
    };

    // Layer 2
    const dcs = input.temporal?.dcs ?? 5.0;
    const mode = input.temporal?.operating_mode ?? "NORMAL";
    const l2Content = truncateTokens(
      `Mode: ${mode} | DCS: ${dcs}`,
      budgets.temporal_limit
    );
    const l2: AssembledLayer = {
      layer_num: 2,
      name: "Temporal Context",
      content: l2Content,
      token_count: estimateTokens(l2Content),
    };

    // Layer 3
    const eventStrs = (input.events || []).map(
      (e) => `{✓:${e.task || e.name || "task"},dur:${e.dur || 30},q:${e.q || 5}}`
    );
    const l3Content = truncateTokens(
      eventStrs.length ? `Events: ${eventStrs.join(" ")}` : "",
      budgets.events_limit
    );
    const l3: AssembledLayer = {
      layer_num: 3,
      name: "PostgreSQL Events",
      content: l3Content,
      token_count: estimateTokens(l3Content),
    };

    // Layer 4
    const hebbianUpdates: Array<Record<string, any>> = [];
    const pathStrs: string[] = [];
    for (const p of input.neo4j_paths || []) {
      const w = Number(p.weight || p.edge_weight || 0);
      if (w > 0.3) {
        const pStr = p.path_str || `${p.from_node || "A"} → ${p.to_node || "B"} (w:${w.toFixed(2)})`;
        pathStrs.push(pStr);
        hebbianUpdates.push({ path: pStr, old_weight: w, new_weight: Math.min(1.0, w + 0.1) });
      }
    }
    const l4Content = truncateTokens(
      pathStrs.length ? `Pathways: ${pathStrs.join(" | ")}` : "",
      budgets.neo4j_limit
    );
    const l4: AssembledLayer = {
      layer_num: 4,
      name: "Neo4j Pathways",
      content: l4Content,
      token_count: estimateTokens(l4Content),
    };

    // Layer 5
    const snips = (input.semantic_snippets || []).map((s) => s.text || "");
    const l5Content = truncateTokens(
      snips.length ? `Semantic: ${snips.join(" ; ")}` : "",
      budgets.semantic_limit
    );
    const l5: AssembledLayer = {
      layer_num: 5,
      name: "pgvector / Semantic",
      content: l5Content,
      token_count: estimateTokens(l5Content),
    };

    // Layer 6
    const webSnips = (input.web_results || []).slice(0, 3).map((w) => w.snippet || w.title || "");
    const l6Content = truncateTokens(
      (input.intent_requires_web && webSnips.length) ? `Web: ${webSnips.join(" | ")}` : "",
      budgets.web_limit
    );
    const l6: AssembledLayer = {
      layer_num: 6,
      name: "Web Search Results",
      content: l6Content,
      token_count: estimateTokens(l6Content),
    };

    const layers = [l1, l2, l3, l4, l5, l6];
    let totalTokens = layers.reduce((acc, curr) => acc + curr.token_count, 0);
    let compressionApplied = false;

    if (totalTokens > budgets.total_limit) {
      compressionApplied = true;
      let excess = totalTokens - budgets.total_limit;
      if (l5.token_count > 0) {
        const reduction = Math.min(l5.token_count, excess);
        l5.content = truncateTokens(l5.content, l5.token_count - reduction);
        l5.token_count = estimateTokens(l5.content);
        excess -= reduction;
      }
      if (excess > 0 && l3.token_count > 0) {
        const reduction = Math.min(l3.token_count, excess);
        l3.content = truncateTokens(l3.content, l3.token_count - reduction);
        l3.token_count = estimateTokens(l3.content);
        excess -= reduction;
      }
      totalTokens = layers.reduce((acc, curr) => acc + curr.token_count, 0);
    }

    const activeText = layers
      .filter((l) => l.content.length > 0)
      .map((l) => l.content)
      .join("\n\n");

    const assembledPrompt = [
      "LOCUS_SHORTHAND: {✓: task_completed, dur: duration_minutes, q: quality_score_1_to_10}",
      "If data needed to answer a question is not in this context, say you don't have it yet. Do NOT invent data.",
      "--- BEGIN CONTEXT BLOCK ---",
      activeText,
      "--- END CONTEXT BLOCK ---",
    ].join("\n\n");

    return {
      assembled_prompt: assembledPrompt,
      layers,
      total_tokens: totalTokens,
      compression_applied: compressionApplied,
      hebbian_updates: hebbianUpdates,
      metadata: {
        total_layers: 6,
        headroom_budget: budgets.total_limit,
      },
    };
  }
}
