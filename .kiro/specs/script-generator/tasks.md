# Implementation Plan: Script Converter

## Overview

Build the `script_generator` Python module that accepts raw script text (from Gemini Pro or any source), uses GPT-4o-mini to convert it into a structured `VideoScript` JSON, validates visual instructions against the Asset Orchestrator schema, and returns a render-ready script. Implementation proceeds bottom-up: exceptions → models/config → serializer → validator → LLM client → converter orchestrator.

## Tasks

- [x] 1. Set up project structure and exception hierarchy
  - [x] 1.1 Create the `script_generator/` package directory with `__init__.py`
    - Create `script_generator/__init__.py` with placeholder exports
    - _Requirements: N/A (project scaffolding)_

  - [x] 1.2 Create the exception hierarchy in `script_generator/exceptions.py`
    - Implement `ScriptConverterError` base exception
    - Implement `ValidationError` for invalid input or visual instructions
    - Implement `ParseError` for LLM response or JSON parse failures
    - Implement `AuthenticationError` for missing/invalid API key
    - Implement `LLMError` for non-retryable OpenAI API errors
    - _Requirements: 6.1, 6.2, 6.3, 6.5_

  - [x] 1.3 Create the logger factory in `script_generator/logger.py`
    - Implement `get_logger(name, level)` factory mirroring `research_agent/logger.py`
    - Support configurable log levels: DEBUG, INFO, WARNING, ERROR
    - Format entries with timestamp, level, module name, message
    - _Requirements: 8.3, 8.4_

- [ ] 2. Implement data models and configuration
  - [x] 2.1 Create `script_generator/models.py` with core dataclasses
    - Implement `SceneBlock` dataclass with `scene_number`, `narration_text`, `visual_instruction` dict
    - Implement `VideoScript` dataclass with `title`, `scenes`, `generated_at`, `total_word_count`, `metadata`
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [x] 2.2 Create `script_generator/config.py` with `ConverterConfig` dataclass
    - Implement `ConverterConfig` with fields: `openai_api_key`, `llm_model`, `log_level`
    - Load `OPENAI_API_KEY` from env var
    - Apply defaults: `llm_model="gpt-4o-mini"`, `log_level="INFO"`
    - Validate config values at init, raise `ValidationError` for invalid values
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [x] 2.3 Write unit tests for models and config (`tests/unit/test_config_sg.py`)
    - Test default config values (gpt-4o-mini, INFO)
    - Test `OPENAI_API_KEY` loaded from environment
    - Test `ValidationError` for invalid `log_level`
    - Test `ValidationError` for empty `llm_model`
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [ ]* 2.4 Write property test for configuration defaults (P5)
    - **Property 5: Configuration defaults**
    - For any `ConverterConfig` created without overrides, defaults are `llm_model="gpt-4o-mini"` and `log_level="INFO"`
    - **Validates: Requirements 7.2, 7.3**

- [ ] 3. Implement serializer
  - [x] 3.1 Create `script_generator/serializer.py` with `ScriptSerializer` class
    - Implement `serialize(script: VideoScript) -> str` converting to JSON with ISO 8601 timestamps
    - Implement `deserialize(json_str: str) -> VideoScript` parsing JSON back to dataclass
    - Raise `ParseError` with description when fields are missing or invalid
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [x] 3.2 Write unit tests for serializer (`tests/unit/test_serializer_sg.py`)
    - Test round-trip with a known `VideoScript` object
    - Test `ParseError` on missing `title` field
    - Test `ParseError` on missing `scenes` field
    - Test `ParseError` on malformed JSON string
    - Test ISO 8601 timestamp format in serialized output
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [ ]* 3.3 Write property test for serialization round-trip (P1)
    - **Property 1: Serialization round-trip**
    - For any valid `VideoScript`, serialize then deserialize produces an equivalent object
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.5**

  - [ ]* 3.4 Write property test for invalid JSON deserialization (P2)
    - **Property 2: Invalid JSON deserialization raises ParseError**
    - For any JSON string missing required fields or with wrong types, `deserialize()` raises `ParseError`
    - **Validates: Requirements 5.4**

