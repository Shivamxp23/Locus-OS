/**
 * SPEC §27.3: TypeScript client for LOCUS_SHORTHAND 4× Text Compressor (F-0122 / US-96).
 */

export interface ShorthandCompressionResultData {
  original_text: string;
  compressed_text: string;
  original_tokens: number;
  compressed_tokens: number;
  compression_ratio: number;
  tokens_saved: number;
  compressed: boolean;
}

export interface DecompressResultData {
  compressed_text: string;
  decompressed_text: string;
}

export interface CompressEventResultData {
  event_type: string;
  raw_data: Record<string, unknown>;
  compressed_event: string;
}

export interface DecoderDictionaryData {
  decoder: Record<string, string>;
  count: number;
}

export interface ShorthandStatusData {
  feature_enabled?: boolean;
  subsystem_enabled?: boolean;
  provider?: string;
  dictionary_size: number;
}

export interface LocusShorthandClientOptions {
  sidecarUrl?: string;
}

export class LocusShorthandClient {
  private readonly baseUrl: string;

  constructor(options: LocusShorthandClientOptions = {}) {
    this.baseUrl = options.sidecarUrl || "http://127.0.0.1:8420";
  }

  async compress(
    text: string,
    stripArticles: boolean = true
  ): Promise<ShorthandCompressionResultData> {
    const res = await fetch(`${this.baseUrl}/compression/shorthand/compress`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, strip_articles: stripArticles }),
    });
    if (!res.ok) {
      throw new Error(`Failed to compress shorthand text: ${res.status}`);
    }
    return res.json();
  }

  async decompress(text: string): Promise<DecompressResultData> {
    const res = await fetch(`${this.baseUrl}/compression/shorthand/decompress`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!res.ok) {
      throw new Error(`Failed to decompress shorthand text: ${res.status}`);
    }
    return res.json();
  }

  async compressEvent(
    eventType: string,
    data: Record<string, unknown>
  ): Promise<CompressEventResultData> {
    const res = await fetch(`${this.baseUrl}/compression/shorthand/compress-event`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ event_type: eventType, data }),
    });
    if (!res.ok) {
      throw new Error(`Failed to compress behavioral event: ${res.status}`);
    }
    return res.json();
  }

  async getDecoder(): Promise<DecoderDictionaryData> {
    const res = await fetch(`${this.baseUrl}/compression/shorthand/decoder`, {
      method: "GET",
    });
    if (!res.ok) {
      throw new Error(`Failed to get shorthand decoder dictionary: ${res.status}`);
    }
    return res.json();
  }

  async getStatus(): Promise<ShorthandStatusData> {
    const res = await fetch(`${this.baseUrl}/compression/shorthand/status`, {
      method: "GET",
    });
    if (!res.ok) {
      throw new Error(`Failed to get shorthand compressor status: ${res.status}`);
    }
    return res.json();
  }
}
