/**
 * locus-extension/src/tools/budget.ts - Tool Budget TypeScript client.
 *
 * Implements Spec §3.11
 */

export interface BudgetConfig {
  maxInvocationsPerTurn: number;
  maxSecondsPerTurn: number;
  defaultTimeoutSeconds: number;
}

export class ToolBudgetClient {
  constructor(
    private config: BudgetConfig = {
      maxInvocationsPerTurn: 25,
      maxSecondsPerTurn: 120,
      defaultTimeoutSeconds: 15,
    },
  ) {}

  public isWithinLimits(invocationCount: number, totalSeconds: number): boolean {
    return (
      invocationCount < this.config.maxInvocationsPerTurn &&
      totalSeconds < this.config.maxSecondsPerTurn
    );
  }
}
