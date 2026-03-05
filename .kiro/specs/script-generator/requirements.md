# Requirements Document

## Introduction

The Script Converter is a Python module in the Faceless Technical Media Engine pipeline. Instead of generating scripts from scratch, it accepts raw script text that the user has written using Gemini Pro (or any other tool) and converts it into the structured `VideoScript` JSON format that the Asset Orchestrator expects. The conversion is handled by GPT-4o-mini — a cheap, fast formatting call, not content generation. Every output is validated against the Asset Orchestrator's visual instruction schema before leaving the module.

## Glossary

- **Script_Converter**: The top-level Python class responsible for orchestrating raw-text-to-VideoScript conversion
- **Video_Script**: A structured dataclass containing an ordered list of Scene_Blocks that together form a complete video script
- **Scene_Block**: A single unit of a Video_Script containing narration text and a Visual_Instruction
- **Visual_Instruction**: A structured directive consumed by the Asset Orchestrator with fields: type, title, data, and optional style (types: bar_chart, line_chart, pie_chart, code_snippet, text_overlay)
- **LLM_Client**: The component that interfaces with OpenAI's API for format conversion
- **Script_Serializer**: The component that converts Video_Script objects to and from JSON
- **Validator**: The component that checks Visual_Instructions against the Asset Orchestrator schema

## Requirements

### Requirement 1: Raw Script Input

**User Story:** As a content producer, I want to paste my Gemini Pro script in any format, so that I can quickly convert it to a render-ready structure without manual formatting.

#### Acceptance Criteria

1. THE Script_Converter SHALL accept a raw script as a single string input
2. WHEN the raw script string is empty or contains only whitespace, THE Script_Converter SHALL raise a ValidationError with a descriptive message
3. THE Script_Converter SHALL accept raw scripts in plain text, markdown, or any structured text format without requiring a specific input schema

### Requirement 2: LLM-Based Format Conversion

**User Story:** As a content producer, I want GPT-4o-mini to structure my raw script into VideoScript JSON, so that the conversion is automated and consistent.

#### Acceptance Criteria

1. THE Script_Converter SHALL call the LLM_Client with a system prompt containing the VideoScript JSON schema and the list of valid Visual_Instruction types (bar_chart, line_chart, pie_chart, code_snippet, text_overlay)
2. THE LLM_Client SHALL use OpenAI as the LLM provider
3. WHEN the LLM model is not specified in configuration, THE LLM_Client SHALL default to gpt-4o-mini
4. THE Script_Converter SHALL send the raw script text as the user message to the LLM_Client
5. WHEN the LLM returns a response, THE Script_Converter SHALL parse the response into a Video_Script dataclass
6. THE system prompt SHALL instruct the LLM to preserve the original narration content from the raw script without adding or removing substantive content

### Requirement 3: Video Script Structure

**User Story:** As a downstream consumer, I want scripts in a structured scene-by-scene format, so that the Asset Orchestrator can render each scene directly.

#### Acceptance Criteria

1. THE Video_Script SHALL contain a title, a list of 5 to 10 Scene_Blocks, and metadata including a generation timestamp
2. EACH Scene_Block SHALL contain a scene_number (integer), narration_text (string), and a Visual_Instruction (dict with keys: type, title, data)
3. THE Visual_Instruction type field SHALL contain one of: bar_chart, line_chart, pie_chart, code_snippet, text_overlay
4. THE Visual_Instruction data field SHALL conform to the Asset Orchestrator expected format: labels and values lists for chart types, code and language strings for code_snippet, and text string for text_overlay

### Requirement 4: Visual Instruction Validation

**User Story:** As a system operator, I want visual instructions validated before reaching the Asset Orchestrator, so that rendering failures are caught early.

#### Acceptance Criteria

1. THE Script_Converter SHALL validate each Visual_Instruction against the Asset Orchestrator schema before returning the Video_Script
2. WHEN a Visual_Instruction of type bar_chart or line_chart is validated, THE Validator SHALL verify that data contains labels (list of strings) and values (list of numbers) of equal length
3. WHEN a Visual_Instruction of type pie_chart is validated, THE Validator SHALL verify that data contains labels (list of strings) and values (list of positive numbers) of equal length
4. WHEN a Visual_Instruction of type code_snippet is validated, THE Validator SHALL verify that data contains code (non-empty string) and language (string)
5. WHEN a Visual_Instruction of type text_overlay is validated, THE Validator SHALL verify that data contains text (non-empty string)
6. WHEN a Visual_Instruction contains a type not in the valid set, THE Validator SHALL return a violation identifying the invalid type

### Requirement 5: Script Serialization and Deserialization

**User Story:** As a downstream consumer, I want to save and load scripts as JSON, so that I can persist scripts and pass them between pipeline stages.

#### Acceptance Criteria

1. THE Script_Serializer SHALL convert a Video_Script dataclass to a JSON string
2. THE Script_Serializer SHALL convert a JSON string back to a Video_Script dataclass
3. FOR ALL valid Video_Script objects, serializing then deserializing SHALL produce an equivalent Video_Script object (round-trip property)
4. WHEN a JSON string contains invalid or missing fields, THE Script_Serializer SHALL raise a ParseError with a description of the violation
5. THE Script_Serializer SHALL format timestamps in ISO 8601 format

### Requirement 6: Error Handling and Retry

**User Story:** As a system operator, I want robust error handling, so that LLM conversion failures do not crash the pipeline.

#### Acceptance Criteria

1. WHEN the LLM response cannot be parsed into a valid Video_Script, THE Script_Converter SHALL retry once with an error-correction prompt that includes the parse error details
2. WHEN the retry also fails to produce a valid Video_Script, THE Script_Converter SHALL raise a ParseError with a description of both failures
3. WHEN the LLM API returns a non-retryable error (e.g., 400 bad request), THE LLM_Client SHALL raise an LLMError with the error details
4. WHEN any component raises an exception, THE Script_Converter SHALL log the full error context including the raw script length and error type
5. IF the LLM API key is missing or invalid, THEN THE LLM_Client SHALL raise an AuthenticationError with a descriptive message at initialization

### Requirement 7: Configuration

**User Story:** As a system operator, I want the Script Converter configurable via environment variables, so that I can adjust behavior without code changes.

#### Acceptance Criteria

1. THE Script_Converter SHALL read the LLM API key from the environment variable OPENAI_API_KEY
2. THE Script_Converter SHALL accept a configurable LLM model name, defaulting to gpt-4o-mini
3. THE Script_Converter SHALL accept a configurable log level, defaulting to INFO
4. THE Script_Converter SHALL validate configuration values at initialization and raise a ValidationError for invalid values

### Requirement 8: Logging and Observability

**User Story:** As a system operator, I want detailed logging, so that I can monitor script conversions and debug issues.

#### Acceptance Criteria

1. THE Script_Converter SHALL log each conversion request with the raw script length in characters
2. THE Script_Converter SHALL log LLM API calls with model name, prompt token count, and completion token count
3. WHEN errors occur, THE Script_Converter SHALL log at ERROR level with full context
4. THE Script_Converter SHALL support configurable log levels: DEBUG, INFO, WARNING, ERROR
