/**
 * SPEC §2.7-2.8 / F-0096 / US-37: Quality-Based Fallback Heuristic (quality.rs).
 * Evaluates response text for length floors, empty noise tokens, and refusal patterns.
 */

export const MIN_RESPONSE_BYTES = 10;
export const EMPTY_NOISE_TOKENS = new Set(["...", "I", "", "?"]);

export const REFUSAL_PATTERNS: string[] = [
  "I cannot",
  "I can't",
  "I'm unable",
  "I apologize but",
  "As an AI",
  "I don't have the ability",
  "I'm not able",
  "I am not able",
];

const REFUSAL_REGEX = new RegExp(
  REFUSAL_PATTERNS.map((p) => p.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|"),
  "i"
);

/**
 * SPEC §2.7-2.8: is_low_quality(response_text) -> bool:
 * Allocation-free hot-path heuristic:
 * - Check 1: Length floor (< MIN_RESPONSE_BYTES)
 * - Check 2: Empty-noise tokens (strip() in ['...', 'I', '', '?'])
 * - Check 3: Refusal pattern matching
 */
export function isLowQuality(
  responseText: string,
  minBytes: number = MIN_RESPONSE_BYTES
): boolean {
  if (!responseText) {
    return true;
  }

  // Check 1: Length floor (UTF-8 byte length)
  const byteLength = new TextEncoder().encode(responseText).length;
  if (byteLength < minBytes) {
    return true;
  }

  // Check 2: Empty-noise tokens
  if (EMPTY_NOISE_TOKENS.has(responseText.trim())) {
    return true;
  }

  // Check 3: Refusal patterns
  if (REFUSAL_REGEX.test(responseText)) {
    return true;
  }

  return false;
}
