/**
 * SPEC §29.2 lines 7472-7500:
 * Auxiliary LLM Client TypeScript Contract (F-0124 / US-103).
 * Source: Hermes auxiliary_client.py
 *
 * Dedicated LLM client for background tasks (summaries, indexing, embeddings, triage).
 * Never contests main model's prompt cache.
 * Uses cheaper model (e.g., DeepSeek V4 Flash for background tasks).
 */

export interface AuxiliaryGenerationOptions {
  prompt: string;
  system_prompt?: string;
  model?: string;
  temperature?: number;
  max_tokens?: number;
}

export interface AuxiliaryGenerationResponse {
  content: string;
  model_used: string;
  is_auxiliary: boolean;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cost_usd: number;
  duration_ms: number;
  status_code: number;
  error?: string;
  disabled?: string;
}

export interface AuxiliaryModelInfo {
  model: string;
  has_api_key: boolean;
  base_url: string;
  temperature: number;
  max_tokens: number;
  timeout_seconds: number;
  status_code: number;
  error?: string;
  disabled?: string;
}

export interface AuxiliaryStatusResult {
  auxiliary_enabled: boolean;
  active_model: string;
  has_api_key: boolean;
  fallback_model: string;
  provider_enabled: boolean;
  provider_name: string;
  status_code: number;
  error?: string;
  disabled?: string;
}

export class AuxiliaryLLMClient {
  private baseUrl: string;

  constructor(baseUrl: string = "http://127.0.0.1:8000") {
    this.baseUrl = baseUrl.replace(/\/+$/, "");
  }

  async generate(options: AuxiliaryGenerationOptions): Promise<AuxiliaryGenerationResponse> {
    const res = await fetch(`${this.baseUrl}/auxiliary/llm/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(options),
    });
    return (await res.json()) as AuxiliaryGenerationResponse;
  }

  async getModelInfo(): Promise<AuxiliaryModelInfo> {
    const res = await fetch(`${this.baseUrl}/auxiliary/llm/model`, {
      method: "GET",
      headers: { Accept: "application/json" },
    });
    return (await res.json()) as AuxiliaryModelInfo;
  }

  async getStatus(): Promise<AuxiliaryStatusResult> {
    const res = await fetch(`${this.baseUrl}/auxiliary/llm/status`, {
      method: "GET",
      headers: { Accept: "application/json" },
    });
    return (await res.json()) as AuxiliaryStatusResult;
  }
}
