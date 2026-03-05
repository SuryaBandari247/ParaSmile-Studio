# Requirements Document

## Introduction

The Voice Synthesizer is a Python module that converts scene narration text from VideoScript objects into production-ready audio files using the ElevenLabs Text-to-Speech API. It sits between the Script Converter (upstream) and the Asset Orchestrator's FFmpeg composition step (downstream) in the Faceless Technical Media Engine pipeline. The module generates SSML-annotated narration to enforce human-like pacing, produces per-scene audio files, and returns a manifest mapping each scene to its audio path so the Asset Orchestrator can compose final video segments. All voice output must avoid the "yelling AI voice" anti-pattern — pacing, pauses, and emphasis are controlled via SSML.

## Glossary

- **Voice_Synthesizer**: The top-level Python class responsible for orchestrating narration-to-audio conversion for an entire VideoScript
- **SSML_Builder**: The component that transforms plain narration text into SSML-annotated markup with pauses, emphasis, and pacing controls
- **ElevenLabs_Client**: The component that interfaces with the ElevenLabs Text-to-Speech API to generate audio bytes from SSML text
- **Audio_Manifest**: A dataclass mapping each scene number to its rendered audio file path, duration in seconds, and character count
- **Voice_Config**: Configuration dataclass holding API key, voice ID, model ID, stability/similarity settings, output format, SSML pacing defaults, and filler injection settings
- **Filler_Injection**: The process of inserting conversational filler words (uh, um, hmm, so, basically), thinking pauses, and mid-sentence restarts into narration text to simulate natural human speech patterns
- **Scene_Audio**: A dataclass representing a single scene's synthesized audio with file path, duration, scene number, and character count
- **Video_Script**: The structured script dataclass from the Script Converter containing ordered Scene_Blocks with narration text
- **Scene_Block**: A single scene unit from a VideoScript containing scene_number, narration_text, and visual_instruction

## Requirements

### Requirement 1: VideoScript Narration Extraction

**User Story:** As a pipeline operator, I want narration text extracted from each scene in a VideoScript, so that each scene can be synthesized independently.

#### Acceptance Criteria

1. THE Voice_Synthesizer SHALL accept a Video_Script dataclass as input
2. THE Voice_Synthesizer SHALL extract the narration_text field from each Scene_Block in the Video_Script
3. WHEN a Scene_Block has empty or whitespace-only narration_text, THE Voice_Synthesizer SHALL skip that scene and log a warning with the scene number
4. THE Voice_Synthesizer SHALL process scenes in scene_number order

### Requirement 2: SSML Generation for Human-Like Pacing

**User Story:** As a content producer, I want narration rendered with natural, conversational pacing — including filler words, micro-pauses, and rethinking moments — so that the voice output sounds like a real person explaining something, not a polished pre-written speech.

#### Acceptance Criteria

