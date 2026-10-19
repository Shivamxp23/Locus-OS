/**
 * SPEC §1.11 / F-0011 / US-30: TypeScript Title Generation.
 * Auto-generates 3-7 word session titles from the first conversation turn.
 */
import { isEnabled } from "../config";

export const TITLE_SYSTEM_PROMPT =
  "Generate a short, descriptive title (3-7 words) for a conversation " +
  "that starts with the following exchange. Return ONLY the title text, " +
  "nothing else. No quotes, no punctuation at the end, no prefixes.";

/**
 * SPEC §1.11 line 2415:
 * Clean up artifacts from generated titles.
 */
export function cleanTitle(rawTitle: string | null | undefined): string {
  if (!rawTitle) return "";
  let title = String(rawTitle).trim();

  // Strip outer quotes
  const quotePattern = /^["'`«»“”„”]+|["'`«»“”„”]+$/g;
  title = title.replace(quotePattern, "").trim();

  // Strip "Title:" prefix
  if (title.toLowerCase().startsWith("title:")) {
    title = title.slice(6).trim();
  }

  // Strip outer quotes again if enclosed after prefix removal
  title = title.replace(quotePattern, "").trim();

  // Strip trailing punctuation
  title = title.replace(/[\.\!\?\:\;\,]+$/, "").trim();

  // Normalize internal whitespace
  title = title.replace(/\s+/g, " ");

  // Enforce 80 characters limit
  if (title.length > 80) {
    title = title.slice(0, 77) + "...";
  }

  return title;
}

/**
 * SPEC §1.11 line 2392:
 * Assemble system prompt and user conversation exchange snippet.
 */
export function formatTitlePrompt(
  userSnippet: string,
  assistantSnippet: string,
  timeout: number = 30
): {
  task: string;
  messages: Array<{ role: string; content: string }>;
  max_tokens: number;
  temperature: number;
  timeout: number;
} {
  const u = (userSnippet || "").slice(0, 500);
  const a = (assistantSnippet || "").slice(0, 500);

  return {
    task: "title_generation",
    messages: [
      { role: "system", content: TITLE_SYSTEM_PROMPT },
      { role: "user", content: `User: ${u}\n\nAssistant: ${a}` },
    ],
    max_tokens: 500,
    temperature: 0.3,
    timeout,
  };
}

/**
 * SPEC §1.11 line 2426:
 * Default timestamp-based fallback title.
 */
export function generateFallbackTitle(userMessage: string = ""): string {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  const tsStr = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;

  const cleaned = cleanTitle(userMessage);
  if (cleaned) {
    const words = cleaned.split(/\s+/);
    if (words.length <= 7 && cleaned.length <= 50) {
      return cleaned;
    }
    if (words.length > 7) {
      return words.slice(0, 6).join(" ") + "...";
    }
  }

  return `Session ${tsStr}`;
}

/**
 * TitleGenerator manager class.
 */
export class TitleGenerator {
  private static instance: TitleGenerator | null = null;

  public static getInstance(): TitleGenerator {
    if (!TitleGenerator.instance) {
      TitleGenerator.instance = new TitleGenerator();
    }
    return TitleGenerator.instance;
  }

  public isEnabled(): boolean {
    return (
      isEnabled("locus.title_generation.enabled") &&
      isEnabled("locus.sessions.auto_title.enabled")
    );
  }

  public cleanTitle(rawTitle: string): string {
    return cleanTitle(rawTitle);
  }

  public formatPrompt(userSnippet: string, assistantSnippet: string, timeout: number = 30) {
    return formatTitlePrompt(userSnippet, assistantSnippet, timeout);
  }

  /**
   * SPEC §1.11 line 2390:
   * Synchronous / awaitable title generation.
   */
  public async generateTitle(
    userMessage: string,
    assistantResponse: string,
    timeout: number = 30,
    llmCaller?: (payload: any) => Promise<string>
  ): Promise<string | null> {
    if (!this.isEnabled()) {
      return null;
    }

    if (!userMessage?.trim() && !assistantResponse?.trim()) {
      return generateFallbackTitle();
    }

    const payload = formatTitlePrompt(userMessage, assistantResponse, timeout);

    try {
      let rawOutput = "";
      if (llmCaller) {
        rawOutput = await llmCaller(payload);
      } else {
        rawOutput = generateFallbackTitle(userMessage);
      }

      const cleaned = cleanTitle(rawOutput);
      return cleaned || generateFallbackTitle(userMessage);
    } catch (err) {
      return generateFallbackTitle(userMessage);
    }
  }

  /**
   * SPEC §1.11 line 2422:
   * Asynchronous non-blocking title generation.
   */
  public generateTitleAsync(
    userMessage: string,
    assistantResponse: string,
    callback: (title: string) => void,
    timeout: number = 30,
    failureCallback?: (err: Error) => void,
    llmCaller?: (payload: any) => Promise<string>
  ): void {
    Promise.resolve().then(async () => {
      try {
        const title = await this.generateTitle(
          userMessage,
          assistantResponse,
          timeout,
          llmCaller
        );
        if (title) {
          callback(title);
        }
      } catch (err: any) {
        if (failureCallback) {
          failureCallback(err);
        }
      }
    });
  }
}
