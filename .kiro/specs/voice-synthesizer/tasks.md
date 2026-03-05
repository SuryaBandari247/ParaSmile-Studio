# Implementation Plan: Voice Synthesizer

## Overview

Build the `voice_synthesizer` Python module that converts VideoScript scene narrations into production-ready audio files via ElevenLabs TTS with SSML pacing and conversational filler injection. Implementation proceeds bottom-up: exceptions → config/models → filler injector → SSML builder → ElevenLabs client → synthesizer orchestrator → logger integration, with tests alongside each component.

## Tasks

- [x] 1. Set up project structure, dependencies, and exception hierarchy
  - [x] 1.1 Create the `voice_synthesizer/` package directory with `__init__.py`
    - Create `voice_synthesizer/__init__.py` with placeholder exports
    - _Requirements: N/A (project scaffolding)_

  - [x] 1.2 Create the exception hierarchy in `voice_synthesizer/exceptions.py`
    - Implement `VoiceSynthesizerError` base exception
    - Implement `AuthenticationError` for missing/invalid API key
    - Implement `SynthesisError(scene_number: int, message: str)` with scene context
    - Implement `NetworkError` for connectivity failures
    - Implement `ValidationError` for invalid configuration values
    - _Requirements: 3.2, 6.3, 6.4, 6.5, 7.9, 7.10_

  - [x] 1.3 Add `elevenlabs` and `mutagen` dependencies to `requirements.txt`
    - Add `elevenlabs>=1.0.0` for TTS API
    - Add `mutagen>=1.47.0` for audio duration calculation
    - _Requirements: 3.1_

  - [x] 1.4 Update `.env.example` with `ELEVENLABS_API_KEY`
    - Add `ELEVENLABS_API_KEY=your_elevenlabs_api_key_here` with comment
    - _Requirements: 7.1_

- [x] 2. Implement data models and configuration
  - [x] 2.1 Create `voice_synthesizer/models.py` with SceneAudio and AudioManifest dataclasses
    - Implement `SceneAudio` with fields: scene_number, file_path (str|None), duration_seconds, char_count, error (str|None), and `to_dict()` method
    - Implement `AudioManifest` with fields: entries, total_duration_seconds, total_scenes_synthesized, total_scenes_failed, total_characters_processed, generated_at, and `get_audio_path(scene_number)` and `to_dict()` methods
    - _Requirements: 4.4, 5.1, 5.2, 5.3, 5.4_

  - [x] 2.2 Create `voice_synthesizer/config.py` with VoiceConfig dataclass
    - Implement `VoiceConfig` with all fields from design: API settings, voice tuning, SSML pacing, filler injection, output settings
    - Load `ELEVENLABS_API_KEY` from env var
    - Validate stability, similarity_boost, style in 0.0–1.0 range
    - Validate filler_density, restart_probability in 0.0–1.0 range
    - Raise `ValidationError` for out-of-range values
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9, 7.10_

  - [x] 2.3 Create `voice_synthesizer/logger.py` with logging factory
    - Implement `get_logger(name, level)` factory mirroring existing modules
    - Support configurable log levels: DEBUG, INFO, WARNING, ERROR
    - _Requirements: 8.5_

- [x] 3. Implement Filler Injector
  - [x] 3.1 Create `voice_synthesizer/filler_injector.py` with `FillerInjector` class
    - Implement `__init__` with filler_density, restart_probability, pause bounds, vocabulary, seed
    - Define `DEFAULT_FILLERS` with weighted distribution
    - Define `PROTECTED_PATTERNS` for code refs, quotes, proper nouns, acronyms
    - Implement `inject(text)` method:
      - Identify protected spans via regex
      - Find eligible insertion points (clause boundaries, before conjunctions, after introductory phrases)
      - Roll filler_density probability at each point, insert filler + thinking pause marker
      - Roll restart_probability, generate mid-sentence restarts
      - Return text with `{{pause:Nms}}` markers
    - Implement `_find_insertion_points(text, protected_spans)` method
    - Implement `_generate_restart(clause)` method
    - Ensure deterministic output with fixed seed
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8, 9.9, 9.10, 9.11_

  - [x] 3.2 Write unit tests for FillerInjector (`tests/unit/test_filler_injector.py`)
    - Test filler insertion at clause boundaries
    - Test protected spans (code refs, quotes, proper nouns) are never modified
    - Test mid-sentence restart generation
    - Test empty text returns empty text
    - Test deterministic output with fixed seed
    - Test filler_density=0.0 produces no fillers
    - Test filler_density=1.0 fills every eligible point
    - Test custom vocabulary override
    - _Requirements: 9.1, 9.2, 9.3, 9.6, 9.7, 9.8, 9.9, 9.10_

  - [ ]* 3.3 Write property test for protected span preservation (P6)
    - **Property 6: Protected spans are never modified**
    - **Validates: Requirements 9.9**

  - [ ]* 3.4 Write property test for deterministic seed (P7)
    - **Property 7: Deterministic output with fixed seed**
    - **Validates: Requirements 9.10**

