/**
 * SPEC §2.6 / F-0095 / US-35: Anti-Hallucination Guard (Stage 10).
 * Runs verification of generated output against Context Forge retrieval content.
 * Integrates into Pi's afterToolCall hook or as a post-generation verification step.
 */
import { isEnabled } from "./config";

export type GuardMode = "strict" | "warn" | "off";

export const DEFAULT_CAVEAT_MESSAGE =
  "⚠️ Note: I'm not fully certain about some details. Let me know if anything seems off.";

export const DEFAULT_ANTI_HALLUCINATION_CONFIG = {
  mode: "warn" as GuardMode,
  caveatMessage: DEFAULT_CAVEAT_MESSAGE,
  maxUngroundedClaimsBeforeBlock: 1,
};

export interface FactualClaim {
  statement: string;
  category: string;
  confidence: number;
}

export interface BrainErrorLog {
  timestamp: number;
  error_type: string;
  severity: number;
  ungrounded_claims: string[];
  details?: Record<string, any>;
}

export interface AntiHallucinationCheckResult {
  block: boolean;
  reason?: string | null;
  original_response: string;
  output_response: string;
  claims_detected: string[];
  ungrounded_claims: string[];
  brain_error?: BrainErrorLog | null;
  mode: GuardMode;
}

export interface AntiHallucinationGuard {
  check(
    llmResponse: string,
    contextForgeContent: string,
    mode?: GuardMode
  ): Promise<AntiHallucinationCheckResult>;
  extractFactualClaims(llmResponse: string): FactualClaim[];
  containsEvidenceFor(contextContent: string, claim: string): boolean;
  isFeatureEnabled(): boolean;
  handleAfterToolCall(toolName: string, result: any, contextContent: string): Promise<any>;
}

const USER_CLAIM_PATTERNS = [
  /\b(you\s+(have|are|were|did|completed|started|worked|scheduled|logged|noted|set|finished|missed|created|visited|asked))\b/i,
  /\b(your\s+(goal|vault|project|task|habit|calendar|focus|session|sleep|energy|score|dcs|tws|streak|history|status|directive|record))\b/i,
  /\b(in\s+your\s+vault|in\s+your\s+notes|in\s+your\s+system)\b/i,
  /\b(yesterday\s+you|earlier\s+you|last\s+week\s+you)\b/i,
  /\b(according\s+to\s+your\s+(data|records|logs|history))\b/i,
];

const OPINION_PATTERNS = [
  /^(i\s+think|i\s+recommend|i\s+suggest|in\s+my\s+opinion|perhaps|maybe)\b/i,
  /^(you\s+should|you\s+could|try\s+to|consider|make\s+sure\s+to|be\s+careful)\b/i,
  /\b(generally|usually|typically|in\s+python|in\s+typescript|for\s+example)\b/i,
];

export class AntiHallucinationGuardImpl implements AntiHallucinationGuard {
  private sidecarUrl: string;

  constructor(sidecarUrl: string = "http://127.0.0.1:8420") {
    this.sidecarUrl = sidecarUrl;
  }

  isFeatureEnabled(): boolean {
    return isEnabled("locus.brain.anti_hallucination.enabled");
  }

  extractFactualClaims(llmResponse: string): FactualClaim[] {
    if (!llmResponse) return [];
    const claims: FactualClaim[] = [];
    const sentences = llmResponse
      .split(/(?<=[.!?\n])\s+/)
      .map((s) => s.trim())
      .filter((s) => s.length >= 8);

    for (const sent of sentences) {
      if (OPINION_PATTERNS.some((p) => p.test(sent))) {
        continue;
      }
      if (USER_CLAIM_PATTERNS.some((p) => p.test(sent))) {
        let category = "user_data";
        if (/\b(history|yesterday|earlier|previously|last\s+week)\b/i.test(sent)) {
          category = "user_history";
        }
        claims.push({
          statement: sent,
          category,
          confidence: 1.0,
        });
      }
    }
    return claims;
  }

