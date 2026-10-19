/**
 * SPEC §2.1-2.3 / F-0092 / US-32: TypeScript Intent Classifier & Query Router (Stage 2).
 * Classifies queries into 8 canonical intents, applies anti-hallucination confidence gates,
 * and builds Routing Manifest objects for parallel retrieval execution.
 */
import { isEnabled } from "./config";

export type IntentCategory =
  | "FACTUAL_PERSONAL"
  | "BEHAVIORAL_PATTERN"
  | "KNOWLEDGE_RETRIEVAL"
  | "TASK_PLANNING"
  | "EMOTIONAL_STATE"
  | "EXTERNAL_KNOWLEDGE"
  | "SYNTHESIS"
  | "INFERENCE_REQUEST";

export type TemporalScope = "TODAY" | "WEEK" | "MONTH" | "ALLTIME";

export interface RoutingManifest {
  intent_type: IntentCategory;
  sources_required: string[];
  temporal_scope: TemporalScope;
  deep_reasoning: boolean;
  confidence: number;
  start_ts?: number | null;
  end_ts?: number | null;
}

export const ALL_RETRIEVAL_SOURCES = ["pg", "neo4j", "pgvector", "pageindex"];

export const DEFAULT_SOURCES_BY_INTENT: Record<IntentCategory, string[]> = {
  FACTUAL_PERSONAL: ["pg"],
  BEHAVIORAL_PATTERN: ["pg", "neo4j"],
  KNOWLEDGE_RETRIEVAL: ["pgvector", "pageindex"],
  TASK_PLANNING: ["pg", "neo4j"],
  EMOTIONAL_STATE: ["pg"],
  EXTERNAL_KNOWLEDGE: ["pgvector"],
  SYNTHESIS: ["pg", "neo4j", "pgvector", "pageindex"],
  INFERENCE_REQUEST: ["pg", "neo4j"],
};

export class IntentClassifier {
  private sidecarBaseUrl: string;

  constructor(sidecarBaseUrl: string = "http://127.0.0.1:8420") {
    this.sidecarBaseUrl = sidecarBaseUrl;
  }

  public isFeatureEnabled(): boolean {
    return isEnabled("locus.query_router.enabled") && isEnabled("locus.intent_classifier.enabled");
  }

  /**
   * SPEC §2.1-2.3 STEP 4: Confidence Gate (Anti-Hallucination)
   * IF confidence < 0.7: sources_required = ["pg", "neo4j", "pgvector", "pageindex"]
   */
  public applyConfidenceGate(manifest: RoutingManifest): RoutingManifest {
    if (manifest.confidence < 0.7) {
      return {
        ...manifest,
        sources_required: [...ALL_RETRIEVAL_SOURCES],
      };
    }
    return manifest;
  }

  /**
   * Classify user query via sidecar or local fallback.
   */
  public async classify(
    query: string,
    timezone: string = "Asia/Kolkata"
  ): Promise<RoutingManifest> {
    if (!this.isFeatureEnabled()) {
      return {
        intent_type: "KNOWLEDGE_RETRIEVAL",
        sources_required: [...ALL_RETRIEVAL_SOURCES],
        temporal_scope: "ALLTIME",
        deep_reasoning: false,
        confidence: 0.5,
      };
    }

    try {
      const response = await fetch(`${this.sidecarBaseUrl}/router/classify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, timezone }),
      });

      if (response.ok) {
        const data = (await response.json()) as { manifest: RoutingManifest };
        return this.applyConfidenceGate(data.manifest);
      }
    } catch {
      // Fallback on network failure
    }

    // Deterministic fallback
    return this.classifyLocal(query);
  }

  public classifyLocal(query: string): RoutingManifest {
    const q = (query || "").toLowerCase();
    let intent: IntentCategory = "KNOWLEDGE_RETRIEVAL";
    let scope: TemporalScope = "ALLTIME";
    let deep = false;
    let confidence = 0.85;

    if (/\b(plan|todo|schedule|task|agenda)\b/.test(q)) {
      intent = "TASK_PLANNING";
    } else if (/\b(habit|streak|routine|sleep|focus)\b/.test(q)) {
      intent = "BEHAVIORAL_PATTERN";
    } else if (/\b(feel|feeling|mood|stressed|happy)\b/.test(q)) {
      intent = "EMOTIONAL_STATE";
    } else if (/\b(my name|my email|my phone)\b/.test(q)) {
      intent = "FACTUAL_PERSONAL";
    } else if (/\b(synthesize|summarize|overview)\b/.test(q)) {
      intent = "SYNTHESIS";
      deep = true;
    } else if (/\b(why did|cause|relationship between)\b/.test(q)) {
      intent = "INFERENCE_REQUEST";
      deep = true;
    } else if (/\b(weather|stock|news)\b/.test(q)) {
      intent = "EXTERNAL_KNOWLEDGE";
    }

    if (/\b(today|this morning|tonight)\b/.test(q)) {
      scope = "TODAY";
    } else if (/\b(this week|past week)\b/.test(q)) {
      scope = "WEEK";
    } else if (/\b(this month|past month)\b/.test(q)) {
      scope = "MONTH";
    }

    const manifest: RoutingManifest = {
      intent_type: intent,
      sources_required: DEFAULT_SOURCES_BY_INTENT[intent] || ["pg", "pgvector"],
      temporal_scope: scope,
      deep_reasoning: deep,
      confidence,
    };

    return this.applyConfidenceGate(manifest);
  }
}