1. THE SSML_Builder SHALL wrap narration text in a valid SSML `<speak>` root element
2. THE SSML_Builder SHALL insert a `<break time="..."/>` pause after each sentence boundary (period, exclamation mark, question mark followed by whitespace or end-of-string)
3. THE SSML_Builder SHALL use a configurable default sentence pause duration, defaulting to 400 milliseconds
4. THE SSML_Builder SHALL insert a `<break time="..."/>` pause after each paragraph boundary (double newline), defaulting to 800 milliseconds
5. THE SSML_Builder SHALL wrap the entire narration in a `<prosody rate="...">` element with a configurable speaking rate, defaulting to "medium"
6. THE SSML_Builder SHALL support speaking rate values: "x-slow", "slow", "medium", "fast", "x-fast", and percentage values (e.g., "90%")
7. WHEN narration text contains special XML characters (&, <, >, ", '), THE SSML_Builder SHALL escape them before embedding in SSML elements

### Requirement 9: Conversational Filler and Natural Speech Patterns

**User Story:** As a content producer, I want the AI voice to sound like a real person thinking out loud — with filler words, hesitation pauses, and sentence reformulations — so that the output feels genuinely conversational and not like a scripted teleprompter read.

#### Acceptance Criteria

1. THE SSML_Builder SHALL support a Filler_Injection mode that inserts conversational filler words and micro-pauses into narration text before SSML wrapping
2. WHEN Filler_Injection is enabled, THE SSML_Builder SHALL randomly insert filler words (e.g., "uh", "um", "hmm", "so", "like", "you know", "basically", "right", "I mean") at natural insertion points: before conjunctions, after introductory clauses, and at clause boundaries
3. THE SSML_Builder SHALL use a configurable filler_density parameter (0.0–1.0, default 0.15) controlling the probability of inserting a filler at each eligible insertion point
4. THE SSML_Builder SHALL insert "thinking pauses" — `<break time="200ms"/>` to `<break time="600ms"/>` — before filler words to simulate the moment of gathering a thought
5. THE SSML_Builder SHALL vary pause durations randomly within configured bounds (min_thinking_pause_ms default 150, max_thinking_pause_ms default 500) to avoid robotic regularity
6. THE SSML_Builder SHALL occasionally insert mid-sentence restarts where a phrase is begun, interrupted with a short pause and filler, then rephrased (e.g., "this is going to— uh, what I mean is, this will change how we...")
7. THE SSML_Builder SHALL use a configurable restart_probability (0.0–1.0, default 0.05) controlling how often mid-sentence restarts occur
8. THE SSML_Builder SHALL maintain a filler word vocabulary that can be extended or overridden via Voice_Config
9. THE SSML_Builder SHALL never insert fillers inside technical terms, code references, proper nouns, or quoted strings
10. THE SSML_Builder SHALL ensure filler injection is deterministic when given the same random seed, enabling reproducible output for testing
11. Filler_Injection SHALL be enabled by default and can be disabled via Voice_Config for clean narration when needed

### Requirement 3: ElevenLabs API Integration

**User Story:** As a pipeline operator, I want narration synthesized via the ElevenLabs API, so that the output uses high-quality, configurable voices.

#### Acceptance Criteria

1. THE ElevenLabs_Client SHALL authenticate using an API key loaded from the environment variable `ELEVENLABS_API_KEY`
2. IF the `ELEVENLABS_API_KEY` is missing or empty, THEN THE ElevenLabs_Client SHALL raise an AuthenticationError with a descriptive message at initialization
3. THE ElevenLabs_Client SHALL call the ElevenLabs text-to-speech endpoint with the SSML-annotated text, voice ID, and model ID
4. THE ElevenLabs_Client SHALL support configurable voice settings: stability (0.0–1.0, default 0.5), similarity_boost (0.0–1.0, default 0.75), and style (0.0–1.0, default 0.0)
5. THE ElevenLabs_Client SHALL default to the "eleven_multilingual_v2" model when no model ID is configured
6. THE ElevenLabs_Client SHALL return raw audio bytes in the configured output format
7. THE ElevenLabs_Client SHALL support output formats: "mp3_44100_128" (default), "mp3_44100_192", "pcm_16000", "pcm_24000"

### Requirement 4: Per-Scene Audio File Output

**User Story:** As a pipeline operator, I want each scene's narration saved as a separate audio file, so that the Asset Orchestrator can compose each scene independently.

#### Acceptance Criteria

1. THE Voice_Synthesizer SHALL write each scene's audio to a separate file in a configurable output directory, defaulting to `output/audio`
2. THE Voice_Synthesizer SHALL name audio files using the pattern `scene_{scene_number:03d}.mp3` (zero-padded to 3 digits)
3. WHEN the output directory does not exist, THE Voice_Synthesizer SHALL create it including any parent directories
4. THE Voice_Synthesizer SHALL return a Scene_Audio dataclass for each synthesized scene containing: file_path (absolute), duration_seconds (float), scene_number (int), and char_count (int)
5. THE Voice_Synthesizer SHALL calculate audio duration from the audio file after writing

### Requirement 5: Audio Manifest Generation

**User Story:** As a pipeline operator, I want a manifest mapping scenes to audio files, so that the Asset Orchestrator knows which audio to compose with which visual.

#### Acceptance Criteria

1. AFTER synthesizing all scenes, THE Voice_Synthesizer SHALL return an Audio_Manifest containing a list of Scene_Audio entries and summary metadata
2. THE Audio_Manifest SHALL include metadata: total_duration_seconds (sum of all scene durations), total_scenes_synthesized (count), total_characters_processed (sum), generated_at (ISO 8601 UTC timestamp)
3. THE Audio_Manifest SHALL provide a `get_audio_path(scene_number)` method that returns the file path for a given scene number, or None if not found
4. THE Audio_Manifest SHALL provide a `to_dict()` method for JSON serialization

### Requirement 6: Error Handling and Resilience

**User Story:** As a pipeline operator, I want robust error handling, so that a single scene failure does not block the entire narration pipeline.

#### Acceptance Criteria

1. WHEN the ElevenLabs API returns an error for a single scene, THE Voice_Synthesizer SHALL log the error with scene number and continue processing remaining scenes
2. THE Voice_Synthesizer SHALL include failed scenes in the Audio_Manifest with a `None` file_path and an error message field
3. WHEN the ElevenLabs API returns a rate limit error (HTTP 429), THE ElevenLabs_Client SHALL wait and retry up to 3 times with exponential backoff (1s, 2s, 4s)
4. WHEN all retries are exhausted, THE ElevenLabs_Client SHALL raise a SynthesisError with the scene number and API error details
5. WHEN a network error occurs, THE ElevenLabs_Client SHALL raise a NetworkError after retry exhaustion
6. THE Voice_Synthesizer SHALL return partial results with an error summary when some scenes fail

### Requirement 7: Configuration

**User Story:** As a pipeline operator, I want the Voice Synthesizer configurable via environment variables and constructor parameters, so that I can adjust voice, pacing, and output settings without code changes.

#### Acceptance Criteria

1. THE Voice_Synthesizer SHALL read the ElevenLabs API key from the environment variable `ELEVENLABS_API_KEY`
2. THE Voice_Config SHALL accept a configurable voice_id, defaulting to a sensible ElevenLabs preset voice ID
3. THE Voice_Config SHALL accept a configurable model_id, defaulting to "eleven_multilingual_v2"
4. THE Voice_Config SHALL accept configurable SSML pacing defaults: sentence_pause_ms (default 400), paragraph_pause_ms (default 800), speaking_rate (default "medium")
5. THE Voice_Config SHALL accept configurable filler injection settings: filler_enabled (default True), filler_density (default 0.15), restart_probability (default 0.05), min_thinking_pause_ms (default 150), max_thinking_pause_ms (default 500), filler_seed (default None for random)
6. THE Voice_Config SHALL accept a configurable filler_vocabulary list that overrides the default filler words when provided
7. THE Voice_Config SHALL accept a configurable output_format, defaulting to "mp3_44100_128"
8. THE Voice_Config SHALL accept a configurable output_dir, defaulting to "output/audio"
9. THE Voice_Config SHALL validate that stability, similarity_boost, and style values are within the 0.0–1.0 range, raising a ValidationError otherwise
10. THE Voice_Config SHALL validate that filler_density and restart_probability are within the 0.0–1.0 range, raising a ValidationError otherwise

### Requirement 8: Logging and Observability

**User Story:** As a pipeline operator, I want detailed logging, so that I can monitor narration synthesis and debug issues.

#### Acceptance Criteria

1. THE Voice_Synthesizer SHALL log each scene synthesis request with scene number and character count
2. THE Voice_Synthesizer SHALL log synthesis completion for each scene with duration in seconds and output file path
3. THE Voice_Synthesizer SHALL log total synthesis summary: scenes processed, scenes failed, total duration, total characters
4. WHEN errors occur, THE Voice_Synthesizer SHALL log at ERROR level with full context including scene number and error details
5. THE Voice_Synthesizer SHALL support configurable log levels: DEBUG, INFO, WARNING, ERROR
