/**
 * Rate Limit Tracking (§1.9)
 *
 * Tracks x-ratelimit-* response headers and guards against rate quota exhaustion.
 */

export interface RateLimitBucket {
  limit: number;
  remaining: number;
  reset_seconds: number;
  captured_at: number;
}

export interface RateLimitState {
  provider: string;
  requests_min?: RateLimitBucket;
  tokens_min?: RateLimitBucket;
}

export class RateLimitTracker {
  private statesByProvider: Map<string, RateLimitState> = new Map();

  public updateFromHeaders(headers: Record<string, string>, provider: string = "generic"): RateLimitState {
    const norm: Record<string, string> = {};
    for (const [k, v] of Object.entries(headers)) {
      norm[k.toLowerCase()] = v;
    }
    const state: RateLimitState = this.statesByProvider.get(provider) || { provider };

    const rpmLimit = parseInt(norm["x-ratelimit-limit-requests"] || "0", 10);
    const rpmRem = parseInt(norm["x-ratelimit-remaining-requests"] || "0", 10);
    const rpmReset = parseFloat(norm["x-ratelimit-reset-requests"] || "0");
    if (rpmLimit > 0) {
      state.requests_min = {
        limit: rpmLimit,
        remaining: rpmRem,
        reset_seconds: rpmReset,
        captured_at: Date.now(),
      };
    }

    const tpmLimit = parseInt(norm["x-ratelimit-limit-tokens"] || "0", 10);
    const tpmRem = parseInt(norm["x-ratelimit-remaining-tokens"] || "0", 10);
    const tpmReset = parseFloat(norm["x-ratelimit-reset-tokens"] || "0");
    if (tpmLimit > 0) {
      state.tokens_min = {
        limit: tpmLimit,
        remaining: tpmRem,
        reset_seconds: tpmReset,
        captured_at: Date.now(),
      };
    }

    this.statesByProvider.set(provider, state);
    return state;
  }

  public shouldPause(provider: string = "generic", minRemaining: number = 2): boolean {
    const state = this.statesByProvider.get(provider);
    if (!state) return false;
    if (state.requests_min && state.requests_min.limit > 0 && state.requests_min.remaining < minRemaining) {
      return true;
    }
    return false;
  }
}
