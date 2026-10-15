/**
 * Locus Code Graph Analysis (§29.6) TypeScript companion.
 */

export enum SymbolKind {
  MODULE = 'module',
  CLASS = 'class',
  FUNCTION = 'function',
  VARIABLE = 'variable',
  IMPORT = 'import',
}

export interface CodeSymbolNode {
  name: string;
  kind: SymbolKind;
  filePath: string;
  lineNumber: number;
  docstring?: string;
  references?: string[];
}

export class CodeDependencyGraph {
  public nodes: Map<string, CodeSymbolNode> = new Map();
  public edges: Map<string, Set<string>> = new Map();
  public reverseEdges: Map<string, Set<string>> = new Map();

  addNode(node: CodeSymbolNode): void {
    this.nodes.set(node.name, node);
    if (!this.edges.has(node.name)) {
      this.edges.set(node.name, new Set());
    }
    if (!this.reverseEdges.has(node.name)) {
      this.reverseEdges.set(node.name, new Set());
    }
  }

  addDependency(sourceName: string, targetName: string): void {
    if (!this.edges.has(sourceName)) {
      this.edges.set(sourceName, new Set());
    }
    if (!this.reverseEdges.has(targetName)) {
      this.reverseEdges.set(targetName, new Set());
    }
    this.edges.get(sourceName)!.add(targetName);
    this.reverseEdges.get(targetName)!.add(sourceName);
  }

  getImpactRadius(symbolName: string, maxDepth: number = 3): Set<string> {
    const impacted = new Set<string>();
    let frontier = new Set<string>([symbolName]);

    for (let depth = 0; depth < maxDepth; depth++) {
      const nextFrontier = new Set<string>();
      for (const cur of frontier) {
        const dependents = this.reverseEdges.get(cur);
        if (dependents) {
          for (const dep of dependents) {
            if (!impacted.has(dep)) {
              impacted.add(dep);
              nextFrontier.add(dep);
            }
          }
        }
      }
      frontier = nextFrontier;
      if (frontier.size === 0) break;
    }

    return impacted;
  }
}
