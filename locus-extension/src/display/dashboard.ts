/**
 * Locus Terminal Dashboard & TUI Specification (§7.1-7.9, §30.8, §30.11) TypeScript companion.
 */

export interface DashboardState {
  activeModel: string;
  factionDistribution: Record<string, number>;
  runningSubagentsCount: number;
  tokenUsageTotal: number;
  contextTokensUsed: number;
  contextTokenLimit: number;
}

export class LocusTUIDashboard {
  public state: DashboardState = {
    activeModel: 'claude-3-5-sonnet',
    factionDistribution: { Career: 0.4, Health: 0.25, Learning: 0.2, Personal: 0.15 },
    runningSubagentsCount: 0,
    tokenUsageTotal: 0,
    contextTokensUsed: 15400,
    contextTokenLimit: 128000,
  };

  getContextHeadroomPct(): number {
    return Math.max(0, 100 - (this.state.contextTokensUsed / this.state.contextTokenLimit) * 100);
  }

  renderFactionBar(width: number = 40): string {
    let bar = '';
    for (const [faction, pct] of Object.entries(this.state.factionDistribution)) {
      const len = Math.round(pct * width);
      bar += faction[0].toUpperCase().repeat(len);
    }
    return `[${bar.padEnd(width, ' ')}]`;
  }
}
