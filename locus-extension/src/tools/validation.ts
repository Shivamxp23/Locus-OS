/**
 * locus-extension/src/tools/validation.ts - Tool Call Validation TypeScript client.
 *
 * Implements Spec §3.8
 */

export interface ToolValidationResult {
  isValid: boolean;
  errors: string[];
  sanitizedParams: Record<string, unknown>;
}

export class ToolCallValidatorClient {
  public validateRequiredKeys(toolName: string, params: Record<string, unknown>, requiredKeys: string[]): ToolValidationResult {
    const errors: string[] = [];
    for (const key of requiredKeys) {
      if (params[key] === undefined || params[key] === null) {
        errors.push(`Tool ${toolName}: missing required parameter '${key}'`);
      }
    }
    return {
      isValid: errors.length === 0,
      errors,
      sanitizedParams: { ...params },
    };
  }
}
