/**
 * Locus Post-Turn Background Reviewer (SPEC §1.7 & §10.1, F-0007).
 * Implements daemonized post-turn review with strict tool whitelisting,
 * skill update preference hierarchy, and never-fatal error containment.
 */

export const ALLOWED_REVIEW_TOOLS: string[] = [
  "memory",
  "skill_manage",
  "locus_memory",
  "locus_vault",
];

export enum SkillUpdatePreference {
  UPDATE_CURRENTLY_LOADED = "update_currently_loaded",
  UPDATE_EXISTING_UMBRELLA = "update_existing_umbrella",
  ADD_SUPPORT_FILE = "add_support_file",
  CREATE_NEW_UMBRELLA = "create_new_umbrella",
}

export interface PostTurnReviewRequest {
  messages: Array<{ role: string; content: string }>;
  sessionId?: string;
  sync?: boolean;
  sidecarUrl?: string;
}

export interface PostTurnReviewResult {
  reviewId: string;
  sessionId: string;
  status: "dispatched" | "completed" | "disabled" | "error";
  memoryInsights: any[];
  skillUpdates: any[];
  deniedToolsAttempted: string[];
  executionMode: string;
  durationMs: number;
}

/**
 * Check if a tool is permitted during post-turn review per SPEC §1.7 line 2861.
 */
export function isToolAllowedForReview(toolName: string): boolean {
  if (!toolName || typeof toolName !== "string") return false;
  return ALLOWED_REVIEW_TOOLS.includes(toolName.trim());
}

/**
 * Filter an array of tool names, stripping any tool not in the review whitelist.
 */
export function filterToolsForReview(tools: string[]): string[] {
  if (!Array.isArray(tools)) return [];
  return tools.filter((t) => isToolAllowedForReview(t));
}

/**
 * Build review prompt combining memory extraction and skill preference hierarchy.
 */
export function buildReviewPrompt(messages: Array<{ role: string; content: string }>): string {
  const lines: string[] = [
    "=== POST-TURN BACKGROUND REVIEW PROMPT ===",
    "MEMORY REVIEW: Has the user revealed preferences, personal details, constraints, or domain rules?",
    "SKILL REVIEW: Should any skill be saved, updated, or patched?",
    "Preference hierarchy:",
    "1. UPDATE A CURRENTLY-LOADED SKILL",
    "2. UPDATE AN EXISTING UMBRELLA",
    "3. ADD A SUPPORT FILE under an existing umbrella",
    "4. CREATE A NEW CLASS-LEVEL UMBRELLA SKILL",
    `ALLOWED TOOLS: ${ALLOWED_REVIEW_TOOLS.join(", ")}`,
    `SNAPSHOT: ${messages.length} messages`,
  ];
  return lines.join("\n");
}

/**
 * Dispatch post-turn background review asynchronously.
 * Guarantees "never fatal" execution: errors are contained and never throw to the caller.
 */
export async function spawnBackgroundReview(
  request: PostTurnReviewRequest
): Promise<PostTurnReviewResult> {
  const fallbackResult: PostTurnReviewResult = {
    reviewId: `rev-${Math.random().toString(16).slice(2, 10)}`,
    sessionId: request.sessionId || `sess-${Math.random().toString(16).slice(2, 8)}`,
    status: "dispatched",
    memoryInsights: [],
    skillUpdates: [],
    deniedToolsAttempted: [],
    executionMode: request.sync ? "sync" : "background_thread",
    durationMs: 0,
  };

  const sidecarUrl = request.sidecarUrl || "http://127.0.0.1:8420";

  try {
    const res = await fetch(`${sidecarUrl}/review/post-turn`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        messages: request.messages,
        session_id: request.sessionId,
        sync: request.sync ?? false,
      }),
    });

    if (res.status === 503) {
      return {
        ...fallbackResult,
        status: "disabled",
      };
    }

    if (!res.ok) {
      return {
        ...fallbackResult,
        status: "error",
      };
    }

    const data = await res.json();
    return {
      reviewId: data.result?.review_id || fallbackResult.reviewId,
      sessionId: data.result?.session_id || fallbackResult.sessionId,
      status: data.result?.status || "completed",
      memoryInsights: data.result?.memory_insights || [],
      skillUpdates: data.result?.skill_updates || [],
      deniedToolsAttempted: data.result?.denied_tools_attempted || [],
      executionMode: data.result?.execution_mode || "background_thread",
      durationMs: data.result?.duration_ms || 0,
    };
  } catch (err) {
    // SPEC §1.7: Never fatal principle
    return {
      ...fallbackResult,
      status: "error",
    };
  }
}

/**
 * Register post-turn review hook with Pi extension system.
 */
export function registerPostTurnReviewHook(pi: any): void {
  if (!pi || typeof pi.on !== "function") return;
  pi.on("turn_end", async (event: any) => {
    try {
      const messages = event?.messages || [];
      const sessionId = event?.sessionId;
      // Spawn non-blocking background review
      spawnBackgroundReview({ messages, sessionId, sync: false }).catch(() => {
        // Suppress any uncaught rejection
      });
    } catch {
      // Contain error
    }
  });
}
