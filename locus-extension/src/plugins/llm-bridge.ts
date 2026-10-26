/**
 * SPEC §9.9 lines 6143-6199:
 * Plugin LLM Sandboxing & Auxiliary Bridge (F-0034 / US-65).
 * TypeScript client for sandboxed secondary LLM execution, daily token quota enforcement,
 * and fail-fast 15s timeout containment.
 */

export interface PluginLLMMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

export interface PluginLLMTokenUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
}

export interface PluginLLMQuotaInfo {
  plugin_id: string;
  token_quota_daily: number;
  tokens_used_today: number;
  tokens_remaining: number;
  last_reset_date: string;
  quota_exceeded: boolean;
}

export interface PluginLLMGenerateRequest {
  plugin_id: string;
  messages: PluginLLMMessage[];
  max_tokens?: number;
  temperature?: number;
  timeout?: number;
}

export interface PluginLLMGenerateResponse {
  status: "ok" | "error";
  plugin_id: string;
  content?: string;
  quota?: PluginLLMQuotaInfo;
  error?: string;
  detail?: string;
}

export class PluginLLMBridgeClient {
  private baseUrl: string;

  constructor(baseUrl: string = "http://127.0.0.1:8420") {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  /**
   * SPEC §9.9 lines 6165-6187:
   * Call plugin auxiliary LLM with sandboxing and daily token quota enforcement.
   */
  async callPluginLLM(req: PluginLLMGenerateRequest): Promise<PluginLLMGenerateResponse> {
    const url = `${this.baseUrl}/plugins/llm/generate`;
    const controller = new AbortController();
    const timeoutMs = (req.timeout ?? 15.0) * 1000;
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const resp = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          plugin_id: req.plugin_id,
          messages: req.messages,
          max_tokens: req.max_tokens ?? 500,
          temperature: req.temperature ?? 0.2,
          timeout: req.timeout ?? 15.0,
        }),
        signal: controller.signal,
      });

      if (resp.status === 503) {
        const body = await resp.json().catch(() => ({}));
        throw new Error(
          `Plugin LLM disabled (status 503): ${body.detail || "Feature disabled"}`
        );
      }

      const data = await resp.json();
      return data as PluginLLMGenerateResponse;
    } catch (err: any) {
      if (err.name === "AbortError") {
        return {
          status: "error",
          plugin_id: req.plugin_id,
          error: "timeout",
          detail: `Plugin LLM call timed out after ${req.timeout ?? 15.0}s`,
        };
      }
      throw err;
    } finally {
      clearTimeout(timeoutId);
    }
  }

  /**
   * SPEC §9.9 lines 6162-6164:
   * Get quota and usage information for a plugin.
   */
  async getQuota(pluginId: string): Promise<PluginLLMQuotaInfo> {
    const url = `${this.baseUrl}/plugins/llm/quota?plugin_id=${encodeURIComponent(pluginId)}`;
    const resp = await fetch(url);
    if (resp.status === 503) {
      throw new Error("Plugin LLM disabled (status 503)");
    }
    const data = await resp.json();
    return data.quota as PluginLLMQuotaInfo;
  }

  /**
   * SPEC §9.9 line 6188:
   * Reset daily tokens used for a plugin.
   */
  async resetQuota(pluginId: string): Promise<PluginLLMQuotaInfo> {
    const url = `${this.baseUrl}/plugins/llm/reset`;
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ plugin_id: pluginId }),
    });
    if (resp.status === 503) {
      throw new Error("Plugin LLM disabled (status 503)");
    }
    const data = await resp.json();
    return data.quota as PluginLLMQuotaInfo;
  }

  /**
   * SPEC §9.9 lines 6189-6190:
   * Get aggregate usage metrics across all plugins.
   */
  async getAllUsage(): Promise<Record<string, any>> {
    const url = `${this.baseUrl}/plugins/llm/usage`;
    const resp = await fetch(url);
    if (resp.status === 503) {
      throw new Error("Plugin LLM disabled (status 503)");
    }
    const data = await resp.json();
    return data.plugins as Record<string, any>;
  }
}
