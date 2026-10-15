/**
 * Prompt Injection Filter (§13.1)
 *
 * Pre-generation defense against prompt injections, jailbreaks, and delimiter escapes.
 */

export interface InjectionScore {
  score: number;
  flagged: boolean;
  triggers: string[];
}

export class PromptInjectionFilter {
  private patterns: RegExp[] = [
    /ignore previous instructions/i,
    /system override/i,
    /you are now in developer mode/i,
    /disregard safety guidelines/i,
    /reveal your system prompt/i,
  ];

  public score(text: string): InjectionScore {
    const triggers: string[] = [];
    for (const pat of this.patterns) {
      if (pat.test(text)) {
        triggers.push(pat.source);
      }
    }
    const score = triggers.length * 0.4;
    return {
      score: Math.min(1.0, score),
      flagged: triggers.length > 0,
      triggers,
    };
  }
}
