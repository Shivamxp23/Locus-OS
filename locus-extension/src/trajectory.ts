/**
 * SPEC §19.2 line 10 / F-0049: Trajectory Recording TypeScript Interface.
 * Defines session turn and trajectory data models, sensitive token redaction,
 * and client helper for sending turn records to the Locus sidecar.
 */

export interface TurnRecord {
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  timestamp: string;
  tokens?: {
    prompt?: number;
    completion?: number;
    total?: number;
  };
  toolCalls?: Array<{
    name: string;
    args?: Record<string, unknown>;
    result?: unknown;
    error?: string;
  }>;
  metadata?: Record<string, unknown>;
}

export interface TrajectorySession {
  sessionId: string;
  model: string;
  platform: string;
  startTime: string;
  endTime?: string;
  turns: TurnRecord[];
  metadata?: Record<string, unknown>;
}

const REDACTION_REGEXES = [
  /sk-[A-Za-z0-9_-]{20,}/g,
  /ghp_[A-Za-z0-9]{20,}/g,
  /glpat-[A-Za-z0-9_-]{20,}/g,
  /Bearer\s+[A-Za-z0-9._~+/-]+=*/gi,
  /COUCHDB_PASSWORD=[^\s\n]+/gi,
  /TELEGRAM_BOT_TOKEN=[^\s\n]+/gi,
];

/**
 * SPEC §19.2: Redact sensitive tokens and credentials from turn contents.
 */
export function redactSensitiveData(text: string): string {
  if (!text) return text;
  let result = text;
  for (const regex of REDACTION_REGEXES) {
    result = result.replace(regex, "[REDACTED]");
  }
  return result;
}

/**
 * Format and prepare a turn record for trajectory persistence.
 */
export function formatTurn(
  role: TurnRecord["role"],
  content: string,
  toolCalls?: TurnRecord["toolCalls"],
  tokens?: TurnRecord["tokens"],
  metadata?: Record<string, unknown>
): TurnRecord {
  return {
    role,
    content: redactSensitiveData(content),
    timestamp: new Date().toISOString(),
    tokens: tokens || {},
    toolCalls: toolCalls?.map((tc) => ({
      ...tc,
      args: tc.args ? JSON.parse(redactSensitiveData(JSON.stringify(tc.args))) : undefined,
    })),
    metadata: metadata || {},
  };
}