- [x] 4. Implement SSML Builder
  - [x] 4.1 Create `voice_synthesizer/ssml_builder.py` with `SSMLBuilder` class
    - Implement `__init__` with sentence_pause_ms, paragraph_pause_ms, speaking_rate
    - Implement `build(text)` method:
      - Escape XML special characters
      - Convert `{{pause:Nms}}` markers to `<break time="Nms"/>` elements
      - Insert sentence-boundary `<break>` elements
      - Insert paragraph-boundary `<break>` elements
      - Wrap in `<prosody rate="...">` element
      - Wrap in `<speak>` root element
    - Implement `_escape_xml(text)` method
    - Implement `_insert_sentence_breaks(text)` method
    - Implement `_insert_paragraph_breaks(text)` method
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

  - [x] 4.2 Write unit tests for SSMLBuilder (`tests/unit/test_ssml_builder.py`)
    - Test output is valid XML with `<speak>` root
    - Test sentence breaks inserted after periods, exclamation marks, question marks
    - Test paragraph breaks inserted after double newlines
    - Test XML special characters escaped (&, <, >, ", ')
    - Test prosody rate wrapping with default and custom rates
    - Test pause markers converted to `<break>` elements
    - Test empty text produces minimal valid SSML
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

  - [ ]* 4.3 Write property test for well-formed SSML (P1)
    - **Property 1: SSML output is well-formed XML**
    - **Validates: Requirements 2.1**

  - [ ]* 4.4 Write property test for XML escaping (P4)
    - **Property 4: XML special characters are escaped**
    - **Validates: Requirements 2.7**

- [x] 5. Checkpoint — Ensure filler injector and SSML builder tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement ElevenLabs Client
  - [x] 6.1 Create `voice_synthesizer/elevenlabs_client.py` with `ElevenLabsClient` class
    - Implement `__init__` with api_key, voice_id, model_id, stability, similarity_boost, style, output_format
    - Raise `AuthenticationError` if api_key is empty/None
    - Implement `synthesize(ssml_text)` returning raw audio bytes
    - Implement `_call_api(ssml_text)` with retry logic: up to 3 retries on HTTP 429 with exponential backoff (1s, 2s, 4s)
    - Raise `SynthesisError` after retry exhaustion on API errors
    - Raise `NetworkError` after retry exhaustion on connectivity failures
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 6.3, 6.4, 6.5_

  - [x] 6.2 Write unit tests for ElevenLabsClient (`tests/unit/test_elevenlabs_client.py`)
    - Test `AuthenticationError` raised for empty API key
    - Test `AuthenticationError` raised for None API key
    - Test successful synthesis returns audio bytes (mocked HTTP)
    - Test retry on HTTP 429 (mocked)
    - Test `SynthesisError` raised after 3 retries (mocked)
    - Test `NetworkError` raised on connection failure (mocked)
    - Test voice settings passed correctly in API request (mocked)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 6.3, 6.4, 6.5_

- [x] 7. Implement VoiceSynthesizer orchestrator
  - [x] 7.1 Create `voice_synthesizer/synthesizer.py` with `VoiceSynthesizer` class
    - Implement `__init__` loading config, initializing FillerInjector, SSMLBuilder, ElevenLabsClient, Logger
    - Raise `AuthenticationError` if ELEVENLABS_API_KEY missing
    - Raise `ValidationError` for invalid config
    - Implement `synthesize(video_script)` method:
      - Extract narration_text from each SceneBlock in scene_number order
      - Skip empty/whitespace narrations with warning log
      - For each scene: inject fillers → build SSML → call ElevenLabs → write file → calculate duration
      - On per-scene failure: log error, create failed SceneAudio entry, continue
      - Build AudioManifest with all entries + metadata
      - Log synthesis summary
    - Implement `_write_audio(audio_bytes, scene_number)` method
    - Implement `_calculate_duration(file_path)` method using mutagen
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 4.1, 4.2, 4.3, 4.4, 4.5, 5.1, 5.2, 6.1, 6.2, 6.6, 8.1, 8.2, 8.3, 8.4_

  - [x] 7.2 Write unit tests for VoiceSynthesizer (`tests/unit/test_voice_synthesizer.py`)
    - Test full pipeline with mocked ElevenLabs API
    - Test empty scene narration is skipped with warning
    - Test partial failure: one scene fails, others succeed
    - Test AudioManifest has correct entry count and metadata
    - Test audio files written to correct output directory
    - Test file naming pattern scene_001.mp3, scene_002.mp3
    - Test `AuthenticationError` raised when API key missing
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 4.1, 4.2, 5.1, 5.2, 6.1, 6.2, 6.6_

  - [ ]* 7.3 Write property test for manifest count invariant (P8)
    - **Property 8: Audio manifest scene count invariant**
    - **Validates: Requirements 5.1, 5.2**

  - [ ]* 7.4 Write property test for partial results (P12)
    - **Property 12: Partial results on scene failure**
    - **Validates: Requirements 6.1, 6.2, 6.6**

- [x] 8. Wire package exports and update configuration
  - [x] 8.1 Update `voice_synthesizer/__init__.py` with public API
    - Export `VoiceSynthesizer`, `VoiceConfig`
    - Export `SceneAudio`, `AudioManifest`
    - Export all custom exceptions
    - Export `SSMLBuilder`, `FillerInjector`, `ElevenLabsClient`
    - _Requirements: N/A (package API)_

- [x] 9. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional property tests — skip for faster MVP
- All ElevenLabs API calls should be mocked in tests to avoid external dependencies and costs
- Follows the same module patterns as `research_agent/` and `script_generator/` (config, exceptions, logger)
- Python 3.13, tests in `tests/unit/`
- The `mutagen` library is used for audio duration calculation from MP3 files
- Filler injection uses `{{pause:Nms}}` markers that the SSMLBuilder converts to `<break>` elements
