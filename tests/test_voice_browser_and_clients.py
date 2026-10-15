"""Test suite for Wave 8B: Voice, Browser, Retrieval & Foundation Clients.

Covers:
- F-0044: STT / TTS Providers (§14.1-14.4)
- F-0045: Browser Automation (§16.1-16.2 + §20.1-20.3)
- F-0059: Vectorless Retrieval (PageIndex) (§27.1)
- F-0124: Auxiliary LLM Client (§29.2)
- F-0034: Plugin LLM Sandboxing & Auxiliary Bridge (§9.9)
"""

import time
import pytest

from sidecar.voice.pipeline import AudioFormat, TranscriptionResult, SynthesisResult, AudioTranscriber, VoiceSynthesizer, VoicePipeline
from sidecar.browser.automation import BrowserAction, BrowserPageSession, BrowserAutomationController
from sidecar.search.pageindex import PageIndexEntry, PageIndexEngine
from sidecar.llm.auxiliary_client import AuxiliaryTaskType, AuxiliaryLLMResponse, AuxiliaryLLMClient
from sidecar.plugins.llm_bridge import PluginQuotaPolicy, PluginLLMBridge


# -----------------------------------------------------------------------------
# F-0044: STT / TTS Voice Pipeline
# -----------------------------------------------------------------------------
def test_voice_pipeline_unit():
    transcriber = AudioTranscriber("whisper")
    synth = VoiceSynthesizer("elevenlabs")

    dummy_audio = b"\x00\x01\x02\x03" * 1000
    res = transcriber.transcribe(dummy_audio)
    assert len(res.text) > 0
    assert res.confidence > 0.9

    synth_res = synth.synthesize("Locus voice pipeline active")
    assert synth_res.audio_format == AudioFormat.MP3
    assert len(synth_res.audio_bytes) > 0


def test_voice_pipeline_integration():
    pipeline = VoicePipeline(stt_provider="whisper", tts_provider="elevenlabs")
    dummy_input = b"\x00\x01" * 500

    def echo_responder(transcript: str) -> str:
        return f"Echoing: {transcript}"

    result = pipeline.process_voice_turn(dummy_input, echo_responder)
    assert result.duration_seconds > 0.1
    assert result.audio_format == AudioFormat.MP3


# -----------------------------------------------------------------------------
# F-0045: Browser Automation
# -----------------------------------------------------------------------------
def test_browser_automation_unit():
    controller = BrowserAutomationController(headless=True)
    session = controller.create_session("sess_1")
    assert session.current_url == "about:blank"

    res = controller.execute_action("sess_1", BrowserAction.NAVIGATE, {"url": "https://locus.local"})
    assert res["status"] == "ok"
    assert session.current_url == "https://locus.local"


def test_browser_automation_integration():
    controller = BrowserAutomationController(headless=True)
    controller.execute_action("sess_auto", BrowserAction.NAVIGATE, {"url": "https://dashboard.local"})
    click_res = controller.execute_action("sess_auto", BrowserAction.CLICK, {"selector": "#submit-btn"})
    assert click_res["clicked"] == "#submit-btn"

    shot = controller.execute_action("sess_auto", BrowserAction.SCREENSHOT, {})
    assert shot["format"] == "png"
    assert "data_base64" in shot


# -----------------------------------------------------------------------------
# F-0059: PageIndex Retrieval
# -----------------------------------------------------------------------------
def test_pageindex_unit():
    engine = PageIndexEngine()
    doc = """# Introduction
Welcome to Locus Operating System.

## Architecture
The system consists of core extensions and sidecar services.

### Memory Engine
Neo4j and LightRAG power cognitive graph memories.
"""
    entries = engine.index_markdown("doc_1", doc)
    assert len(entries) == 3
    assert entries[0].section_title == "Introduction"
    assert entries[1].level == 2


def test_pageindex_integration():
    engine = PageIndexEngine()
    doc = """# Deployment Guide
Instructions for Docker and systemd deployments.

## Security Policies
Details on shell sandboxing and autonomy gate thresholds.
"""
    engine.index_markdown("doc_deploy", doc)
    results = engine.search_index("security sandboxing")
    assert len(results) >= 1
    assert results[0].section_title == "Security Policies"


# -----------------------------------------------------------------------------
# F-0124: Auxiliary LLM Client
# -----------------------------------------------------------------------------
def test_auxiliary_llm_unit():
    client = AuxiliaryLLMClient()
    resp = client.execute_task(AuxiliaryTaskType.TITLE_GENERATION, "Discussion regarding QLoRA fine tuning")
    assert "Title:" in resp.content
    assert resp.token_usage > 0


def test_auxiliary_llm_integration():
    client = AuxiliaryLLMClient()
    r1 = client.execute_task(AuxiliaryTaskType.TAG_EXTRACTION, "Vault note content on biology and graphs")
    r2 = client.execute_task(AuxiliaryTaskType.CONTEXT_SUMMARY, "Long context paragraph to be compressed")

    assert "#project" in r1.content
    assert "Summary:" in r2.content
    assert client.get_total_auxiliary_tokens() > 0


# -----------------------------------------------------------------------------
# F-0034: Plugin LLM Bridge
# -----------------------------------------------------------------------------
def test_plugin_llm_bridge_unit():
    bridge = PluginLLMBridge()
    bridge.register_plugin("plugin_calendar")

    res = bridge.generate_completion("plugin_calendar", "Schedule meeting at 3pm", model="mock-small-fast")
    assert res["success"] is True
    assert "Plugin [plugin_calendar]" in res["completion"]


def test_plugin_llm_bridge_integration():
    policy = PluginQuotaPolicy(
        max_requests_per_minute=100,
        max_tokens_per_hour=5000,
        allowed_models=["mock-small-fast"],
    )
    bridge = PluginLLMBridge()
    bridge.register_plugin("plugin_secure", policy)

    # Disallowed model check
    bad_model = bridge.generate_completion("plugin_secure", "test", model="unauthorized-gpt-5")
    assert bad_model["success"] is False
    assert "not permitted" in bad_model["error"]

    # Allowed model check
    good_model = bridge.generate_completion("plugin_secure", "hello world", model="mock-small-fast")
    assert good_model["success"] is True
