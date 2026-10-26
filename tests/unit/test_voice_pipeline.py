"""
SPEC §14.1-14.4 lines 4490-4552: Unit tests for Voice Pipeline (F-0044 / US-76).
"""
from __future__ import annotations

import pytest

import sidecar.config as config
from sidecar.providers.voice import (
    BaseVoiceProvider,
    DefaultVoiceProvider,
)
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


def test_groq_whisper_stt_provider():
    """SPEC §14.1 line 4498: "GroqWhisper (default, fastest, free tier): FUNCTION transcribe(audio_buffer)" """
    provider = GroqWhisperSTTProvider()
    assert provider.name == "groq_whisper"
    assert provider.transcribe(b"") == ""
    # With fallback mock
    res = provider.transcribe(b"test_audio_bytes")
    assert "GroqWhisper" in res
    assert len(res) > 0


def test_whisper_local_stt_provider():
    """SPEC §14.1 line 4509: "WhisperLocal: FUNCTION transcribe(audio_buffer): result = whisper_model.transcribe(audio_buffer)" """
    provider = WhisperLocalSTTProvider(model_size="base")
    assert provider.name == "whisper_local"
    assert provider.transcribe(b"") == ""
    res = provider.transcribe(b"audio_sample")
    assert "WhisperLocal" in res


def test_openai_and_azure_stt_providers():
    """SPEC §14.1 line 4515: "AzureSTT / OpenAISTT: similar HTTP API patterns" """
    oa = OpenAISTTProvider()
    assert oa.name == "openai_stt"
    assert oa.transcribe(b"") == ""
    assert "OpenAISTT" in oa.transcribe(b"12345")

    az = AzureSTTProvider()
    assert az.name == "azure_stt"
    assert az.transcribe(b"") == ""
    assert "AzureSTT" in az.transcribe(b"67890")


def test_edge_tts_provider():
    """SPEC §14.2 line 4518: "EdgeTTS (default, free, no API key): FUNCTION synthesize(text, voice='en-US-GuyNeural')" """
    provider = EdgeTTSProvider()
    assert provider.name == "edge_tts"
    assert provider.synthesize("") == b""
    audio = provider.synthesize("Hello world")
    assert len(audio) > 0
    voices = provider.list_voices()
    assert "en-US-GuyNeural" in voices


def test_elevenlabs_piper_openai_tts_providers():
    """SPEC §14.2 line 4524: "ElevenLabs: FUNCTION synthesize(text, voice_id): response = elevenlabs_api.generate(text=text, voice=voice_id)" """
    el = ElevenLabsTTSProvider()
    assert el.name == "elevenlabs"
    assert el.synthesize("") == b""
    assert b"ElevenLabs" in el.synthesize("sample")
    assert len(el.list_voices()) > 0

    pi = PiperTTSProvider()
    assert pi.name == "piper"
    assert pi.synthesize("") == b""
    assert b"Piper" in pi.synthesize("sample")

    oa = OpenAITTSProvider()
    assert oa.name == "openai_tts"
    assert oa.synthesize("") == b""
    assert b"OpenAI TTS" in oa.synthesize("sample")
    assert "alloy" in oa.list_voices()


def test_voice_pipeline_manager_defaults():
    """SPEC §14.1 line 4498: "Default: Groq Whisper (STT), Edge TTS (TTS) — both free." """
    manager = VoicePipelineManager()
    assert manager.active_stt.name == "groq_whisper"
    assert manager.active_tts.name == "edge_tts"
    assert "groq_whisper" in manager.list_stt_providers()
    assert "edge_tts" in manager.list_tts_providers()


def test_voice_pipeline_process_voice_message_flow():
    """SPEC §14.3 line 4535: "TELEGRAM VOICE MESSAGE FLOW: 1. User sends voice message on Telegram ... Audio → STT → Pipeline → TTS → Audio" """
    mock_stt = MockSTTProvider("What is the capital of France?")
    mock_tts = MockTTSProvider(["voice_test"])
    manager = VoicePipelineManager(stt_provider=mock_stt, tts_provider=mock_tts)

    def dummy_pipeline(prompt: str) -> str:
        return f"Response to: {prompt}"

    transcript, response, audio = manager.process_voice_message(
        b"dummy_ogg_audio",
        processor=dummy_pipeline,
        voice="voice_test",
    )

    assert transcript == "What is the capital of France?"
    assert response == "Response to: What is the capital of France?"
    assert audio == b"MOCK_AUDIO(voice_test):Response to: What is the capital of France?"


def test_voice_provider_off_switches():
    """SPEC §14.1 line 4490: "Voice handling at Stage 0 (Intake). The STT/TTS calls happen in the Python sidecar." """
    mock_stt = MockSTTProvider("hello")
    mock_tts = MockTTSProvider()
    mgr = VoicePipelineManager(stt_provider=mock_stt, tts_provider=mock_tts)
    provider = DefaultVoiceProvider(pipeline=mgr)

    assert provider.is_available() is True
    assert provider.is_stt_enabled() is True
    assert provider.is_tts_enabled() is True

    # Disable entire voice subsystem
    config.set("locus.voice.enabled", False)
    try:
        assert provider.is_available() is False
        assert provider.is_stt_enabled() is False
        assert provider.is_tts_enabled() is False

        with pytest.raises(RuntimeError, match="disabled"):
            provider.transcribe(b"test")

        with pytest.raises(RuntimeError, match="disabled"):
            provider.synthesize("test")

        with pytest.raises(RuntimeError, match="disabled"):
            provider.process_voice_message(b"test")
    finally:
        config.set("locus.voice.enabled", True)

    # Disable STT only
    config.set("locus.stt.enabled", False)
    try:
        assert provider.is_stt_enabled() is False
        assert provider.is_tts_enabled() is True
        with pytest.raises(RuntimeError, match="STT provider is disabled"):
            provider.transcribe(b"test")
        # TTS should still work
        assert len(provider.synthesize("test")) > 0
    finally:
        config.set("locus.stt.enabled", True)

    # Disable TTS only
    config.set("locus.tts.enabled", False)
    try:
        assert provider.is_stt_enabled() is True
        assert provider.is_tts_enabled() is False
        with pytest.raises(RuntimeError, match="TTS provider is disabled"):
            provider.synthesize("test")
        # STT should still work
        assert provider.transcribe(b"test") == "hello"
    finally:
        config.set("locus.tts.enabled", True)


def test_swappable_stt_and_tts_provider():
    """SPEC §14.1 line 4490: "Provider Interfaces: STTProvider, TTSProvider" """
    mgr = VoicePipelineManager()
    provider = DefaultVoiceProvider(pipeline=mgr)

    # Swap to mock STT
    provider.set_stt_provider(MockSTTProvider("Custom swapped transcript"))
    assert provider.transcribe(b"audio") == "Custom swapped transcript"

    # Swap to mock TTS
    provider.set_tts_provider(MockTTSProvider(["swapped_voice"]))
    audio = provider.synthesize("test", voice="swapped_voice")
    assert b"MOCK_AUDIO(swapped_voice):test" == audio
