/**
 * locus-extension/src/intent-classifier.ts - Query Router Client
 *
 * Implements Spec §2.1-2.3 (Query Router / Intent Classifier Stage 2).
 */

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
  start_ts: number;
  end_ts: number;
  deep_reasoning: boolean;
  confidence: number;
  metadata?: Record<string, unknown>;
}

export interface IntentClassifierProvider {
  classify(message: string): Promise<RoutingManifest>;
}

export class RemoteIntentClassifier implements IntentClassifierProvider {
  private endpoint: string;
  private enabled: boolean;

  constructor(options: { endpoint?: string; enabled?: boolean } = {}) {
    this.endpoint = options.endpoint ?? "http://127.0.0.1:8420/router/classify";
    this.enabled = options.enabled ?? true;
  }

  public isEnabled(): boolean {
    return this.enabled;
  }

  public async classify(message: string): Promise<RoutingManifest> {
    if (!this.enabled) {
      return {
        intent_type: "KNOWLEDGE_RETRIEVAL",
        sources_required: ["pg", "neo4j", "pgvector", "pageindex"],
        temporal_scope: "ALLTIME",
        start_ts: 0,
        end_ts: Date.now() / 1000,
        deep_reasoning: false,
        confidence: 0.5,
        metadata: { disabled: true },
      };
    }

    try {
      const res = await fetch(this.endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
      });
      if (!res.ok) {
        throw new Error(`Intent classifier HTTP ${res.status}`);
      }
      return (await res.json()) as RoutingManifest;
    } catch {
      // Offline fallback: Query all sources
      return {
        intent_type: "KNOWLEDGE_RETRIEVAL",
        sources_required: ["pg", "neo4j", "pgvector", "pageindex"],
        temporal_scope: "ALLTIME",
        start_ts: 0,
        end_ts: Date.now() / 1000,
        deep_reasoning: false,
        confidence: 0.5,
        metadata: { fallback: true },
      };
    }
  }
}
