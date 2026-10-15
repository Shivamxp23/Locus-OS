/**
 * locus-extension/src/tools/custom-tools.ts - Custom Locus Tools TypeScript client.
 *
 * Implements Spec §3.12
 */

export interface CustomToolDefinition {
  name: string;
  description: string;
  parameters: Record<string, unknown>;
  category?: string;
}

export class CustomToolClient {
  private registeredTools: Map<string, CustomToolDefinition> = new Map();

  public registerTool(tool: CustomToolDefinition): void {
    this.registeredTools.set(tool.name, tool);
  }

  public getTool(name: string): CustomToolDefinition | undefined {
    return this.registeredTools.get(name);
  }

  public listTools(): CustomToolDefinition[] {
    return Array.from(this.registeredTools.values());
  }
}
