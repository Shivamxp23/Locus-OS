/**
 * locus-extension/src/context-forge.ts - Context Forge 6-Layer Assembler
 *
 * Implements Spec §2.5 (Context Forge Stage 6).
 */

export interface ContextLayers {
  identity?: string;
  temporal?: string;
  events?: string;
  neo4jPaths?: string;
  semantic?: string;
  web?: string;
}

export interface AssembledContext {
  contextText: string;
  totalTokensEst: number;
  compressed: boolean;
  layersIncluded: string[];
}

export interface ContextAssembler {
  assemble(layers: ContextLayers): AssembledContext;
}

export class LocalContextForge implements ContextAssembler {
  public static readonly TOTAL_BUDGET = 800;
  private enabled: boolean;

  constructor(options: { enabled?: boolean } = {}) {
    this.enabled = options.enabled ?? true;
  }

  public isEnabled(): boolean {
    return this.enabled;
  }

  public estimateTokens(text: string): number {
    if (!text) return 0;
    return Math.max(1, Math.floor(text.trim().length / 4));
  }

  public assemble(layers: ContextLayers): AssembledContext {
    if (!this.enabled) {
      return {
        contextText: "",
        totalTokensEst: 0,
        compressed: false,
        layersIncluded: [],
      };
    }

    const blocks: string[] = [
      "STRICT DIRECTIVE: If data needed to answer a question is not in this context, say you don't have it yet. Do NOT invent data.",
      "[LOCUS_SHORTHAND: ✓=completed, dur=duration_min, q=quality_1_10, tws=task_weight_score, dcs=daily_capacity_score]",
    ];

    const included: string[] = [];

    if (layers.identity) {
      blocks.push(`[Layer 1 (Identity)]\n${layers.identity.slice(0, 320)}`);
      included.push("Identity");
    }
    if (layers.temporal) {
      blocks.push(`[Layer 2 (Temporal)]\n${layers.temporal.slice(0, 240)}`);
      included.push("Temporal");
    }
    if (layers.events) {
      blocks.push(`[Layer 3 (Events)]\n${layers.events.slice(0, 720)}`);
      included.push("Events");
    }
    if (layers.neo4jPaths) {
      blocks.push(`[Layer 4 (Neo4j)]\n${layers.neo4jPaths.slice(0, 600)}`);
      included.push("Neo4j");
    }
    if (layers.semantic) {
      blocks.push(`[Layer 5 (Semantic)]\n${layers.semantic.slice(0, 800)}`);
      included.push("Semantic");
    }
    if (layers.web) {
      blocks.push(`[Layer 6 (Web)]\n${layers.web.slice(0, 400)}`);
      included.push("Web");
    }

    const contextText = blocks.join("\n\n");
    const totalTokensEst = this.estimateTokens(contextText);

    return {
      contextText,
      totalTokensEst,
      compressed: totalTokensEst > LocalContextForge.TOTAL_BUDGET,
      layersIncluded: included,
    };
  }
}
