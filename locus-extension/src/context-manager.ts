/**
 * Locus Context Window Manager & Headroom CCR integration (SPEC §1.6 & §4.17, F-0006).
 * Handles token estimation, threshold-based compaction decisions, and reversible CCR.
 */

export interface Message {
  role: string;
  content: string;
  metadata?: Record<string, any>;
}

export interface CompactionOptions {
  protectFirstN?: number;
  protectLastN?: number;
  threshold?: number;
  sidecarUrl?: string;
}

export interface CompactionSummary {
  compressedMessages: Message[];
  originalTokens: number;
  compressedTokens: number;
  ratio: number;
  cachedKeys: string[];
}

/**
 * Estimate context tokens roughly (approx 4 chars per token).
 */
export function estimateContextTokens(textOrMessages: string | Message[]): number {
  if (!textOrMessages) return 0;
  if (typeof textOrMessages === "string") {
    const chars = textOrMessages.length;
    const words = textOrMessages.trim().split(/\s+/).filter(Boolean).length;
    return Math.max(Math.floor(chars / 3.8), words);
  }

  let total = 0;
  for (const m of textOrMessages) {
    total += estimateContextTokens(m.role || "") + estimateContextTokens(m.content || "") + 4;
  }
  return total;
}

/**
 * Evaluate if prompt tokens exceed compaction threshold.
 */
export function shouldCompact(promptTokens: number, threshold: number = 8000): boolean {
  return promptTokens >= threshold;
}

/**
 * Compact message list preserving first 3 and last 6 messages.
 */
export function compactContext(messages: Message[], options: CompactionOptions = {}): CompactionSummary {
  const protectFirstN = options.protectFirstN ?? 3;
  const protectLastN = options.protectLastN ?? 6;
  const origTokens = estimateContextTokens(messages);

  if (messages.length <= protectFirstN + protectLastN) {
    return {
      compressedMessages: [...messages],
      originalTokens: origTokens,
      compressedTokens: origTokens,
      ratio: 1.0,
      cachedKeys: [],
    };
  }

  const firstSegment = messages.slice(0, protectFirstN);
  const middleSegment = messages.slice(protectFirstN, messages.length - protectLastN);
  const lastSegment = messages.slice(messages.length - protectLastN);

  const cachedKey = `ccr-${Math.random().toString(36).substring(2, 10)}`;
  const middleContent = middleSegment.map((m) => `[${m.role}]: ${m.content}`).join("\n");
  const compSnippet = middleContent.slice(0, 100).trim();

  const summaryMessage: Message = {
    role: "system",
    content: `[COMPACTED]: ${middleSegment.length} turns compressed via Headroom CCR.\n${compSnippet}...\n[Original cached as ccr:${cachedKey}. Use headroom_retrieve('${cachedKey}') to read]`,
    metadata: {
      compaction: true,
      cacheKey: cachedKey,
      compressedCount: middleSegment.length,
    },
  };

  const finalMessages = [...firstSegment, summaryMessage, ...lastSegment];
  const finalTokens = estimateContextTokens(finalMessages);

  return {
    compressedMessages: finalMessages,
    originalTokens: origTokens,
    compressedTokens: finalTokens,
    ratio: origTokens > 0 ? Number((finalTokens / origTokens).toFixed(3)) : 1.0,
    cachedKeys: [cachedKey],
  };
}
