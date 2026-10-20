/**
 * SPEC §4.16: Context Compression (F-0110 / US-55).
 * TypeScript contracts for Hermes ContextEngine ABC and CompactionProvider
 * adapting Pi compaction hooks and session management.
 */

export interface ContextMessage {
  role: string;
  content: string;
  metadata?: Record<string, any>;
}

export interface CompactionConfig {
  enabled: boolean;
  thresholdPercent: number; // 0.75
  protectFirstN: number; // 3
  protectLastN: number; // 6
  defaultContextLength: number;
}

export interface CompactionResult {
  compressedMessages: ContextMessage[];
  newSessionId: string;
  oldSessionId: string;
  wasCompressed: boolean;
  summary?: string;
  intermediateCount: number;
}

export abstract class ContextEngine {
  name: string;
  contextLength: number;
  thresholdPercent: number;
  protectFirstN: number;
  protectLastN: number;
  thresholdTokens: number;
  lastPromptTokens: number = 0;
  compressionCount: number = 0;

  constructor(
    name: string = "compressor",
    contextLength: number = 128000,
    thresholdPercent: number = 0.75,
    protectFirstN: number = 3,
    protectLastN: number = 6
  ) {
    this.name = name;
    this.contextLength = contextLength;
    this.thresholdPercent = thresholdPercent;
    this.protectFirstN = protectFirstN;
    this.protectLastN = protectLastN;
    this.thresholdTokens = Math.floor(contextLength * thresholdPercent);
  }

  abstract updateFromResponse(usage: Record<string, any>): void;
  abstract shouldCompress(promptTokens: number): boolean;
  abstract compress(
    messages: ContextMessage[],
    currentTokens: number,
    focusTopic?: string
  ): Promise<ContextMessage[]> | ContextMessage[];
  abstract onSessionStart(sessionId: string): void;
  abstract onSessionEnd(sessionId: string, messages: ContextMessage[]): void;
  abstract onSessionReset(): void;

  updateModel(model: string, contextLength: number, thresholdPercent?: number): void {
    this.contextLength = contextLength;
    if (thresholdPercent !== undefined) {
      this.thresholdPercent = thresholdPercent;
    }
    this.thresholdTokens = Math.floor(this.contextLength * this.thresholdPercent);
  }
}
