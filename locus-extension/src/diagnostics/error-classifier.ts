/**
 * Locus Error Classifier (§29.1) TypeScript companion.
 */

export enum ErrorCategory {
  TRANSIENT = 'transient',
  RATE_LIMIT = 'rate_limit',
  CONTEXT_OVERFLOW = 'context_overflow',
  AUTH_FAILURE = 'auth_failure',
  PERMISSION_DENIED = 'permission_denied',
  SYNTAX_ERROR = 'syntax_error',
  TOOL_EXECUTION_FAILURE = 'tool_execution_failure',
  TIMEOUT = 'timeout',
  MODEL_UNAVAILABLE = 'model_unavailable',
  UNKNOWN = 'unknown',
}

export interface ClassifiedError {
  category: ErrorCategory;
  rawMessage: string;
  isRetryable: boolean;
  retryDelaySeconds: number;
  suggestedAction: string;
  metadata?: Record<string, any>;
}

export class ErrorClassifier {
  private static patterns: Array<[ErrorCategory, RegExp[], boolean, number, string]> = [
    [
      ErrorCategory.RATE_LIMIT,
      [/rate limit/i, /429/, /too many requests/i, /quota exceeded/i],
      true,
      30.0,
      'Wait for rate limit window to reset or fallback to alternative model provider',
    ],
    [
      ErrorCategory.CONTEXT_OVERFLOW,
      [/context length/i, /maximum context length/i, /token count exceeded/i, /prompt is too long/i],
      false,
      0.0,
      'Compress context, summarize conversation history, or switch to large-window model',
    ],
    [
      ErrorCategory.AUTH_FAILURE,
      [/invalid api key/i, /unauthorized/i, /401/, /authentication failed/i],
      false,
      0.0,
      'Verify credentials and refresh API keys or OAuth tokens',
    ],
    [
      ErrorCategory.PERMISSION_DENIED,
      [/permission denied/i, /access denied/i, /403/, /eacces/i],
      false,
      0.0,
      'Check file system permissions or request human elevation approval',
    ],
    [
      ErrorCategory.TIMEOUT,
      [/timed out/i, /timeout/i, /etimedout/i, /deadline exceeded/i, /504/],
      true,
      5.0,
      'Retry operation with increased timeout budget',
    ],
    [
      ErrorCategory.MODEL_UNAVAILABLE,
      [/model unavailable/i, /service unavailable/i, /503/, /500/, /502/],
      true,
      10.0,
      'Failover to backup model endpoint',
    ],
  ];

  classify(error: Error | string, context?: Record<string, any>): ClassifiedError {
    const msg = error instanceof Error ? error.message : String(error);

    for (const [category, patterns, retryable, delay, action] of ErrorClassifier.patterns) {
      for (const pat of patterns) {
        if (pat.test(msg)) {
          return {
            category,
            rawMessage: msg,
            isRetryable: retryable,
            retryDelaySeconds: delay,
            suggestedAction: action,
            metadata: context,
          };
        }
      }
    }

    return {
      category: ErrorCategory.UNKNOWN,
      rawMessage: msg,
      isRetryable: false,
      retryDelaySeconds: 0.0,
      suggestedAction: 'Escalate to user or log diagnostic report',
      metadata: context,
    };
  }
}
