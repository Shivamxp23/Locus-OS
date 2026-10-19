/**
 * SPEC §1.9 / F-0009 / US-28: TypeScript Rate Limit Tracking.
 * Port of 12-header parsing, state tracking, display formatting, and pre-call rate guard.
 */
import { isEnabled } from "./config";

export interface RateLimitBucket {
  limit: number;
  remaining: number;
  resetSeconds: number;
  capturedAt: number;
  used: number;
  usagePct: number;
  remainingSecondsNow: number;
}

export interface RateLimitState {
  requestsMin: RateLimitBucket;
  requestsHour: RateLimitBucket;
  tokensMin: RateLimitBucket;
  tokensHour: RateLimitBucket;
  provider: string;
  capturedAt: number;
  hasData: boolean;
}

export function createEmptyBucket(): RateLimitBucket {
  return {
    limit: 0,
    remaining: 0,
    resetSeconds: 0,
    capturedAt: 0,
    used: 0,
    usagePct: 0,
    remainingSecondsNow: 0,
  };
}

export function computeBucket(
  limit: number,
  remaining: number,
  resetSeconds: number,
  capturedAt: number,
  now?: number
): RateLimitBucket {
  const currentNow = now !== undefined ? now : Date.now() / 1000;
  const used = Math.max(0, limit - remaining);
  const usagePct = limit > 0 ? Math.round((used / limit) * 10000) / 100 : 0;
  const elapsed = Math.max(0, currentNow - capturedAt);
  const remainingSecondsNow = Math.max(0, Math.round((resetSeconds - elapsed) * 1000) / 1000);

  return {
    limit,
    remaining,
    resetSeconds,
    capturedAt,
    used,
    usagePct,
    remainingSecondsNow,
  };
}

function parseIntVal(val: any): number {
  if (val === undefined || val === null) return 0;
  if (typeof val === "number") return Math.max(0, Math.floor(val));
  const s = String(val).trim().toLowerCase();
  if (!s) return 0;
  let multiplier = 1;
  if (s.endsWith("k")) {
    multiplier = 1000;
    const n = parseFloat(s.slice(0, -1));
    return isNaN(n) ? 0 : Math.max(0, Math.floor(n * multiplier));
  }
  if (s.endsWith("m")) {
    multiplier = 1000000;
    const n = parseFloat(s.slice(0, -1));
    return isNaN(n) ? 0 : Math.max(0, Math.floor(n * multiplier));
  }
  const n = parseInt(s, 10);
  return isNaN(n) ? 0 : Math.max(0, n);
}

function parseResetSeconds(val: any, now: number): number {
  if (val === undefined || val === null) return 0;
  if (typeof val === "number") {
    if (val > 1e8) return Math.max(0, Math.round((val - now) * 1000) / 1000);
    return Math.max(0, val);
  }
  const s = String(val).trim().toLowerCase();
  if (!s) return 0;
  const num = Number(s);
  if (!isNaN(num)) {
    if (num > 1e8) return Math.max(0, Math.round((num - now) * 1000) / 1000);
    return Math.max(0, num);
  }

  let totalSec = 0;
  let matched = false;
  const hMatch = s.match(/(\d+(?:\.\d+)?)\s*h/);
  if (hMatch) {
    totalSec += parseFloat(hMatch[1]) * 3600;
    matched = true;
  }
  const mMatch = s.match(/(\d+(?:\.\d+)?)\s*m(?!s)/);
  if (mMatch) {
    totalSec += parseFloat(mMatch[1]) * 60;
    matched = true;
  }
  const sMatch = s.match(/(\d+(?:\.\d+)?)\s*s(?!e)/);
  if (sMatch) {
    totalSec += parseFloat(sMatch[1]);
    matched = true;
  }
  const msMatch = s.match(/(\d+(?:\.\d+)?)\s*ms/);
  if (msMatch) {
    totalSec += parseFloat(msMatch[1]) / 1000;
    matched = true;
  }

  return matched ? Math.max(0, Math.round(totalSec * 1000) / 1000) : 0;
}

/**
 * SPEC §1.9 line 2236:
 * Extract 12 x-ratelimit-* headers:
 * RPM, RPH, TPM, TPH limits, remaining, resets.
 */
