"""
SPEC §14.1-14.4 lines 4490-4552:
Voice Pipeline Manager (F-0044 / US-76).

Coordinates Audio → STT → Pipeline → TTS → Audio flow.
Supports runtime swappable STT and TTS providers, default fallbacks,
and Telegram voice message flow.
"""
from __future__ import annotations

import logging
from typing import Callable, Dict, List, Optional, Tuple

from sidecar.voice.stt import (
    AzureSTTProvider,
    BaseSTTProvider,
    GroqWhisperSTTProvider,
    MockSTTProvider,
    OpenAISTTProvider,
    WhisperLocalSTTProvider,
)
from sidecar.voice.tts import (
    BaseTTSProvider,
    EdgeTTSProvider,
    ElevenLabsTTSProvider,
    MockTTSProvider,
    OpenAITTSProvider,
    PiperTTSProvider,
)

logger = logging.getLogger(__name__)


class VoicePipelineManager:
    """
    Manages active STT and TTS providers and executes voice pipeline tasks.
    Default STT: GroqWhisper (fastest, free tier).
    Default TTS: EdgeTTS (free, high quality).
    """

    def __init__(
        self,
        stt_provider: Optional[BaseSTTProvider] = None,
        tts_provider: Optional[BaseTTSProvider] = None,
    ) -> None:
        self._stt_registry: Dict[str, BaseSTTProvider] = {
            "groq_whisper": GroqWhisperSTTProvider(),
            "whisper_local": WhisperLocalSTTProvider(),
            "openai_stt": OpenAISTTProvider(),
            "azure_stt": AzureSTTProvider(),
            "mock_stt": MockSTTProvider(),
        }
        self._tts_registry: Dict[str, BaseTTSProvider] = {
            "edge_tts": EdgeTTSProvider(),
            "elevenlabs": ElevenLabsTTSProvider(),
            "piper": PiperTTSProvider(),
            "openai_tts": OpenAITTSProvider(),
            "mock_tts": MockTTSProvider(),
        }

        self._active_stt: BaseSTTProvider = stt_provider or self._stt_registry["groq_whisper"]
        self._active_tts: BaseTTSProvider = tts_provider or self._tts_registry["edge_tts"]

    @property
    def active_stt(self) -> BaseSTTProvider:
        return self._active_stt

    @property
    def active_tts(self) -> BaseTTSProvider:
        return self._active_tts

    def register_stt_provider(self, name: str, provider: BaseSTTProvider) -> None:
        self._stt_registry[name] = provider

    def register_tts_provider(self, name: str, provider: BaseTTSProvider) -> None:
        self._tts_registry[name] = provider

    def set_stt_provider(self, provider: BaseSTTProvider | str) -> None:
        if isinstance(provider, str):
            if provider not in self._stt_registry:
                raise ValueError(f"Unknown STT provider: {provider}")
            self._active_stt = self._stt_registry[provider]
        else:
            self._active_stt = provider
            self._stt_registry[provider.name] = provider

    def set_tts_provider(self, provider: BaseTTSProvider | str) -> None:
        if isinstance(provider, str):
            if provider not in self._tts_registry:
                raise ValueError(f"Unknown TTS provider: {provider}")
            self._active_tts = self._tts_registry[provider]
        else:
            self._active_tts = provider
            self._tts_registry[provider.name] = provider

    def list_stt_providers(self) -> List[str]:
        return list(self._stt_registry.keys())

    def list_tts_providers(self) -> List[str]:
        return list(self._tts_registry.keys())

    def list_voices(self) -> List[str]:
        return self._active_tts.list_voices()

    def transcribe(
        self,
        audio_bytes: bytes,
        language: str = "en",
        model: Optional[str] = None,
    ) -> str:
        """Transcribe incoming audio buffer using active STT provider."""
        return self._active_stt.transcribe(audio_bytes, language=language, model=model)

    def synthesize(self, text: str, voice: Optional[str] = None) -> bytes:
        """Synthesize response text to audio buffer using active TTS provider."""
        return self._active_tts.synthesize(text, voice=voice)

    def process_voice_message(
        self,
        audio_bytes: bytes,
        processor: Optional[Callable[[str], str]] = None,
        voice: Optional[str] = None,
    ) -> Tuple[str, str, bytes]:
        """
        SPEC §14.3: Telegram Voice Message Flow:
        Audio → STT → Pipeline (processor) → TTS → Audio.
        Returns (transcription, response_text, synthesized_audio_bytes).
        """
        # 1. Transcribe audio
        transcript = self.transcribe(audio_bytes)
        
        # 2. Pipeline generates response text
        if processor:
            response_text = processor(transcript)
        else:
            response_text = f"Processed transcript: {transcript}"

        # 3. TTS provider synthesizes audio
        audio_out = self.synthesize(response_text, voice=voice)

        return transcript, response_text, audio_out
