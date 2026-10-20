/**
 * Session Management & Telegram Bridge Contract (SPEC §5.1-5.8: Session Management & Telegram Bridge).
 * Maps to canonical locus-extension/src/session-bridge.ts and sidecar endpoints:
 *   GET /sessions/config
 *   POST /sessions/create
 *   GET /sessions/{session_id}
 *   POST /sessions/{session_id}/fork
 *   POST /sessions/{session_id}/resume
 *   POST /sessions/{session_id}/export
 *   POST /sessions/telegram/bridge
 */

export type EntryType =
  | "message"
  | "tool_call"
  | "tool_result"
  | "compaction_summary"
  | "branch_summary"
  | "metadata"
  | "system_event"
  | "checkpoint"
  | "marker";

export interface SessionEntry {
  id: string;
  parent_id?: string | null;
  type: EntryType;
  role?: "user" | "assistant" | "system" | "tool" | null;
  content?: string | null;
  timestamp: number;
  metadata?: Record<string, any>;
}

export interface SessionInfo {
  session_id: string;
  parent_session_id?: string | null;
  fork_point?: string | null;
  entries_count: number;
  storage_path?: string;
}

export interface ForkSessionRequest {
  fork_point: string;
  summary?: string;
}

export interface ResumeSessionResult {
  session_id: string;
  messages_count: number;
  compactions_count: number;
  context: Array<{
    role: string;
    content: string;
    entry_id: string;
    type?: string;
  }>;
}

export interface TelegramBridgeRequest {
  telegram_chat_id: string | number;
  user_message: string;
}

export interface TelegramBridgeResponse {
  status: string;
  chat_id: string;
  session_id: string;
  response: string;
}

export interface ExportSessionResult {
  status: string;
  session_id: string;
  format: "markdown" | "json" | "jsonl";
  data: string;
}

export class SessionBridgeClient {
  private baseUrl: string;

  constructor(baseUrl: string = "http://127.0.0.1:8000") {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  async getConfig(): Promise<Record<string, any>> {
    const res = await fetch(`${this.baseUrl}/sessions/config`);
    if (!res.ok) {
      throw new Error(`getConfig failed with status ${res.status}`);
    }
    return (await res.json()) as Record<string, any>;
  }

  async createSession(sessionId?: string, parentId?: string): Promise<SessionInfo> {
    const res = await fetch(`${this.baseUrl}/sessions/create`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, parent_id: parentId }),
    });
    if (!res.ok) {
      throw new Error(`createSession failed with status ${res.status}`);
    }
    return (await res.json()) as SessionInfo;
  }

  async getSession(sessionId: string): Promise<SessionInfo & { entries: SessionEntry[] }> {
    const res = await fetch(`${this.baseUrl}/sessions/${encodeURIComponent(sessionId)}`);
    if (!res.ok) {
      throw new Error(`getSession failed with status ${res.status}`);
    }
    return (await res.json()) as SessionInfo & { entries: SessionEntry[] };
  }

  async forkSession(
    parentSessionId: string,
    forkPoint: string,
    summary?: string
  ): Promise<SessionInfo> {
    const res = await fetch(`${this.baseUrl}/sessions/${encodeURIComponent(parentSessionId)}/fork`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ fork_point: forkPoint, summary }),
    });
    if (!res.ok) {
      throw new Error(`forkSession failed with status ${res.status}`);
    }
    return (await res.json()) as SessionInfo;
  }

  async resumeSession(sessionId: string): Promise<ResumeSessionResult> {
    const res = await fetch(`${this.baseUrl}/sessions/${encodeURIComponent(sessionId)}/resume`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
    if (!res.ok) {
      throw new Error(`resumeSession failed with status ${res.status}`);
    }
    return (await res.json()) as ResumeSessionResult;
  }

  async exportSession(
    sessionId: string,
    format: "markdown" | "json" | "jsonl" = "markdown"
  ): Promise<ExportSessionResult> {
    const res = await fetch(`${this.baseUrl}/sessions/${encodeURIComponent(sessionId)}/export`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ format }),
    });
    if (!res.ok) {
      throw new Error(`exportSession failed with status ${res.status}`);
    }
    return (await res.json()) as ExportSessionResult;
  }

  async bridgeTelegramMessage(
    chatId: string | number,
    message: string
  ): Promise<TelegramBridgeResponse> {
    const res = await fetch(`${this.baseUrl}/sessions/telegram/bridge`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ telegram_chat_id: chatId, user_message: message }),
    });
    if (!res.ok) {
      throw new Error(`bridgeTelegramMessage failed with status ${res.status}`);
    }
    return (await res.json()) as TelegramBridgeResponse;
  }
}
