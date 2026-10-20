/**
 * SPEC §3.10: Tool Output Accumulator Client.
 * Bridges TypeScript tool execution with Sidecar streaming accumulator,
 * providing bounded memory capture, rolling tail snapshots, and temp file spillover.
 */

export type TruncationType = "lines" | "bytes" | "none";

export interface OutputSnapshot {
  content: string;
  truncated: boolean;
  truncated_by?: TruncationType | null;
  total_lines: number;
  total_bytes: number;
  max_lines: number;
  max_bytes: number;
  full_output_path?: string | null;
}

export interface FullOutputResult {
  content: string;
  truncated: boolean;
  omitted_bytes: number;
}

export interface OutputAccumulatorConfig {
  enabled: boolean;
  default_max_lines: number;
  default_max_bytes: number;
  temp_file_prefix: string;
  persist_temp_files: boolean;
}

export class ToolOutputAccumulatorClient {
  private baseUrl: string;

  constructor(baseUrl: string = "http://localhost:8000") {
    this.baseUrl = baseUrl.replace(/\/+$/, "");
  }

  /**
   * Create a new output accumulator session.
   */
  async createAccumulator(options: {
    accumulatorId?: string;
    maxLines?: number;
    maxBytes?: number;
    tempFilePrefix?: string;
  } = {}): Promise<string> {
    const url = `${this.baseUrl}/tools/accumulator/create`;
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        accumulator_id: options.accumulatorId,
        max_lines: options.maxLines,
        max_bytes: options.maxBytes,
        temp_file_prefix: options.tempFilePrefix,
      }),
    });

    if (response.status === 503) {
      throw new Error("Tool output accumulator is disabled via locus.tool_output_accumulator.enabled");
    }

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`Failed to create output accumulator (${response.status}): ${errText}`);
    }

    const data = await response.json();
    return data.accumulator_id;
  }

  /**
   * Append data chunk to an active accumulator.
   */
  async append(accumulatorId: string, data: string): Promise<OutputSnapshot> {
    const url = `${this.baseUrl}/tools/accumulator/${encodeURIComponent(accumulatorId)}/append`;
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ data }),
    });

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`Failed to append to accumulator (${response.status}): ${errText}`);
    }

    const resData = await response.json();
    return resData.snapshot;
  }

  /**
   * Fetch current tail snapshot of accumulated output.
   */
  async snapshot(accumulatorId: string, persistIfTruncated: boolean = true): Promise<OutputSnapshot> {
    const url = `${this.baseUrl}/tools/accumulator/${encodeURIComponent(accumulatorId)}/snapshot?persist=${persistIfTruncated}`;
    const response = await fetch(url, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`Failed to get accumulator snapshot (${response.status}): ${errText}`);
    }

    const resData = await response.json();
    return resData.snapshot;
  }

  /**
   * Finish output accumulation and flush buffers.
   */
  async finish(accumulatorId: string): Promise<OutputSnapshot> {
    const url = `${this.baseUrl}/tools/accumulator/${encodeURIComponent(accumulatorId)}/finish`;
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`Failed to finish accumulator (${response.status}): ${errText}`);
    }

    const resData = await response.json();
    return resData.snapshot;
  }

  /**
   * Read full output with optional head/tail preservation.
   */
  async readFullOutput(accumulatorId: string, maxBytes: number = 50000): Promise<FullOutputResult> {
    const url = `${this.baseUrl}/tools/accumulator/${encodeURIComponent(accumulatorId)}/full?max_bytes=${maxBytes}`;
    const response = await fetch(url, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`Failed to read full output (${response.status}): ${errText}`);
    }

    const resData = await response.json();
    return resData.full_output;
  }

  /**
   * Close and delete an accumulator session.
   */
  async close(accumulatorId: string): Promise<void> {
    const url = `${this.baseUrl}/tools/accumulator/${encodeURIComponent(accumulatorId)}`;
    const response = await fetch(url, {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
    });

    if (!response.ok && response.status !== 404) {
      const errText = await response.text();
      throw new Error(`Failed to close accumulator (${response.status}): ${errText}`);
    }
  }

  /**
   * Query accumulator configuration and health status.
   */
  async getConfig(): Promise<{ enabled: boolean; config: OutputAccumulatorConfig; provider: string }> {
    const url = `${this.baseUrl}/tools/accumulator/config`;
    const response = await fetch(url, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    if (response.status === 503) {
      return {
        enabled: false,
        provider: "none",
        config: {
          enabled: false,
          default_max_lines: 0,
          default_max_bytes: 0,
          temp_file_prefix: "disabled",
          persist_temp_files: false,
        },
      };
    }

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`Failed to get accumulator config (${response.status}): ${errText}`);
    }

    return await response.json();
  }
}
