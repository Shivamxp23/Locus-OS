/**
 * Locus Cause Chain Engine (§30.2 / §30.3) TypeScript companion.
 */

export enum CausalRelationType {
  DIRECT_CAUSE = 'direct_cause',
  ENABLER = 'enabler',
  TRIGGER = 'trigger',
  INHIBITOR = 'inhibitor',
}

export interface CausalLink {
  sourceEvent: string;
  targetEvent: string;
  relationType: CausalRelationType;
  confidence: number;
  evidence?: string;
  timestamp?: number;
}

export class CauseChainEngine {
  private links: CausalLink[] = [];
  private forwardGraph: Map<string, CausalLink[]> = new Map();
  private backwardGraph: Map<string, CausalLink[]> = new Map();

  recordLink(
    sourceEvent: string,
    targetEvent: string,
    relationType: CausalRelationType = CausalRelationType.DIRECT_CAUSE,
    confidence: number = 0.9,
    evidence: string = ''
  ): CausalLink {
    const link: CausalLink = {
      sourceEvent,
      targetEvent,
      relationType,
      confidence,
      evidence,
      timestamp: Date.now(),
    };
    this.links.push(link);

    if (!this.forwardGraph.has(sourceEvent)) this.forwardGraph.set(sourceEvent, []);
    this.forwardGraph.get(sourceEvent)!.push(link);

    if (!this.backwardGraph.has(targetEvent)) this.backwardGraph.set(targetEvent, []);
    this.backwardGraph.get(targetEvent)!.push(link);

    return link;
  }

  traceRootCauses(effectEvent: string, maxDepth: number = 5): string[] {
    const roots = new Set<string>();
    const visited = new Set<string>();

    const dfs = (current: string, depth: number) => {
      if (depth >= maxDepth || visited.has(current)) return;
      visited.add(current);

      const parents = this.backwardGraph.get(current) || [];
      if (parents.length === 0) {
        roots.add(current);
      } else {
        for (const p of parents) {
          dfs(p.sourceEvent, depth + 1);
        }
      }
    };

    dfs(effectEvent, 0);
    return Array.from(roots);
  }
}
