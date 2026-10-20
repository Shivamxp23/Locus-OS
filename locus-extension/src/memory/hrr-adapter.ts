/**
 * locus-extension/src/memory/hrr-adapter.ts
 *
 * SPEC §4.10: TypeScript bridge for requesting fast zero-LLM associative binds,
 * circular correlation unbinding, superposition bundling, cleanup associative recall,
 * and ephemeral state composition via the Locus Python sidecar.
 */

export interface HRRVector {
  dimension: number;
  values: number[];
}

export interface HolographicConfig {
  enabled: boolean;
  dimension: number;
  similarity_threshold: number;
  codebook_cache_path?: string | null;
}

export interface EphemeralStateInput {
  current_task: { id?: string; name?: string } | string;
  active_mode: { name?: string; tier?: string } | string;
  stress_level: { category?: string; score?: number } | string;
}

export interface CleanupResult {
  symbol: string | null;
  similarity: number;
}

export class HRRAdapter {
  private baseUrl: string;

  constructor(baseUrl: string = "http://127.0.0.1:8420") {
    this.baseUrl = baseUrl.replace(/\/+$/, "");
  }

  async getConfig(): Promise<HolographicConfig> {
    const res = await fetch(`${this.baseUrl}/memory/hrr/config`);
    if (!res.ok) {
      throw new Error(`Failed to fetch HRR config: ${res.status} ${res.statusText}`);
    }
    const data = await res.json();
    return data.config as HolographicConfig;
  }

  async bind(a: HRRVector, b: HRRVector): Promise<HRRVector> {
    const res = await fetch(`${this.baseUrl}/memory/hrr/bind`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ a, b }),
    });
    if (!res.ok) {
      throw new Error(`Failed to bind HRR vectors: ${res.status} ${res.statusText}`);
    }
    const data = await res.json();
    return data.vector as HRRVector;
  }

  async unbind(c: HRRVector, b: HRRVector): Promise<HRRVector> {
    const res = await fetch(`${this.baseUrl}/memory/hrr/unbind`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ c, b }),
    });
    if (!res.ok) {
      throw new Error(`Failed to unbind HRR vector: ${res.status} ${res.statusText}`);
    }
    const data = await res.json();
    return data.vector as HRRVector;
  }

  async bundle(vectors: HRRVector[]): Promise<HRRVector> {
    const res = await fetch(`${this.baseUrl}/memory/hrr/bundle`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ vectors }),
    });
    if (!res.ok) {
      throw new Error(`Failed to bundle HRR vectors: ${res.status} ${res.statusText}`);
    }
    const data = await res.json();
    return data.vector as HRRVector;
  }

  async cleanup(noisyVector: HRRVector, threshold?: number): Promise<CleanupResult> {
    const res = await fetch(`${this.baseUrl}/memory/hrr/cleanup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        vector: noisyVector,
        threshold: threshold !== undefined ? threshold : null,
      }),
    });
    if (!res.ok) {
      throw new Error(`Failed to cleanup HRR vector: ${res.status} ${res.statusText}`);
    }
    const data = await res.json();
    return {
      symbol: data.symbol,
      similarity: data.similarity,
    };
  }

  async encodeEphemeralState(input: EphemeralStateInput): Promise<HRRVector> {
    const res = await fetch(`${this.baseUrl}/memory/hrr/encode_state`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    });
    if (!res.ok) {
      throw new Error(`Failed to encode ephemeral state: ${res.status} ${res.statusText}`);
    }
    const data = await res.json();
    return data.vector as HRRVector;
  }

  async listSymbols(): Promise<string[]> {
    const res = await fetch(`${this.baseUrl}/memory/hrr/codebook/symbols`);
    if (!res.ok) {
      throw new Error(`Failed to list symbols: ${res.status} ${res.statusText}`);
    }
    const data = await res.json();
    return data.symbols as string[];
  }

  async getSymbol(symbol: string): Promise<HRRVector | null> {
    const res = await fetch(
      `${this.baseUrl}/memory/hrr/codebook/symbols/${encodeURIComponent(symbol)}`
    );
    if (res.status === 404) {
      return null;
    }
    if (!res.ok) {
      throw new Error(`Failed to get symbol ${symbol}: ${res.status} ${res.statusText}`);
    }
    const data = await res.json();
    return data.vector as HRRVector;
  }

  async getOrCreateSymbol(symbol: string): Promise<HRRVector> {
    const res = await fetch(`${this.baseUrl}/memory/hrr/codebook/symbol`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbol }),
    });
    if (!res.ok) {
      throw new Error(`Failed to get or create symbol ${symbol}: ${res.status} ${res.statusText}`);
    }
    const data = await res.json();
    return data.vector as HRRVector;
  }
}
