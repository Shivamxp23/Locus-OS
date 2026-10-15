/**
 * Session Management & Branching (§5.1-§5.4)
 *
 * Tree-structured conversation session tracking with branching and export.
 */

export interface SessionMetadata {
  session_id: string;
  title: string;
  parent_session_id?: string;
  fork_point_entry_id?: string;
  created_at: string;
}

export interface SessionEntry {
  id: string;
  entry_type: "message" | "tool_call" | "tool_result" | "compaction_summary" | "branch_summary";
  payload: Record<string, unknown>;
  created_at: string;
}

export class Session {
  public metadata: SessionMetadata;
  public entries: SessionEntry[] = [];

  constructor(metadata: SessionMetadata) {
    this.metadata = metadata;
  }

  public append(entryType: SessionEntry["entry_type"], payload: Record<string, unknown>): SessionEntry {
    const entry: SessionEntry = {
      id: "ent_" + Math.random().toString(36).substring(2, 8),
      entry_type: entryType,
      payload,
      created_at: new Date().toISOString(),
    };
    this.entries.push(entry);
    return entry;
  }

  public replayMessages(): Array<Record<string, unknown>> {
    return this.entries
      .filter(e => e.entry_type === "message")
      .map(e => e.payload);
  }
}

export class SessionManager {
  private sessions: Map<string, Session> = new Map();

  public createSession(title: string = "New Session"): Session {
    const sid = "sess_" + Math.random().toString(36).substring(2, 8);
    const meta: SessionMetadata = {
      session_id: sid,
      title,
      created_at: new Date().toISOString(),
    };
    const sess = new Session(meta);
    this.sessions.set(sid, sess);
    return sess;
  }

  public forkSession(parentSessionId: string, forkPointId?: string): Session {
    const parent = this.sessions.get(parentSessionId);
    if (!parent) {
      throw new Error(`Parent session ${parentSessionId} not found`);
    }
    const childId = "sess_" + Math.random().toString(36).substring(2, 8);
    const meta: SessionMetadata = {
      session_id: childId,
      title: `Branch of ${parent.metadata.title}`,
      parent_session_id: parentSessionId,
      fork_point_entry_id: forkPointId,
      created_at: new Date().toISOString(),
    };
    const child = new Session(meta);
    for (const e of parent.entries) {
      child.entries.push(e);
      if (forkPointId && e.id === forkPointId) break;
    }
    this.sessions.set(childId, child);
    return child;
  }
}
