# US-76 Spec Traceability Matrix

## Feature
- ID: F-0044
- Title: STT / TTS Providers
- Spec Reference: §14.1-14.4 lines 4490-4552

## Traceability Mapping

| Spec Requirement | Spec Line | Implementation | Test Coverage |
|------------------|-----------|----------------|---------------|
| `GroqWhisper` (default, fastest, free tier) STT provider using `whisper-large-v3-turbo` | 4498-4507 | `sidecar/voice/stt.py:GroqWhisperSTTProvider` | `tests/unit/test_voice_pipeline.py:test_groq_whisper_stt_provider`, `tests/integration/test_voice_service.py:test_service_voice_stt_transcribe` |
| `WhisperLocal` STT provider | 4509-4513 | `sidecar/voice/stt.py:WhisperLocalSTTProvider` | `tests/unit/test_voice_pipeline.py:test_whisper_local_stt_provider` |
| `AzureSTT` / `OpenAISTT` STT providers | 4515 | `sidecar/voice/stt.py:OpenAISTTProvider`, `AzureSTTProvider` | `tests/unit/test_voice_pipeline.py:test_openai_and_azure_stt_providers` |
| `EdgeTTS` (default, free, no API key, `en-US-GuyNeural`) TTS provider | 4518-4523 | `sidecar/voice/tts.py:EdgeTTSProvider` | `tests/unit/test_voice_pipeline.py:test_edge_tts_provider`, `tests/integration/test_voice_service.py:test_service_voice_tts_synthesize` |
| `ElevenLabs`, `Piper`, `OpenAITTS` TTS providers | 4524-4533 | `sidecar/voice/tts.py:ElevenLabsTTSProvider`, `PiperTTSProvider`, `OpenAITTSProvider` | `tests/unit/test_voice_pipeline.py:test_elevenlabs_piper_openai_tts_providers` |
| Telegram Voice Message Flow: Audio → STT → Pipeline → TTS → Audio | 4535-4547 | `sidecar/voice/pipeline.py:VoicePipelineManager:process_voice_message` | `tests/unit/test_voice_pipeline.py:test_voice_pipeline_process_voice_message_flow`, `tests/integration/test_voice_service.py:test_service_voice_process_message` |
| Provider Interfaces: `STTProvider`, `TTSProvider`, `VoicePipelineManager` | 4490-4496 | `sidecar/voice/stt.py:BaseSTTProvider`, `sidecar/voice/tts.py:BaseTTSProvider`, `sidecar/voice/pipeline.py:VoicePipelineManager` | `tests/unit/test_voice_pipeline.py:test_voice_pipeline_manager_defaults`, `test_swappable_stt_and_tts_provider` |
| Modular Off-switches (`locus.voice.enabled`, `locus.stt.enabled`, `locus.tts.enabled`) returning HTTP 503 | 4490 | `sidecar/providers/voice.py:DefaultVoiceProvider`, `sidecar/service.py` | `tests/unit/test_voice_pipeline.py:test_voice_provider_off_switches`, `tests/integration/test_voice_service.py:test_service_voice_off_switches` |
| FastAPI Service Routes (`/voice/stt/transcribe`, `/voice/tts/synthesize`, `/voice/process_message`, `/voice/providers`, `/voice/voices`) | 4490 | `sidecar/service.py` | `tests/integration/test_voice_service.py` |
| Extension Client Contract | 4490 | `locus-extension/src/voice/voice.ts:VoicePipelineClient` | TypeScript contract and client |
