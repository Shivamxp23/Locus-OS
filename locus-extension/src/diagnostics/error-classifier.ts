/**
 * SPEC §29.1 lines 7435-7471:
 * Error Classifier TypeScript Client Contract (F-0065 / US-102).
 * Source: Hermes error_classifier.py
 *
 * Interfaces and client for classifying runtime errors into 7 canonical categories:
 * rate_limit, auth_failure, context_overflow, server_error, timeout, content_filter, unknown.
 */

export type ErrorCategoryType =
  | "rate_limit"
  | "auth_failure"
  | "context_overflow"
  | "server_error"
  | "timeout"
  | "content_filter"
  | "unknown";

export type RecoveryActionType =
  | "auto_retry"
  | "surface_user"
  | "trigger_compaction"
  | "retry_then_fallback"
  | "retry_shorter_context"
  | "rephrase_and_retry"
  | "log_and_continue";

export interface ErrorClassificationResult {
  category: ErrorCategoryType;
  action: RecoveryActionType;
  retryable: boolean;
  max_retries: number;
  backoff_seconds: number;
  fallback_model_recommended: boolean;
  explanation: string;
  raw_status?: number | null;
  raw_message?: string;
  status_code: number;
  error?: string;
  disabled?: string;
}

export interface ErrorRecoveryStrategy {
  action: string;
  max_retries: number;
  backoff_seconds: number;
}

export interface ErrorTaxonomyResult {
  categories: ErrorCategoryType[];
  actions: RecoveryActionType[];
  strategies: Record<string, ErrorRecoveryStrategy>;
  status_code: number;
  error?: string;
  disabled?: string;
}

export interface ErrorClassifierStatusResult {
  subsystem_enabled: boolean;
  classifier_name: string;
  taxonomy_version: string;
  provider_enabled: boolean;
  provider_name: string;
  status_code: number;
  error?: string;
  disabled?: string;
}

export class ErrorClassifierClient {
  private baseUrl: string;

  constructor(baseUrl: string = "http://127.0.0.1:8000") {
    this.baseUrl = baseUrl.replace(/\/+$/, "");
  }

  async classifyError(errorPayload: unknown): Promise<ErrorClassificationResult> {
    const res = await fetch(`${this.baseUrl}/diagnostics/error/classify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ error: errorPayload }),
    });
    return (await res.json()) as ErrorClassificationResult;
  }

  async getTaxonomy(): Promise<ErrorTaxonomyResult> {
    const res = await fetch(`${this.baseUrl}/diagnostics/error/taxonomy`, {
      method: "GET",
      headers: { Accept: "application/json" },
    });
    return (await res.json()) as ErrorTaxonomyResult;
  }

  async getStatus(): Promise<ErrorClassifierStatusResult> {
    const res = await fetch(`${this.baseUrl}/diagnostics/error/status`, {
      method: "GET",
      headers: { Accept: "application/json" },
    });
    return (await res.json()) as ErrorClassifierStatusResult;
  }
}
