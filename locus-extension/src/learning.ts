/**
 * Locus Learning, User Profiling & Reward Model Integration (SPEC §1.7, §10.1, §10.3, §10.5, §10.6-10.7, F-0035).
 * Bridges Pi agent events to the Locus sidecar learning provider.
 */

export interface LearningCandidate {
  facetClass: string;
  cueFamily: string;
  evidence: Record<string, any>;
  timestamp: number;
  value?: any;
}

export interface StableFacet {
  facetClass: string;
  key: string;
  value: any;
  confidence: number;
  evidenceCount: number;
  lastUpdated: number;
}

export interface RewardSignal {
  features: Record<string, any>;
  label: number;
  createdAt: number;
}

export interface PatternRecord {
  horizon: string;
  patternType: string;
  confidence: number;
  count: number;
  details?: Record<string, any>;
}

/**
 * Record a learning candidate with the sidecar learning subsystem.
 */
export async function recordLearningCandidate(
  candidate: LearningCandidate,
  sidecarUrl: string = "http://127.0.0.1:8420"
): Promise<boolean> {
  try {
    const res = await fetch(`${sidecarUrl}/learning/candidate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        facet_class: candidate.facetClass,
        cue_family: candidate.cueFamily,
        evidence: candidate.evidence,
        timestamp: candidate.timestamp,
        value: candidate.value,
      }),
    });
    return res.ok;
  } catch {
    return false;
  }
}

/**
 * Check stability and return newly stabilized facets.
 */
export async function checkStability(
  windowSeconds: number = 1800,
  threshold: number = 0.7,
  sidecarUrl: string = "http://127.0.0.1:8420"
): Promise<StableFacet[]> {
  try {
    const res = await fetch(`${sidecarUrl}/learning/stability/check`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ window_seconds: windowSeconds, threshold }),
    });
    if (!res.ok) return [];
    const data = await res.json();
    return (data.stabilized || []).map((s: any) => ({
      facetClass: s.facet_class,
      key: s.key,
      value: s.value,
      confidence: s.confidence,
      evidenceCount: s.evidence_count,
      lastUpdated: s.last_updated,
    }));
  } catch {
    return [];
  }
}

/**
 * Retrieve current compiled PROFILE.md content.
 */
export async function getUserProfile(
  sidecarUrl: string = "http://127.0.0.1:8420"
): Promise<string> {
  try {
    const res = await fetch(`${sidecarUrl}/learning/profile`);
    if (!res.ok) return "";
    const data = await res.json();
    return data.profile || "";
  } catch {
    return "";
  }
}

/**
 * Record a tool usage execution event.
 */
export async function recordToolUsage(
  toolName: string,
  args: any,
  success: boolean,
  durationMs: number,
  sidecarUrl: string = "http://127.0.0.1:8420"
): Promise<boolean> {
  try {
    const res = await fetch(`${sidecarUrl}/learning/tool-usage`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tool_name: toolName,
        args,
        success,
        duration_ms: durationMs,
      }),
    });
    return res.ok;
  } catch {
    return false;
  }
}

/**
 * Record a thumbs-up (1) or thumbs-down (0) feedback signal.
 */
export async function recordRewardSignal(
  features: Record<string, any>,
  label: number,
  sidecarUrl: string = "http://127.0.0.1:8420"
): Promise<boolean> {
  try {
    const res = await fetch(`${sidecarUrl}/learning/reward/signal`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ features, label }),
    });
    return res.ok;
  } catch {
    return false;
  }
}

/**
 * Score a thought/action candidate returning predicted thumbs_up probability.
 */
export async function scoreThought(
  features: Record<string, any>,
  sidecarUrl: string = "http://127.0.0.1:8420"
): Promise<number> {
  try {
    const res = await fetch(`${sidecarUrl}/learning/reward/score`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ features }),
    });
    if (!res.ok) return 0.5;
    const data = await res.json();
    return typeof data.probability === "number" ? data.probability : 0.5;
  } catch {
    return 0.5;
  }
}

/**
 * Update Hebbian edge weight with access, feedback, and STDP modulation.
 */
export async function updateHebbianWeight(
  edgeId: string,
  feedback?: string,
  responseTimeMs?: number,
  sidecarUrl: string = "http://127.0.0.1:8420"
): Promise<number> {
  try {
    const res = await fetch(`${sidecarUrl}/learning/hebbian/update`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        edge_id: edgeId,
        feedback,
        response_time_ms: responseTimeMs,
      }),
    });
    if (!res.ok) return 1.0;
    const data = await res.json();
    return typeof data.weight === "number" ? data.weight : 1.0;
  } catch {
    return 1.0;
  }
}

/**
 * Retrieve detected multi-horizon patterns.
 */
export async function getPatterns(
  sidecarUrl: string = "http://127.0.0.1:8420"
): Promise<PatternRecord[]> {
  try {
    const res = await fetch(`${sidecarUrl}/learning/patterns`);
    if (!res.ok) return [];
    const data = await res.json();
    return data.patterns || [];
  } catch {
    return [];
  }
}

/**
 * Register learning hooks into Pi extension event emitter.
 */
export function registerLearningHooks(pi: any): void {
  if (!pi || typeof pi.on !== "function") return;

  pi.on("tool_call", async (event: any) => {
    try {
      const toolName = event?.toolName || "";
      const args = event?.args || {};
      const success = event?.success ?? true;
      const durationMs = event?.durationMs ?? 0;
      recordToolUsage(toolName, args, success, durationMs).catch(() => {});
    } catch {
      // Never fatal
    }
  });
}
