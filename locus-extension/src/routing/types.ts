/**
 * SPEC §2.7-2.8 / F-0096 / US-37: Intelligent Model Routing Type Definitions.
 * Port of OpenHuman routing architecture: classification categories,
 * latency/cost hints, routing decision records, and health checks.
 */

export type TaskCategory = "lightweight" | "medium" | "heavy";
export type TargetBackend = "local" | "remote";
export type LatencyBudget = "low" | "medium" | "high";
export type CostSensitivity = "low" | "medium" | "high";

export interface RoutingHints {
  latencyBudget?: LatencyBudget;
  costSensitivity?: CostSensitivity;
  privacyRequired?: boolean;
}

export interface RoutingDecision {
  category: TaskCategory;
  primary: TargetBackend;
  fallback: TargetBackend | null;
  supportsStreaming: boolean;
  resolvedModel: string;
  reason: string;
}

export interface HealthStatus {
  healthy: boolean;
  lastCheck: number;
  endpoint: string;
  providerType: "ollama" | "openai-compat";
}

export interface RoutingRecord {
  category: TaskCategory;
  target: TargetBackend;
  resolvedModel: string;
  healthStatus: boolean;
  usedFallback: boolean;
  latencyMs: number;
  tokensIn?: number;
  tokensOut?: number;
  estimatedCost?: number;
}

export interface ChatMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

export interface ChatRequest {
  model: string;
  messages: ChatMessage[];
  hints?: RoutingHints;
  tools?: Array<Record<string, unknown>>;
  stream?: boolean;
}

export interface ChatResponse {
  text: string;
  model: string;
  backend: TargetBackend;
  usage?: {
    promptTokens?: number;
    completionTokens?: number;
    totalTokens?: number;
  };
}

export interface RoutingConfig {
  enabled: boolean;
  privacyMode: boolean;
  localBaseUrl: string;
  localProvider: "ollama" | "openai-compat";
  healthCacheTtlMs: number;
  minResponseBytes: number;
}

export const DEFAULT_ROUTING_CONFIG: RoutingConfig = {
  enabled: true,
  privacyMode: false,
  localBaseUrl: "http://127.0.0.1:11434",
  localProvider: "ollama",
  healthCacheTtlMs: 30000,
  minResponseBytes: 10,
};
