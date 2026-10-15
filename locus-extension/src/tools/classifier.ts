/**
 * locus-extension/src/tools/classifier.ts - Tool Result Classifier TypeScript client.
 *
 * Implements Spec §3.9
 */

export enum ToolResultOutcome {
  SUCCESS = "success",
  RETRIABLE = "retriable",
  FATAL = "fatal",
  TIMEOUT = "timeout",
}

export class ToolClassifierClient {
  public classifyOutcome(error?: Error | string): ToolResultOutcome {
    if (!error) return ToolResultOutcome.SUCCESS;
    const msg = (typeof error === "string" ? error : error.message).toLowerCase();
    if (msg.includes("timeout") || msg.includes("timed out")) return ToolResultOutcome.TIMEOUT;
    if (msg.includes("rate limit") || msg.includes("429") || msg.includes("503")) return ToolResultOutcome.RETRIABLE;
    return ToolResultOutcome.FATAL;
  }
}
