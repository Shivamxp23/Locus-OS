/**
 * Locus User Learning & Profiling (§1.7, §10.1, §10.3) TypeScript companion.
 */

export enum SignalType {
  CORRECTION = 'correction',
  APPROVAL = 'approval',
  CLARIFICATION = 'clarification',
  FRUSTRATION = 'frustration',
}

export interface UserProfileSignal {
  signalType: SignalType;
  weight: number;
  context: string;
  inferredPreference: string;
  timestamp: number;
}

export class UserLearningEngine {
  public signals: UserProfileSignal[] = [];
  public profile: Record<string, any> = {
    prefersTerseOutput: false,
    satisfactionScore: 0.8,
  };

  recordTurn(assistantTurn: string, userResponse: string, success: boolean = true): number {
    let score = success ? 0.5 : -0.5;
    const lower = userResponse.toLowerCase();

    if (lower.includes('thanks') || lower.includes('great') || lower.includes('proceed')) {
      score += 0.2;
    }
    if (lower.includes('wrong') || lower.includes('stop') || lower.includes('error')) {
      score -= 0.3;
    }

    if (score >= 0.5) {
      this.signals.push({
        signalType: SignalType.APPROVAL,
        weight: score,
        context: userResponse.slice(0, 80),
        inferredPreference: 'Approved output',
        timestamp: Date.now(),
      });
    }

    if (lower.includes('concise')) {
      this.profile.prefersTerseOutput = true;
    }

    return score;
  }
}
