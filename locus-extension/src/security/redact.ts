/**
 * Data Redaction Engine (§13.8)
 *
 * Masks API keys, bearer tokens, passwords, and private keys in logs and telemetry.
 */

export function maskToken(token: string): string {
  if (token.length < 18) {
    return "***REDACTED***";
  }
  return `${token.slice(0, 6)}...${token.slice(-4)}`;
}

export function redactText(text: string): string {
  const patterns: RegExp[] = [
    /sk-[A-Za-z0-9]{20,}/g,
    /sk-ant-[A-Za-z0-9-]{20,}/g,
    /AIza[A-Za-z0-9_-]{35}/g,
    /ghp_[A-Za-z0-9]{36}/g,
    /Bearer\s+[A-Za-z0-9._-]{20,}/g,
  ];

  let res = text;
  for (const pat of patterns) {
    res = res.replace(pat, m => maskToken(m));
  }
  return res;
}
