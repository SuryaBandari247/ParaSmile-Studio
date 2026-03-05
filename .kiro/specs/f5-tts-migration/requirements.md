# Requirements Document: F5-TTS MLX Migration

## Introduction

Replace the ElevenLabs cloud TTS backend with F5-TTS MLX — an open-source, zero-shot text-to-speech model running locally on Apple Silicon via the MLX framework. The existing voice_synthesizer module architecture (VoiceSynthesizer → FillerInjector → SSMLBuilder → TTS Client → Audio Files) is preserved, but the TTS client swaps from ElevenLabs HTTP API to local F5-TTS MLX inference. The filler injection and pacing control systems remain, but pacing is now achieved through silence insertion in the audio waveform rather than SSML markup (F5-TTS doesn't consume SSML). The output format changes from MP3 to WAV (24kHz mono), matching F5-TTS native output.

## Glossary

- **F5-TTS**: A non-autoregressive, zero-shot text-to-speech system using flow-matching mel spectrogram generation with a diffusion transformer
- **MLX**: Apple's machine learning framework optimized for Apple Silicon (M-series chips)
- **Reference Audio**: A 5-10 second mono 24kHz WAV sample used by F5-TTS for zero-shot voice cloning
- **Reference Text**: The transcript of the reference audio, required by F5-TTS for alignment
- **Voice Cloning**: F5-TTS's ability to match the voice characteristics of a reference audio sample
- **Quantized Model**: A reduced-precision version of the F5-TTS model (4-bit or 8-bit) for lower memory usage

## Requirements

### Requirement 1: F5-TTS MLX Client

**User Story:** As a pipeline operator, I want narration synthesized locally using F5-TTS MLX on my Apple Silicon Mac, so that I avoid cloud API costs and latency while maintaining high-quality voice output.

#### Acceptance Criteria

1. THE system SHALL create an `F5TTSClient` class in `voice_synthesizer/f5tts_client.py` that replaces `ElevenLabsClient` as the TTS backend
2. THE `F5TTSClient` SHALL call `f5_tts_mlx.generate.generate()` with the narration text and write the output to a WAV file
3. THE `F5TTSClient` SHALL support a configurable reference audio path (mono 24kHz WAV, 5-10 seconds) for voice cloning
4. THE `F5TTSClient` SHALL support a configurable reference text (transcript of the reference audio)
5. THE `F5TTSClient` SHALL use the bundled default reference audio when no custom reference is provided
6. THE `F5TTSClient` SHALL support configurable generation parameters: steps (default 8), method (default "rk4"), cfg_strength (default 2.0), sway_sampling_coef (default -1.0), speed (default 1.0), seed
7. THE `F5TTSClient` SHALL support optional model quantization (4-bit or 8-bit) via configuration
8. THE `F5TTSClient` SHALL load the F5-TTS model once at initialization and reuse it across all scene syntheses
9. THE `F5TTSClient.synthesize()` SHALL accept plain text (not SSML) and return the file path to the generated WAV

### Requirement 2: Pacing Without SSML

**User Story:** As a content producer, I want natural pacing (sentence pauses, paragraph pauses, thinking pauses) preserved even though F5-TTS doesn't support SSML, so that the voice output still sounds conversational.

#### Acceptance Criteria

1. THE system SHALL create a `PacingProcessor` that converts SSML-style pause markers into silence segments inserted into the final audio waveform
2. THE `PacingProcessor` SHALL insert silence of configurable duration after sentence boundaries
3. THE `PacingProcessor` SHALL insert silence of configurable duration after paragraph boundaries
4. THE `PacingProcessor` SHALL convert `{{pause:Nms}}` markers (from FillerInjector) into silence of N milliseconds in the audio
5. THE `PacingProcessor` SHALL strip all SSML tags and pause markers from text before passing to F5-TTS, producing clean plain text
6. THE `FillerInjector` SHALL continue to work unchanged — its pause markers are consumed by PacingProcessor instead of SSMLBuilder

### Requirement 3: Configuration Update

**User Story:** As a pipeline operator, I want to configure F5-TTS settings (reference audio, speed, model quantization) through VoiceConfig, so that I can tune voice output without code changes.

#### Acceptance Criteria

1. THE `VoiceConfig` SHALL add F5-TTS fields: `ref_audio_path`, `ref_audio_text`, `f5_speed`, `f5_steps`, `f5_method`, `f5_cfg_strength`, `f5_sway_coef`, `f5_seed`, `f5_quantization_bits`
2. THE `VoiceConfig` SHALL remove the `elevenlabs_api_key` requirement — it SHALL no longer raise AuthenticationError when the key is missing
3. THE `VoiceConfig` SHALL retain ElevenLabs fields as optional for backward compatibility but they SHALL NOT be required
4. THE `VoiceConfig` SHALL default `ref_audio_path` to None (use bundled F5-TTS default voice)
5. THE `VoiceConfig` SHALL validate that `f5_speed` is between 0.5 and 2.0
6. THE `VoiceConfig` SHALL validate that `f5_quantization_bits` is None, 4, or 8
7. THE output format SHALL default to WAV (24kHz mono) instead of MP3

### Requirement 4: Synthesizer Integration

**User Story:** As a pipeline operator, I want the VoiceSynthesizer to use F5-TTS by default while keeping the same public interface, so that all downstream consumers (Asset Orchestrator, Pipeline UI) work without changes.

#### Acceptance Criteria

1. THE `VoiceSynthesizer` SHALL use `F5TTSClient` as the default TTS backend
2. THE `VoiceSynthesizer` SHALL no longer require `ELEVENLABS_API_KEY` at initialization
3. THE `VoiceSynthesizer` pipeline SHALL be: narration → FillerInjector → PacingProcessor (extract pauses + clean text) → F5TTSClient (generate audio) → PacingProcessor (insert silence) → write WAV file
4. THE `VoiceSynthesizer` SHALL output WAV files named `scene_{scene_number:03d}.wav`
5. THE `AudioManifest` and `SceneAudio` models SHALL work unchanged with WAV file paths
6. THE per-scene error handling SHALL work unchanged — failed scenes are recorded with error, pipeline continues

### Requirement 5: Dependency and Environment Update

**User Story:** As a developer, I want the project dependencies updated to include F5-TTS MLX and its requirements.

#### Acceptance Criteria

1. THE `requirements.txt` SHALL add `f5-tts-mlx` as a dependency
2. THE `requirements.txt` SHALL add `soundfile` for WAV I/O
3. THE `.env.example` SHALL document F5-TTS configuration options (ref audio path, speed, quantization)
4. THE `ELEVENLABS_API_KEY` SHALL be marked as optional in `.env.example`
