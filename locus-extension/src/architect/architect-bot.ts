/**
 * Locus Self-Evolving Architect Bot (§10.8) TypeScript companion.
 */

export enum ProposalSeverity {
  INFO = 'info',
  WARNING = 'warning',
  CRITICAL = 'critical',
}

export interface ArchitectProposal {
  proposalId: string;
  targetPath: string;
  title: string;
  rationale: string;
  severity: ProposalSeverity;
  recommendedDiff: string;
  confidence: number;
}

export class SelfEvolvingArchitectBot {
  private proposals: ArchitectProposal[] = [];

  constructor(public workspaceRoot: string = '.') {}

  inspectModuleMetrics(
    filePath: string,
    lineCount: number,
    cyclomaticComplexity: number
  ): ArchitectProposal | null {
    if (lineCount > 800) {
      const prop: ArchitectProposal = {
        proposalId: `arch_${Date.now()}_mono`,
        targetPath: filePath,
        title: 'Decompose Monolithic Module',
        rationale: `Module has ${lineCount} lines, exceeding 800 lines limit.`,
        severity: ProposalSeverity.WARNING,
        recommendedDiff: '// Extract sub-components into dedicated modules',
        confidence: 0.92,
      };
      this.proposals.push(prop);
      return prop;
    }
    return null;
  }

  getPendingProposals(): ArchitectProposal[] {
    return this.proposals;
  }
}