export function parseRateLimitHeaders(
  headers: Record<string, any>,
  provider: string = "default",
  now?: number
): RateLimitState {
  const currentNow = now !== undefined ? now : Date.now() / 1000;
  const normHeaders: Record<string, any> = {};
  if (headers && typeof headers === "object") {
    for (const [k, v] of Object.entries(headers)) {
      if (typeof k === "string") {
        normHeaders[k.trim().toLowerCase().replace(/_/g, "-")] = v;
      }
    }
  }

  function getVal(keys: string[]): any {
    for (const k of keys) {
      if (k in normHeaders) return normHeaders[k];
    }
    return undefined;
  }

  function parseBucket(prefix: string, isHour: boolean): RateLimitBucket {
    const periodSuffixes = isHour ? ["-1h", "-hour"] : ["", "-1m", "-minute"];
    const limitKeys = periodSuffixes.map((p) => `x-ratelimit-limit-${prefix}${p}`);
    const remKeys = periodSuffixes.map((p) => `x-ratelimit-remaining-${prefix}${p}`);
    const resetKeys = periodSuffixes.map((p) => `x-ratelimit-reset-${prefix}${p}`);

    const rawLimit = getVal(limitKeys);
    const rawRem = getVal(remKeys);
    const rawReset = getVal(resetKeys);

    const limit = parseIntVal(rawLimit);
    const remaining = rawRem !== undefined ? parseIntVal(rawRem) : limit;
    const resetSec = parseResetSeconds(rawReset, currentNow);

    return computeBucket(limit, remaining, resetSec, currentNow, currentNow);
  }

  const requestsMin = parseBucket("requests", false);
  const requestsHour = parseBucket("requests", true);
  const tokensMin = parseBucket("tokens", false);
  const tokensHour = parseBucket("tokens", true);

  const hasData = [requestsMin, requestsHour, tokensMin, tokensHour].some(
    (b) => b.limit > 0 || b.remaining > 0
  );

  return {
    requestsMin,
    requestsHour,
    tokensMin,
    tokensHour,
    provider: provider || "default",
    capturedAt: currentNow,
    hasData,
  };
}

function formatTokens(n: number): string {
  if (n >= 1000000) {
    const val = n / 1000000;
    return val % 1 !== 0 ? `${val.toFixed(1)}M` : `${val}M`;
  }
  if (n >= 1000) {
    const val = n / 1000;
    return val % 1 !== 0 ? `${val.toFixed(1)}K` : `${val}K`;
  }
  return String(n);
}

/**
 * SPEC §1.9 line 2250:
 * Format rate limit state for TUI/footer display.
 */
export function formatRateLimitDisplay(state?: RateLimitState): string {
  if (!state || !state.hasData) {
    return "No rate limit data";
  }

  const items: string[] = [];
  const configs: [string, RateLimitBucket, boolean][] = [
    ["RPM", state.requestsMin, false],
    ["RPH", state.requestsHour, false],
    ["TPM", state.tokensMin, true],
    ["TPH", state.tokensHour, true],
  ];

  for (const [label, bucket, isToken] of configs) {
    if (bucket.limit > 0) {
      const usedStr = isToken ? formatTokens(bucket.used) : String(bucket.used);
      const limitStr = isToken ? formatTokens(bucket.limit) : String(bucket.limit);
      const pctStr = `${Math.round(bucket.usagePct)}%`;
      const remSec = Math.round(bucket.remainingSecondsNow);
      items.push(`${label}: ${usedStr}/${limitStr} (${pctStr}) resets ${remSec}s`);
    }
  }

  return items.length > 0 ? items.join(" | ") : "No rate limit data";
}

/**
 * SPEC §1.9 line 2260:
 * Pre-call rate guard threshold calculation.
 */
export function shouldThrottle(
  state?: RateLimitState,
  safetyMargin: number = 0.1
): { shouldThrottle: boolean; throttleSeconds: number } {
  if (!state || !state.hasData) {
    return { shouldThrottle: false, throttleSeconds: 0 };
  }

  let sleepTime = 0;

  if (state.requestsMin.limit > 0) {
    const threshold = state.requestsMin.limit * safetyMargin;
    if (state.requestsMin.remaining < threshold) {
      sleepTime = Math.max(sleepTime, state.requestsMin.remainingSecondsNow);
    }
  }

  if (state.tokensMin.limit > 0) {
    if (state.tokensMin.remaining < 1000) {
      sleepTime = Math.max(sleepTime, state.tokensMin.remainingSecondsNow);
    }
  }

  return {
    shouldThrottle: sleepTime > 0,
    throttleSeconds: Math.round(sleepTime * 1000) / 1000,
  };
}

/**
 * Singleton rate limit tracker per session.
 */
export class RateLimitTracker {
  private static instance: RateLimitTracker | null = null;
  private states: Map<string, RateLimitState> = new Map();

  public static getInstance(): RateLimitTracker {
    if (!RateLimitTracker.instance) {
      RateLimitTracker.instance = new RateLimitTracker();
    }
    return RateLimitTracker.instance;
  }

  public isEnabled(): boolean {
    return (
      isEnabled("locus.rate_limit_tracking.enabled") ||
      isEnabled("locus.tracking.rate_limit.enabled")
    );
  }

  public updateFromHeaders(
    headers: Record<string, any>,
    provider: string = "default"
  ): RateLimitState | null {
    if (!this.isEnabled()) {
      return null;
    }
    const state = parseRateLimitHeaders(headers, provider);
    this.states.set(provider, state);
    return state;
  }

  public getState(provider: string = "default"): RateLimitState | null {
    if (!this.isEnabled()) return null;
    return this.states.get(provider) || null;
  }

  public getDisplay(provider: string = "default"): string {
    if (!this.isEnabled()) return "";
    const state = this.getState(provider);
    return formatRateLimitDisplay(state || undefined);
  }

  public checkThrottle(
    provider: string = "default",
    safetyMargin: number = 0.1
  ): { shouldThrottle: boolean; throttleSeconds: number } {
    if (!this.isEnabled()) {
      return { shouldThrottle: false, throttleSeconds: 0 };
    }
    const state = this.getState(provider);
    return shouldThrottle(state || undefined, safetyMargin);
  }

  public reset(): void {
    this.states.clear();
  }
}