  containsEvidenceFor(contextContent: string, claim: string): boolean {
    if (!contextContent) return false;
    if (!claim) return true;

    const normalizedContext = contextContent.toLowerCase();

    // Check quantities/numbers
    const numbers = claim.match(/\b\d+\b/g) || [];
    for (const num of numbers) {
      if (!normalizedContext.includes(num)) {
        return false;
      }
    }

    const stopwords = new Set([
      "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
      "with", "by", "from", "up", "about", "into", "over", "after", "is",
      "are", "was", "were", "be", "been", "being", "have", "has", "had",
      "do", "does", "did", "you", "your", "yours", "yourself", "he", "she",
      "it", "they", "we", "i", "me", "my", "this", "that", "these", "those",
      "can", "could", "shall", "should", "will", "would", "may", "might",
      "must", "of", "off", "out", "earlier", "today", "yesterday", "completed"
    ]);

    const words = (claim.toLowerCase().match(/\b[a-zA-Z0-9_\-]{3,}\b/g) || []).filter(
      (w) => !stopwords.has(w)
    );

    if (words.length === 0) {
      const allWords = claim.toLowerCase().split(/\s+/);
      if (allWords.length >= 3) {
        for (let i = 0; i <= allWords.length - 3; i++) {
          const phrase = allWords.slice(i, i + 3).join(" ");
          if (normalizedContext.includes(phrase)) {
            return true;
          }
        }
      }
      return false;
    }

    const matches = words.filter((w) => normalizedContext.includes(w));
    return matches.length / words.length >= 0.5;
  }

  async check(
    llmResponse: string,
    contextForgeContent: string,
    mode: GuardMode = "warn"
  ): Promise<AntiHallucinationCheckResult> {
    if (!this.isFeatureEnabled() || mode === "off") {
      return {
        block: false,
        reason: null,
        original_response: llmResponse,
        output_response: llmResponse,
        claims_detected: [],
        ungrounded_claims: [],
        mode: "off",
      };
    }

    // Try delegation to sidecar first if available
    try {
      const response = await fetch(`${this.sidecarUrl}/guard/check`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          llm_response: llmResponse,
          context_forge_content: contextForgeContent,
          mode,
        }),
      });
      if (response.status === 200) {
        const json = await response.json();
        if (json.status === "ok" && json.result) {
          return json.result;
        }
      }
    } catch {
      // Fall back to local evaluation if sidecar is unreachable
    }

    // Local evaluation fallback
    const claims = this.extractFactualClaims(llmResponse);
    const claimsDetected = claims.map((c) => c.statement);
    const ungrounded: string[] = [];

    for (const claim of claims) {
      if (!this.containsEvidenceFor(contextForgeContent, claim.statement)) {
        ungrounded.push(claim.statement);
      }
    }

    if (ungrounded.length > 0) {
      if (mode === "strict") {
        const errorLog: BrainErrorLog = {
          timestamp: Date.now() / 1000,
          error_type: "hallucination",
          severity: 2,
          ungrounded_claims: ungrounded,
          details: { original_length: llmResponse.length },
        };
        return {
          block: true,
          reason: "Response contained ungrounded claims",
          original_response: llmResponse,
          output_response: "",
          claims_detected: claimsDetected,
          ungrounded_claims: ungrounded,
          brain_error: errorLog,
          mode: "strict",
        };
      } else {
        const annotated = `${llmResponse.trimEnd()}\n\n${DEFAULT_CAVEAT_MESSAGE}`;
        const errorLog: BrainErrorLog = {
          timestamp: Date.now() / 1000,
          error_type: "soft_hallucination",
          severity: 1,
          ungrounded_claims: ungrounded,
          details: { original_length: llmResponse.length, caveat_added: true },
        };
        return {
          block: false,
          reason: null,
          original_response: llmResponse,
          output_response: annotated,
          claims_detected: claimsDetected,
          ungrounded_claims: ungrounded,
          brain_error: errorLog,
          mode: "warn",
        };
      }
    }

    return {
      block: false,
      reason: null,
      original_response: llmResponse,
      output_response: llmResponse,
      claims_detected: claimsDetected,
      ungrounded_claims: [],
      mode,
    };
  }

  async handleAfterToolCall(toolName: string, result: any, contextContent: string): Promise<any> {
    // SPEC §2.6 line 1857: Runs in Pi's afterToolCall hook for main response
    if (toolName !== "generate" && toolName !== "main_turn") {
      return result;
    }
    const responseText = typeof result === "string" ? result : result?.text || "";
    if (!responseText) return result;

    const checkRes = await this.check(responseText, contextContent);
    if (checkRes.block) {
      return {
        blocked: true,
        reason: checkRes.reason,
        ungrounded_claims: checkRes.ungrounded_claims,
      };
    }
    if (typeof result === "string") {
      return checkRes.output_response;
    }
    return {
      ...result,
      text: checkRes.output_response,
    };
  }
}

export const defaultAntiHallucinationGuard = new AntiHallucinationGuardImpl();
