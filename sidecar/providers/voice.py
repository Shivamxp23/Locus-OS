"""
SPEC §14.1-14.4 lines 4490-4552:
Voice Provider Interface and Implementation (F-0044 / US-76).

Implements BaseVoiceProvider and DefaultVoiceProvider with modular off-switches:
- locus.voice.enabled
- locus.stt.enabled
- locus.tts.enabled
Returning HTTP 503 when disabled.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

import sidecar.config as config
from sidecar.voice.pipeline import VoicePipelineManager
from sidecar.voice.stt import BaseSTTProvider
from sidecar.voice.tts import BaseTTSProvider

logger = logging.getLogger(__name__)


class BaseVoiceProvider(ABC):
    """
    SPEC §14.1-14.4: Provider Interface: VoiceProvider.
    """

    @abstractmethod
    def is_available(self) -> bool:
        """Check if voice provider is enabled."""
        raise NotImplementedError

    @abstractmethod
    def is_stt_enabled(self) -> bool:
        """Check if STT capability is enabled."""
        raise NotImplementedError

    @abstractmethod
    def is_tts_enabled(self) -> bool:
        """Check if TTS capability is enabled."""
        raise NotImplementedError

    @abstractmethod
    def transcribe(
        self,
        audio_bytes: bytes,
        language: str = "en",
        model: Optional[str] = None,
    ) -> str:
        """Transcribe speech audio into text."""
        raise NotImplementedError

    @abstractmethod
    def synthesize(self, text: str, voice: Optional[str] = None) -> bytes:
        """Synthesize text into speech audio bytes."""
        raise NotImplementedError

    @abstractmethod
    def process_voice_message(
        self,
        audio_bytes: bytes,
        processor: Optional[Callable[[str], str]] = None,
        voice: Optional[str] = None,
    ) -> Tuple[str, str, bytes]:
        """Execute full voice message loop (STT -> process -> TTS)."""
        raise NotImplementedError

    @abstractmethod
    def list_stt_providers(self) -> List[str]:
        """List registered STT provider names."""
        raise NotImplementedError

    @abstractmethod
    def list_tts_providers(self) -> List[str]:
        """List registered TTS provider names."""
        raise NotImplementedError

    @abstractmethod
    def list_voices(self) -> List[str]:
        """List available voices for active TTS provider."""
        raise NotImplementedError

    @abstractmethod
    def set_stt_provider(self, provider: BaseSTTProvider | str) -> None:
        """Swap active STT provider."""
        raise NotImplementedError

    @abstractmethod
    def set_tts_provider(self, provider: BaseTTSProvider | str) -> None:
        """Swap active TTS provider."""
        raise NotImplementedError


class DefaultVoiceProvider(BaseVoiceProvider):
    """
    SPEC §14.1-14.4: Default implementation of VoiceProvider.
    Wraps VoicePipelineManager with configuration off-switches.
    """

    def __init__(
        self,
        pipeline: Optional[VoicePipelineManager] = None,
    ) -> None:
        self.pipeline = pipeline or VoicePipelineManager()

    def is_available(self) -> bool:
        """
        Check modular off-switches:
        - locus.voice.enabled
        """
        v1 = config.get("locus.voice.enabled")
        if v1 is not None and not config.is_enabled("locus.voice.enabled"):
            return False
        return True

    def is_stt_enabled(self) -> bool:
        """Check modular off-switch: locus.stt.enabled and locus.voice.enabled."""
        if not self.is_available():
            return False
        v = config.get("locus.stt.enabled")
        if v is not None and not config.is_enabled("locus.stt.enabled"):
            return False
        return True

    def is_tts_enabled(self) -> bool:
        """Check modular off-switch: locus.tts.enabled and locus.voice.enabled."""
        if not self.is_available():
            return False
        v = config.get("locus.tts.enabled")
        if v is not None and not config.is_enabled("locus.tts.enabled"):
            return False
        return True

    def transcribe(
        self,
        audio_bytes: bytes,
        language: str = "en",
        model: Optional[str] = None,
    ) -> str:
        if not self.is_stt_enabled():
            raise RuntimeError("STT provider is disabled by modular off-switch.")
        return self.pipeline.transcribe(audio_bytes, language=language, model=model)

    def synthesize(self, text: str, voice: Optional[str] = None) -> bytes:
        if not self.is_tts_enabled():
            raise RuntimeError("TTS provider is disabled by modular off-switch.")
        return self.pipeline.synthesize(text, voice=voice)

    def process_voice_message(
        self,
        audio_bytes: bytes,
        processor: Optional[Callable[[str], str]] = None,
        voice: Optional[str] = None,
    ) -> Tuple[str, str, bytes]:
        if not self.is_available():
            raise RuntimeError("Voice pipeline is disabled by modular off-switch.")
        return self.pipeline.process_voice_message(audio_bytes, processor=processor, voice=voice)

    def list_stt_providers(self) -> List[str]:
        return self.pipeline.list_stt_providers()

    def list_tts_providers(self) -> List[str]:
        return self.pipeline.list_tts_providers()

    def list_voices(self) -> List[str]:
        return self.pipeline.list_voices()

    def set_stt_provider(self, provider: BaseSTTProvider | str) -> None:
        self.pipeline.set_stt_provider(provider)

    def set_tts_provider(self, provider: BaseTTSProvider | str) -> None:
        self.pipeline.set_tts_provider(provider)
