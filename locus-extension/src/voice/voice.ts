/**
 * SPEC §14.1-14.4 lines 4490-4552:
 * Voice Pipeline Client & TypeScript Contracts (F-0044 / US-76).
 *
 * Interfaces and client for Speech-to-Text (STT) and Text-to-Speech (TTS)
 * providers and the Telegram/Chat voice message flow (Audio → STT → Process → TTS → Audio).
 */

export interface STTProvider {
  name: string;
  isAvailable(): Promise<boolean>;
  transcribe(audioBuffer: ArrayBuffer | Uint8Array, language?: string): Promise<string>;
}

export interface TTSProvider {
  name: string;
  isAvailable(): Promise<boolean>;
  synthesize(text: string, voice?: string): Promise<ArrayBuffer>;
  listVoices(): Promise<string[]>;
}

export interface VoiceProvidersInfo {
  status: string;
  stt_providers: string[];
  tts_providers: string[];
  default_stt: string;
  default_tts: string;
}

export interface VoiceMessageResult {
  status: string;
  transcript: string;
  response: string;
  audio: string;
  format: string;
}

export class VoicePipelineClient {
  private baseUrl: string;

  constructor(baseUrl: string = "http://localhost:8000") {
    this.baseUrl = baseUrl.replace(/\/+$/, "");
  }

  async transcribe(
    audioBase64: string,
    language: string = "en",
    model?: string
  ): Promise<string> {
    const url = `${this.baseUrl}/voice/stt/transcribe`;
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ audio: audioBase64, language, model }),
    });
    if (resp.status === 503) {
      throw new Error("STT is disabled by off-switch");
    }
    if (!resp.ok) {
      throw new Error(`Failed to transcribe audio: ${resp.status}`);
    }
    const data = (await resp.json()) as { status: string; text: string; provider: string };
    return data.text;
  }

  async synthesize(
    text: string,
    voice?: string
  ): Promise<{ audio: string; format: string; provider: string }> {
    const url = `${this.baseUrl}/voice/tts/synthesize`;
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, voice }),
    });
    if (resp.status === 503) {
      throw new Error("TTS is disabled by off-switch");
    }
    if (!resp.ok) {
      throw new Error(`Failed to synthesize speech: ${resp.status}`);
    }
    const data = (await resp.json()) as {
      status: string;
      audio: string;
      format: string;
      provider: string;
    };
    return { audio: data.audio, format: data.format, provider: data.provider };
  }

  async processVoiceMessage(
    audioBase64: string,
    voice?: string
  ): Promise<VoiceMessageResult> {
    const url = `${this.baseUrl}/voice/process_message`;
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ audio: audioBase64, voice }),
    });
    if (resp.status === 503) {
      throw new Error("Voice pipeline is disabled by off-switch");
    }
    if (!resp.ok) {
      throw new Error(`Failed to process voice message: ${resp.status}`);
    }
    return (await resp.json()) as VoiceMessageResult;
  }

  async getProviders(): Promise<VoiceProvidersInfo> {
    const url = `${this.baseUrl}/voice/providers`;
    const resp = await fetch(url, {
      method: "GET",
      headers: { Accept: "application/json" },
    });
    if (resp.status === 503) {
      throw new Error("Voice pipeline is disabled by off-switch");
    }
    if (!resp.ok) {
      throw new Error(`Failed to get voice providers: ${resp.status}`);
    }
    return (await resp.json()) as VoiceProvidersInfo;
  }

  async getVoices(): Promise<string[]> {
    const url = `${this.baseUrl}/voice/voices`;
    const resp = await fetch(url, {
      method: "GET",
      headers: { Accept: "application/json" },
    });
    if (resp.status === 503) {
      throw new Error("Voice pipeline is disabled by off-switch");
    }
    if (!resp.ok) {
      throw new Error(`Failed to get voices: ${resp.status}`);
    }
    const data = (await resp.json()) as { status: string; voices: string[] };
    return data.voices || [];
  }
}
