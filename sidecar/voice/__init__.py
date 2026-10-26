"""
SPEC §14.1-14.4 lines 4490-4552:
Voice Pipeline Module re-exports.
"""
from sidecar.voice.pipeline import VoicePipelineManager
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

__all__ = [
    "BaseSTTProvider",
    "GroqWhisperSTTProvider",
    "WhisperLocalSTTProvider",
    "OpenAISTTProvider",
    "AzureSTTProvider",
    "MockSTTProvider",
    "BaseTTSProvider",
    "EdgeTTSProvider",
    "ElevenLabsTTSProvider",
    "PiperTTSProvider",
    "OpenAITTSProvider",
    "MockTTSProvider",
    "VoicePipelineManager",
]
