/**
 * Token Compression (Headroom CCR - Cache-Compress-Retrieve) (§4.17)
 *
 * Content-routed token compression with cache prefix alignment and reversible CCR lookup.
 */

export interface CompressConfig {
  protect_recent?: number;
  min_tokens_to_compress?: number;
  compress_user_messages?: boolean;
  target_ratio?: number;
  frozen_message_count?: number;
  cache_ttl_seconds?: number;
}

export interface CompressResult {
  compressed_messages: Record<string, unknown>[];
  original_token_estimate: number;
  compressed_token_estimate: number;
  compression_ratio: number;
  cache_keys_created: string[];
}

export class CCRCache {
  private cache: Map<string, { text: string; expireAt: number }> = new Map();
  private defaultTtl: number;

  constructor(defaultTtl: number = 3600) {
    this.defaultTtl = defaultTtl;
  }

  public put(text: string, ttl?: number): string {
    const key = "ccr_" + Math.random().toString(36).substring(2, 10);
    const expireAt = Date.now() + (ttl || this.defaultTtl) * 1000;
    this.cache.set(key, { text, expireAt });
    return key;
  }

  public get(key: string): string | null {
    const entry = this.cache.get(key);
    if (!entry) return null;
    if (Date.now() > entry.expireAt) {
      this.cache.delete(key);
      return null;
    }
    return entry.text;
  }
}

export class HeadroomCompressor {
  private config: Required<CompressConfig>;
  private cache: CCRCache;

  constructor(config: CompressConfig = {}) {
    this.config = {
      protect_recent: config.protect_recent ?? 4,
      min_tokens_to_compress: config.min_tokens_to_compress ?? 250,
      compress_user_messages: config.compress_user_messages ?? false,
      target_ratio: config.target_ratio ?? 0.50,
      frozen_message_count: config.frozen_message_count ?? 1,
      cache_ttl_seconds: config.cache_ttl_seconds ?? 3600,
    };
    this.cache = new CCRCache(this.config.cache_ttl_seconds);
  }

  public compress(messages: Record<string, unknown>[]): CompressResult {
    const origTokens = messages.reduce(
      (acc, m) => acc + Math.max(1, Math.floor(String(m.content || "").length / 4)),
      0
    );

    const frozenCount = Math.min(this.config.frozen_message_count, messages.length);
    const frozen = messages.slice(0, frozenCount);
    const protectLimit = Math.max(frozenCount, messages.length - this.config.protect_recent);
    const middle = messages.slice(frozenCount, protectLimit);
    const recent = messages.slice(protectLimit);

    const processedMiddle: Record<string, unknown>[] = [];
    const cacheKeys: string[] = [];

    for (const msg of middle) {
      const content = String(msg.content || "");
      const tokens = Math.max(1, Math.floor(content.length / 4));

      if (msg.role === "user" && !this.config.compress_user_messages) {
        processedMiddle.push(msg);
        continue;
      }

      if (tokens < this.config.min_tokens_to_compress) {
        processedMiddle.push(msg);
        continue;
      }

      // Compact whitespace / redundant spacing
      const compacted = content.replace(/\n\s*\n+/g, "\n\n").trim();
      if (Math.floor(compacted.length / 4) < tokens * 0.8) {
        const cKey = this.cache.put(content);
        cacheKeys.push(cKey);
        processedMiddle.push({
          ...msg,
          content: `${compacted}\n[CCR_RETRIEVAL_KEY: ${cKey}]`,
          headroom_compressed: true,
        });
      } else {
        processedMiddle.push(msg);
      }
    }

    const finalMessages = [...frozen, ...processedMiddle, ...recent];
    const compTokens = finalMessages.reduce(
      (acc, m) => acc + Math.max(1, Math.floor(String(m.content || "").length / 4)),
      0
    );
    const ratio = Math.round((compTokens / Math.max(1, origTokens)) * 10000) / 10000;

    return {
      compressed_messages: finalMessages,
      original_token_estimate: origTokens,
      compressed_token_estimate: compTokens,
      compression_ratio: ratio,
      cache_keys_created: cacheKeys,
    };
  }

  public retrieve(cacheKey: string): string | null {
    return this.cache.get(cacheKey);
  }
}
