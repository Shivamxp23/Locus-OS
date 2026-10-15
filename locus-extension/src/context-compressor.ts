/**
 * Context Compression Engine (§4.16)
 *
 * Hermes-style threshold monitoring and conversation history compaction.
 */

export interface Message {
  role: string;
  content: string;
  [key: string]: unknown;
}

export interface ContextEngineOptions {
  name?: string;
  contextLength?: number;
  thresholdPercent?: number;
  protectFirstN?: number;
  protectLastN?: number;
}

export class ContextEngine {
  public name: string;
  public contextLength: number;
  public thresholdPercent: number;
  public protectFirstN: number;
  public protectLastN: number;
  public thresholdTokens: number;
  public lastPromptTokens: number = 0;
  public compressionCount: number = 0;

  constructor(options: ContextEngineOptions = {}) {
    this.name = options.name ?? "hermes_compressor";
    this.contextLength = options.contextLength ?? 128000;
    this.thresholdPercent = options.thresholdPercent ?? 0.75;
    this.protectFirstN = options.protectFirstN ?? 3;
    this.protectLastN = options.protectLastN ?? 6;
    this.thresholdTokens = Math.floor(this.contextLength * this.thresholdPercent);
  }

  public shouldCompress(promptTokens?: number): boolean {
    const tokens = promptTokens ?? this.lastPromptTokens;
    return tokens >= this.thresholdTokens;
  }

  public compress(
    messages: Message[],
    focusTopic?: string,
    summarizerFn?: (middle: Message[], focus?: string) => string
  ): Message[] {
    const headCount = this.protectFirstN + 1; // system + first N
    const tailCount = this.protectLastN;

    if (messages.length <= headCount + tailCount) {
      return [...messages];
    }

    const head = messages.slice(0, headCount);
    const tail = messages.slice(-tailCount);
    const middle = messages.slice(headCount, -tailCount);

    if (middle.length === 0) {
      return [...messages];
    }

    let summaryText = "";
    if (summarizerFn) {
      summaryText = summarizerFn(middle, focusTopic);
    } else {
      const snippets = middle
        .slice(0, 8)
        .map(m => `[${m.role}]: ${m.content.slice(0, 80)}`)
        .join("\n");
      summaryText = `Compressed history (${middle.length} messages):\n${snippets}`;
    }

    if (focusTopic) {
      summaryText += `\n[Focus Topic: ${focusTopic}]`;
    }

    const summaryMessage: Message = {
      role: "system",
      content: `[Previous context summary]: ${summaryText}`,
      compressed: true,
    };

    this.compressionCount++;
    return [...head, summaryMessage, ...tail];
  }
}
