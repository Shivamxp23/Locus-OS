/**
 * locus-extension/src/anti-hallucination.ts - Anti-Hallucination Guard
 *
 * Implements Spec §2.6 (Anti-Hallucination Guard Stage 10).
 */

export interface VerificationResult {
  blocked: boolean;
  sanitizedResponse: string;
  ungroundedClaims: string[];
  mode: "warn" | "strict" | "disabled";
}

export interface AntiHallucinationProvider {
  verify(response: string, context: string, mode?: "warn" | "strict"): VerificationResult;
}

export class LocalAntiHallucinationGuard implements AntiHallucinationProvider {
  private enabled: boolean;
  private defaultMode: "warn" | "strict";

  constructor(options: { enabled?: boolean; defaultMode?: "warn" | "strict" } = {}) {
    this.enabled = options.enabled ?? true;
    this.defaultMode = options.defaultMode ?? "warn";
  }

  public isEnabled(): boolean {
    return this.enabled;
  }

  public verify(response: string, context: string, mode?: "warn" | "strict"): VerificationResult {
    if (!this.enabled) {
      return {
        blocked: false,
        sanitizedResponse: response,
        ungroundedClaims: [],
        mode: "disabled",
      };
    }

    const activeMode = mode ?? this.defaultMode;
    const lowerCtx = context.toLowerCase();

    // Check for high-confidence hallucination patterns: exact numbers or claims absent from context
    const claims = response.split(/[.!?\n]+/).map((s) => s.trim()).filter((s) => s.length > 20);
    const ungrounded: string[] = [];

    for (const claim of claims) {
      const lowerClaim = claim.toLowerCase();
      if (lowerClaim.includes("your dcs is") || lowerClaim.includes("you completed")) {
        // Extract words >= 4 chars
        const words = lowerClaim.match(/\b[a-z0-9_-]{4,}\b/g) ?? [];
        const matches = words.filter((w) => lowerCtx.includes(w)).length;
        if (words.length > 0 && matches / words.length < 0.35) {
          ungrounded.push(claim);
        }
      }
    }

    if (ungrounded.length === 0) {
      return {
        blocked: false,
        sanitizedResponse: response,
        ungroundedClaims: [],
        mode: activeMode,
      };
    }

    if (activeMode === "strict") {
      return {
        blocked: true,
        sanitizedResponse: "Response blocked: Contains ungrounded claims not in context.",
        ungroundedClaims: ungrounded,
        mode: "strict",
      };
    }

    return {
      blocked: false,
      sanitizedResponse: `${response}\n\n⚠️ Note: I'm not fully certain about some details. Let me know if anything seems off.`,
      ungroundedClaims: ungrounded,
      mode: "warn",
    };
  }
}
