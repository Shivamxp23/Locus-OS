/**
 * Context Window Management (§1.6)
 *
 * Compaction adapter and token estimation for session history.
 */

import { HeadroomCompressor } from "./providers/memory/headroom-ccr.js";

export interface CompactionOptions {
  protect_first_n?: number;
  protect_last_n?: number;
  threshold_tokens?: number;
}

export function estimateContextTokens(messages: Array<{ content?: string }>): number {
  return messages.reduce((acc, m) => acc + Math.max(1, Math.floor(String(m.content || "").length / 4)), 0);
}

export function shouldCompact(promptTokens: number, thresholdTokens: number): boolean {
  return promptTokens >= thresholdTokens;
}

export class HeadroomCompactionAdapter {
  private compressor: HeadroomCompressor;

  constructor() {
    this.compressor = new HeadroomCompressor();
  }

  public estimateTokens(messages: Array<{ content?: string }>): number {
    return estimateContextTokens(messages);
  }

  public shouldCompact(promptTokens: number, threshold: number = 64000): boolean {
    return shouldCompact(promptTokens, threshold);
  }

  public compact(messages: Record<string, unknown>[], options: CompactionOptions = {}) {
    return this.compressor.compress(messages);
  }
}
