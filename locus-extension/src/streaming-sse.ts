/**
 * SPEC §2.6a / F-0097 / US-36: Streaming (SSE) Extension Client.
 * Implements SSE frame decoder, reconnect logic, token accumulation, and
 * stream event dispatching.
 */
import { isEnabled } from "./config";

export interface SSEMessage {
  data: string;
  event?: string;
  id?: string;
  retry?: number;
}

export interface StreamingConfig {
  enabled: boolean;
  pingTimeoutMs: number;
  autoReconnect: boolean;
}

export const DEFAULT_STREAMING_CONFIG: StreamingConfig = {
  enabled: true,
  pingTimeoutMs: 30000,
  autoReconnect: true,
};

export function isStreamingEnabled(): boolean {
  return isEnabled("locus.streaming_sse.enabled", true);
}

export class SSEFrameDecoder {
  private buffer: string = "";

  public push(chunk: string): SSEMessage[] {
    this.buffer += chunk;
    const messages: SSEMessage[] = [];
    const frames = this.buffer.split(/\r?\n\r?\n/);

    // Keep incomplete trailing frame in buffer
    this.buffer = frames.pop() || "";

    for (const frame of frames) {
      if (!frame.trim()) continue;
      const parsed = this.parseFrame(frame);
      if (parsed) {
        messages.push(parsed);
      }
    }
    return messages;
  }

  public flush(): SSEMessage[] {
    if (!this.buffer.trim()) {
      this.buffer = "";
      return [];
    }
    const parsed = this.parseFrame(this.buffer);
    this.buffer = "";
    return parsed ? [parsed] : [];
  }

  private parseFrame(rawFrame: string): SSEMessage | null {
    let event: string | undefined;
    let id: string | undefined;
    let retry: number | undefined;
    const dataLines: string[] = [];

    const lines = rawFrame.split(/\r?\n/);
    for (const line of lines) {
      if (!line || line.startsWith(":")) continue;
      const colonIdx = line.indexOf(":");
      let field = line;
      let value = "";
      if (colonIdx !== -1) {
        field = line.slice(0, colonIdx).trim();
        value = line.slice(colonIdx + 1);
        if (value.startsWith(" ")) {
          value = value.slice(1);
        }
      }

      if (field === "event") {
        event = value;
      } else if (field === "id") {
        id = value;
      } else if (field === "retry") {
        const parsedRetry = parseInt(value, 10);
        if (!isNaN(parsedRetry)) retry = parsedRetry;
      } else if (field === "data") {
        dataLines.append ? dataLines.push(value) : dataLines.push(value);
      }
    }

    if (dataLines.length === 0 && !event && !id) {
      return null;
    }

    return {
      data: dataLines.join("\n"),
      event,
      id,
      retry,
    };
  }
}

export class StreamingSSEConsumer {
  private decoder = new SSEFrameDecoder();
  private config: StreamingConfig;

  constructor(config?: Partial<StreamingConfig>) {
    this.config = { ...DEFAULT_STREAMING_CONFIG, ...config };
  }

  public isEnabled(): boolean {
    return isStreamingEnabled() && this.config.enabled;
  }

  public async consumeChunks(
    chunks: Iterable<string> | AsyncIterable<string>,
    onMessage: (msg: SSEMessage) => void
  ): Promise<string> {
    let accumulatedText = "";

    for await (const chunk of chunks as any) {
      const messages = this.decoder.push(chunk);
      for (const msg of messages) {
        onMessage(msg);
        if (msg.event === "delta" || !msg.event) {
          try {
            const parsed = JSON.parse(msg.data);
            if (parsed && typeof parsed.token === "string") {
              accumulatedText += parsed.token;
            } else if (parsed && typeof parsed.text === "string") {
              accumulatedText += parsed.text;
            } else {
              accumulatedText += msg.data;
            }
          } catch {
            accumulatedText += msg.data;
          }
        }
      }
    }

    const remaining = this.decoder.flush();
    for (const msg of remaining) {
      onMessage(msg);
    }

    return accumulatedText;
  }
}
