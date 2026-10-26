"""
SPEC §14.1-14.4 lines 4490-4552: Integration tests for Voice Service (F-0044 / US-76).
"""
from __future__ import annotations

import base64
import pytest
from starlette.testclient import TestClient

import sidecar.config as config
from sidecar.service import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    return TestClient(app)


def test_service_voice_stt_transcribe(client: TestClient) -> None:
    """SPEC §14.1 line 4498: "GroqWhisper (default, fastest, free tier): FUNCTION transcribe(audio_buffer)" """
    sample_bytes = b"RIFF dummy wav audio data"
    audio_b64 = base64.b64encode(sample_bytes).decode("ascii")
    res = client.post("/voice/stt/transcribe", json={"audio": audio_b64, "language": "en"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "text" in data
    assert data["provider"] == "groq_whisper"


def test_service_voice_tts_synthesize(client: TestClient) -> None:
    """SPEC §14.2 line 4518: "EdgeTTS (default, free, no API key): FUNCTION synthesize(text, voice='en-US-GuyNeural')" """
    res = client.post("/voice/tts/synthesize", json={"text": "Welcome to Locus OS", "voice": "en-US-GuyNeural"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["format"] == "wav"
    assert "audio" in data
    # Decodes properly as base64
    decoded = base64.b64decode(data["audio"])
    assert len(decoded) > 0


def test_service_voice_process_message(client: TestClient) -> None:
    """SPEC §14.3 line 4535: "TELEGRAM VOICE MESSAGE FLOW: 1. User sends voice message on Telegram ... Audio → STT → Pipeline → TTS → Audio" """
    sample_bytes = b"Sample voice input"
    audio_b64 = base64.b64encode(sample_bytes).decode("ascii")
    res = client.post("/voice/process_message", json={"audio": audio_b64})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "transcript" in data
    assert "response" in data
    assert "audio" in data
    assert data["format"] == "wav"


def test_service_voice_providers_and_voices(client: TestClient) -> None:
    """SPEC §14.1 line 4490: "Provider Interfaces: STTProvider, TTSProvider" """
    res = client.get("/voice/providers")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "groq_whisper" in data["stt_providers"]
    assert "edge_tts" in data["tts_providers"]
    assert data["default_stt"] == "groq_whisper"
    assert data["default_tts"] == "edge_tts"

    res_voices = client.get("/voice/voices")
    assert res_voices.status_code == 200
    voices_data = res_voices.json()
    assert voices_data["status"] == "ok"
    assert "en-US-GuyNeural" in voices_data["voices"]


def test_service_voice_off_switches(client: TestClient) -> None:
    """SPEC §14.1 line 4490: "Modular off-switch returns HTTP 503 when feature is disabled." """
    # Disable entire voice subsystem
    config.set("locus.voice.enabled", False)
    try:
        r1 = client.post("/voice/stt/transcribe", json={"audio": "dGVzdA=="})
        assert r1.status_code == 503

        r2 = client.post("/voice/tts/synthesize", json={"text": "test"})
        assert r2.status_code == 503

        r3 = client.post("/voice/process_message", json={"audio": "dGVzdA=="})
        assert r3.status_code == 503

        r4 = client.get("/voice/providers")
        assert r4.status_code == 503

        r5 = client.get("/voice/voices")
        assert r5.status_code == 503
    finally:
        config.set("locus.voice.enabled", True)

    # Disable STT only
    config.set("locus.stt.enabled", False)
    try:
        r_stt = client.post("/voice/stt/transcribe", json={"audio": "dGVzdA=="})
        assert r_stt.status_code == 503
        # TTS still works
        r_tts = client.post("/voice/tts/synthesize", json={"text": "test"})
        assert r_tts.status_code == 200
    finally:
        config.set("locus.stt.enabled", True)

    # Disable TTS only
    config.set("locus.tts.enabled", False)
    try:
        r_tts = client.post("/voice/tts/synthesize", json={"text": "test"})
        assert r_tts.status_code == 503
        # STT still works
        r_stt = client.post("/voice/stt/transcribe", json={"audio": "dGVzdA=="})
        assert r_stt.status_code == 200
    finally:
        config.set("locus.tts.enabled", True)
