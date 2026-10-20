/**
 * Headroom CCR Token Compression Contract (SPEC §4.17: Token Compression (Headroom CCR)).
 * Maps to sidecar endpoints:
 *   POST /compression/headroom/compress
 *   GET /compression/headroom/retrieve/{cache_key}
 *   GET /compression/headroom/config
 */

export interface CompressConfig {
  protect_recent?: number; // default: 4
  min_tokens_to_compress?: number; // default: 250
  compress_user_messages?: boolean; // default: false
  target_ratio?: number | null; // target compression ratio
  frozen_message_count?: number; // KV cache anchor count
  enabled?: boolean;
  ttl_seconds?: number;
}

export interface CompressResult {
  messages: Array<Record<string, any>>;
  tokens_before: number;
  tokens_after: number;
  tokens_saved: number;
  ratio: number;
  transforms_applied: string[];
  cached_keys: string[];
}

export interface CompressionProvider {
  compress(
    messages: Array<Record<string, any>>,
    model?: string,
    config?: CompressConfig
  ): Promise<CompressResult>;
  retrieve(cacheKey: string): Promise<string | null>;
  isEnabled(): Promise<boolean>;
  getConfig(): Promise<Record<string, any>>;
}

export class HeadroomCCRClient implements CompressionProvider {
  private baseUrl: string;

  constructor(baseUrl: string = "http://127.0.0.1:8000") {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  async compress(
    messages: Array<Record<string, any>>,
    model?: string,
    config?: CompressConfig
  ): Promise<CompressResult> {
    const res = await fetch(`${this.baseUrl}/compression/headroom/compress`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages, model, config }),
    });

    if (res.status === 503) {
      throw new Error("Headroom CCR is disabled by configuration");
    }
    if (!res.ok) {
      throw new Error(`Headroom compression failed with status ${res.status}`);
    }

    const data = await res.json();
    return data.result as CompressResult;
  }

  async retrieve(cacheKey: string): Promise<string | null> {
    const res = await fetch(
      `${this.baseUrl}/compression/headroom/retrieve/${encodeURIComponent(cacheKey)}`,
      { method: "GET" }
    );

    if (res.status === 404) {
      return null;
    }
    if (res.status === 503) {
      throw new Error("Headroom CCR is disabled by configuration");
    }
    if (!res.ok) {
      throw new Error(`Headroom retrieval failed with status ${res.status}`);
    }

    const data = await res.json();
    return data.original ?? null;
  }

  async isEnabled(): Promise<boolean> {
    try {
      const cfg = await this.getConfig();
      return Boolean(cfg.enabled);
    } catch {
      return false;
    }
  }

  async getConfig(): Promise<Record<string, any>> {
    const res = await fetch(`${this.baseUrl}/compression/headroom/config`, {
      method: "GET",
    });
    if (!res.ok) {
      throw new Error(`Failed to fetch headroom config: status ${res.status}`);
    }
    return res.json();
  }
}
