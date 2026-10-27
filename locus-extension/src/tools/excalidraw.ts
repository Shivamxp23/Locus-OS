/**
 * SPEC §27.7 lines 7305-7378: Excalidraw MCP Skill & Diagram Generator TypeScript client.
 */

export interface ExcalidrawElement {
  id: string;
  type: string;
  x: number;
  y: number;
  width: number;
  height: number;
  strokeColor: string;
  backgroundColor: string;
  text?: string;
  label?: string;
  [key: string]: any;
}

export interface ExcalidrawDoc {
  type: string;
  version: number;
  source: string;
  elements: ExcalidrawElement[];
  appState: {
    viewBackgroundColor: string;
    [key: string]: any;
  };
  files?: Record<string, any>;
}

export interface GenerateDiagramRequest {
  system_spec: string;
  output_filename?: string;
  save_to_vault?: boolean;
  vault_root?: string;
}

export interface GenerateDiagramResponse {
  status: string;
  path?: string | null;
  filename?: string;
  nodes_count?: number;
  edges_count?: number;
  elements_count?: number;
  document?: ExcalidrawDoc;
  error?: string | null;
  status_code: number;
}

export interface DiagramGeneratorStatusResponse {
  subsystem_enabled: boolean;
  target_vault_dir: string;
  excalidraw_version: number;
  provider_enabled?: boolean;
  provider_name?: string;
  status_code?: number;
}

export class ExcalidrawDiagramClient {
  private baseUrl: string;

  constructor(baseUrl: string = "http://127.0.0.1:8420") {
    this.baseUrl = baseUrl.replace(/\/+$/, "");
  }

  async generateDiagram(request: GenerateDiagramRequest): Promise<GenerateDiagramResponse> {
    const response = await fetch(`${this.baseUrl}/diagrams/excalidraw/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });

    if (response.status === 503) {
      const err = await response.json();
      throw new Error(`Excalidraw Generator disabled: ${JSON.stringify(err)}`);
    }

    return (await response.json()) as GenerateDiagramResponse;
  }

  async getStatus(): Promise<DiagramGeneratorStatusResponse> {
    const response = await fetch(`${this.baseUrl}/diagrams/excalidraw/status`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    if (response.status === 503) {
      const err = await response.json();
      throw new Error(`Excalidraw Generator disabled: ${JSON.stringify(err)}`);
    }

    return (await response.json()) as DiagramGeneratorStatusResponse;
  }
}
