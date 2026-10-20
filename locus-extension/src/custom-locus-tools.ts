/**
 * SPEC §3.12: Custom Locus Tools Client.
 * Bridges TypeScript agent loop and Pi's registerTool() API with Locus Sidecar,
 * managing the ~8 standard Locus tools and dynamic tool toggling.
 */

export interface CustomToolSpec {
  name: string;
  description: string;
  parameters: Record<string, any>;
  category?: string;
  enabled: boolean;
  metadata?: Record<string, any>;
}

export interface CustomToolResult {
  tool_name: string;
  success: boolean;
  output?: any;
  error?: string;
  metadata?: Record<string, any>;
}

export interface CustomLocusToolsConfig {
  enabled: boolean;
  tool_toggles: Record<string, boolean>;
}

export class CustomLocusToolsClient {
  private baseUrl: string;

  constructor(baseUrl: string = "http://localhost:8420") {
    this.baseUrl = baseUrl.replace(/\/+$/, "");
  }

  /**
   * List all registered custom Locus tools, optionally including disabled tools.
   */
  async listTools(includeDisabled: boolean = false): Promise<CustomToolSpec[]> {
    const url = `${this.baseUrl}/tools/custom/list?include_disabled=${includeDisabled}`;
    const response = await fetch(url, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    if (response.status === 503) {
      // Off-switch active; return empty list
      return [];
    }

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`Failed to list custom tools (${response.status}): ${errText}`);
    }

    const data = await response.json();
    return data.tools || [];
  }

  /**
   * Retrieve tool specification for a specific tool.
   */
  async getTool(toolName: string): Promise<CustomToolSpec | null> {
    const url = `${this.baseUrl}/tools/custom/${encodeURIComponent(toolName)}`;
    const response = await fetch(url, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    if (response.status === 404 || response.status === 503) {
      return null;
    }

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`Failed to get custom tool ${toolName} (${response.status}): ${errText}`);
    }

    const data = await response.json();
    return data.tool || null;
  }

  /**
   * Execute a custom Locus tool with parameters.
   */
  async executeTool(
    toolName: string,
    params: Record<string, any>,
  ): Promise<CustomToolResult> {
    const url = `${this.baseUrl}/tools/custom/execute`;
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tool_name: toolName,
        parameters: params,
      }),
    });

    if (response.status === 503) {
      return {
        tool_name: toolName,
        success: false,
        error: "Custom Locus tools subsystem is disabled via locus.custom_locus_tools.enabled",
      };
    }

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`Failed to execute custom tool ${toolName} (${response.status}): ${errText}`);
    }

    const data = await response.json();
    return data.result;
  }

  /**
   * Toggle enabled state of an individual custom tool.
   */
  async toggleTool(toolName: string, enabled: boolean): Promise<boolean> {
    const url = `${this.baseUrl}/tools/custom/${encodeURIComponent(toolName)}/toggle`;
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled }),
    });

    if (response.status === 503) {
      return false;
    }

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`Failed to toggle custom tool ${toolName} (${response.status}): ${errText}`);
    }

    const data = await response.json();
    return Boolean(data.enabled);
  }

  /**
   * Inspect custom tools subsystem health and configuration.
   */
  async getConfig(): Promise<Record<string, any>> {
    const url = `${this.baseUrl}/tools/custom/config`;
    const response = await fetch(url, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    if (response.status === 503) {
      return { enabled: false, status: "disabled" };
    }

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`Failed to get custom tools config (${response.status}): ${errText}`);
    }

    return await response.json();
  }

  /**
   * Register all enabled custom Locus tools with Pi's registerTool() extension API.
   */
  async registerWithPi(pi: any): Promise<number> {
    if (!pi || typeof pi.registerTool !== "function") {
      throw new Error("Invalid Pi instance provided: missing registerTool method");
    }

    const tools = await this.listTools(false);
    let count = 0;

    for (const tool of tools) {
      pi.registerTool({
        name: tool.name,
        description: tool.description,
        parameters: tool.parameters,
        execute: async (params: Record<string, any>) => {
          const res = await this.executeTool(tool.name, params);
          if (!res.success) {
            throw new Error(res.error || `Error executing custom tool ${tool.name}`);
          }
          return res.output;
        },
      });
      count++;
    }

    return count;
  }
}