- [ ] 4. Implement validator
  - [x] 4.1 Create `script_generator/validator.py` with `Validator` class
    - Define `VALID_TYPES` set: `bar_chart`, `line_chart`, `pie_chart`, `code_snippet`, `text_overlay`
    - Implement `validate_script(script: VideoScript) -> list[str]` returning violation strings
    - Implement `validate_instruction(instruction: dict) -> list[str]` with per-type schema checks:
      - bar_chart/line_chart: `labels` list[str] and `values` list[number] of equal length
      - pie_chart: same as above, values must all be positive
      - code_snippet: non-empty `code` str and `language` str
      - text_overlay: non-empty `text` str
    - _Requirements: 3.3, 3.4, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

  - [x] 4.2 Write unit tests for validator (`tests/unit/test_validator_sg.py`)
    - Test valid bar_chart instruction passes
    - Test bar_chart with mismatched labels/values lengths fails
    - Test pie_chart with negative values fails
    - Test code_snippet with empty code string fails
    - Test text_overlay with empty text fails
    - Test unknown type fails
    - Test `validate_script` aggregates violations across scenes
    - _Requirements: 3.3, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

  - [ ]* 4.3 Write property test for visual instruction validation (P3)
    - **Property 3: Visual instruction validation correctness**
    - For any `VisualInstruction` dict, validator returns empty list iff type is valid and data conforms to schema
    - **Validates: Requirements 3.3, 3.4, 4.2, 4.3, 4.4, 4.5, 4.6**

- [x] 5. Checkpoint — Ensure foundation tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 6. Implement LLM client
  - [x] 6.1 Create `script_generator/llm_client.py` with `LLMClient` class
    - Implement `__init__(api_key, model)` initializing OpenAI client, raising `AuthenticationError` if key is empty/None
    - Implement `complete(system_prompt, user_message) -> LLMResponse` calling `openai.chat.completions.create()` with JSON mode (`response_format={"type": "json_object"}`)
    - Return `LLMResponse` dataclass with `content`, `prompt_tokens`, `completion_tokens`, `model`
    - Raise `LLMError` for non-retryable API errors (e.g., 400)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 6.3, 6.5_

  - [x] 6.2 Write unit tests for LLM client (`tests/unit/test_llm_client_sg.py`)
    - Test `AuthenticationError` raised for empty API key
    - Test `AuthenticationError` raised for None API key
    - Test successful completion returns `LLMResponse` with expected fields (mock OpenAI)
    - Test `LLMError` raised on 400 bad request (mock)
    - Test JSON mode is set in API call (mock)
    - _Requirements: 2.2, 2.3, 6.3, 6.5_

- [ ] 7. Implement ScriptConverter orchestrator
  - [x] 7.1 Create `script_generator/converter.py` with `ScriptConverter` class
    - Implement `__init__(config: ConverterConfig | None)` initializing LLMClient, Validator, Serializer, Logger
    - Raise `AuthenticationError` if `OPENAI_API_KEY` missing
    - Raise `ValidationError` for invalid config
    - Build system prompt containing VideoScript JSON schema and valid visual instruction types
    - _Requirements: 2.1, 6.5, 7.1, 7.4_

  - [x] 7.2 Implement `convert()` method in `ScriptConverter`
    - Accept `raw_script: str`
    - Validate raw_script is non-empty, raise `ValidationError` if empty/whitespace
    - Call LLMClient.complete(system_prompt, raw_script)
    - Parse JSON response into `VideoScript` via Serializer
    - Validate all VisualInstructions via Validator
    - On parse/validation failure (first attempt): retry once with error-correction prompt including error details
    - On second failure: raise `ParseError`
    - Log conversion request with raw script length
    - Log LLM call with model, prompt tokens, completion tokens
    - Log errors at ERROR level with full context
    - Return validated `VideoScript`
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.4, 2.5, 2.6, 3.1, 4.1, 6.1, 6.2, 6.4, 8.1, 8.2, 8.3_

  - [ ]* 7.3 Write property test for system prompt schema inclusion (P4)
    - **Property 4: System prompt contains schema and valid types**
    - For any call to `convert()`, the system prompt contains the VideoScript schema and all five visual instruction type names
    - **Validates: Requirements 2.1**

  - [x] 7.4 Write unit tests for ScriptConverter (`tests/unit/test_converter.py`)
    - Test `ValidationError` raised when raw_script is empty
    - Test `ValidationError` raised when raw_script is whitespace-only
    - Test successful conversion end-to-end with mocked LLM returning valid JSON
    - Test parse failure triggers one retry with error-correction prompt (mock)
    - Test validation failure triggers one retry with error context (mock)
    - Test second failure raises `ParseError`
    - Test `AuthenticationError` raised when API key missing
    - Test logging of conversion request with raw script length
    - Test logging of LLM call with token counts
    - _Requirements: 1.1, 1.2, 2.1, 2.5, 6.1, 6.2, 6.4, 6.5, 8.1, 8.2_

- [ ] 8. Wire package exports
  - [x] 8.1 Update `script_generator/__init__.py` with public API
    - Export `ScriptConverter`, `VideoScript`, `SceneBlock`, `ConverterConfig`
    - Export all custom exceptions
    - Export `ScriptSerializer`, `Validator`
    - _Requirements: N/A (package API)_

- [x] 9. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional property tests — skip for faster MVP
- All OpenAI API calls should be mocked in tests to avoid external dependencies and costs
- Follows the same module patterns as `research_agent/` (config, exceptions, logger)
- Python 3.13, tests in `tests/unit/`
