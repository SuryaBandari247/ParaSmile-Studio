# Requirements Document

## Introduction

The Asset Orchestrator is a Python module that transforms visual instructions from video scripts into production-ready video assets. It sits between the Script Generator (upstream) and the final video assembly pipeline (downstream) in the Faceless Technical Media Engine. The module maps textual visual instructions to Manim Scene classes for code-generated animations, provides reusable templates for technical data visualizations (bar charts, line charts, etc.), and wraps FFmpeg for compositing audio tracks with rendered MP4 animations into final video segments. All visuals are code-generated — no generic AI stock footage.

## Glossary

- **Asset_Orchestrator**: The main Python module responsible for converting visual instructions into rendered video assets
- **Visual_Instruction**: A structured directive from a video script describing what animation or visualization to produce (e.g., "bar_chart: AWS Outage impact by region")
- **Scene_Mapper**: The component that parses Visual_Instructions and maps them to the appropriate Manim Scene class
- **Manim_Scene**: A Manim Scene subclass that renders a specific animation or data visualization to MP4
- **Chart_Template**: A reusable Manim Scene subclass for rendering technical data charts (bar charts, line charts, pie charts)
- **FFmpeg_Wrapper**: The component that invokes FFmpeg to combine audio files with MP4 animations into final video segments
- **Scene_Registry**: A dictionary mapping visual instruction types (e.g., "bar_chart", "line_chart") to their corresponding Manim Scene classes
- **Render_Config**: Configuration parameters for Manim rendering including resolution (1080p), frame rate (30fps), and output format (MP4)
- **Composition_Config**: Configuration parameters for FFmpeg audio/video composition including codec, bitrate, and sync settings

## Requirements

### Requirement 1: Visual Instruction Parsing

**User Story:** As a pipeline operator, I want visual instructions from scripts parsed into structured data, so that the correct Manim Scene can be selected for each instruction.

#### Acceptance Criteria

1. THE Scene_Mapper SHALL accept Visual_Instructions as structured dictionaries with keys: type, title, data, and style
2. WHEN a Visual_Instruction is received, THE Scene_Mapper SHALL validate that the type field matches a registered scene type in the Scene_Registry
3. IF a Visual_Instruction contains an unrecognized type, THEN THE Scene_Mapper SHALL raise an UnknownSceneTypeError with the invalid type name and a list of valid types
4. THE Scene_Mapper SHALL support the following instruction types: "bar_chart", "line_chart", "pie_chart", "code_snippet", and "text_overlay"
5. WHEN a Visual_Instruction is missing required fields, THE Scene_Mapper SHALL raise a ValidationError specifying which fields are missing


### Requirement 2: Scene Registry and Mapping

**User Story:** As a pipeline operator, I want visual instruction types mapped to Manim Scene classes, so that the correct animation is rendered for each instruction.

#### Acceptance Criteria

1. THE Scene_Registry SHALL maintain a mapping from instruction type strings to Manim Scene class references
2. WHEN a valid Visual_Instruction is provided, THE Scene_Mapper SHALL return an instantiated Manim_Scene configured with the instruction's data and style parameters
3. THE Scene_Registry SHALL allow registration of new scene types at runtime via a register method
4. WHEN a scene type is registered with a key that already exists, THE Scene_Registry SHALL raise a DuplicateSceneTypeError
5. THE Scene_Mapper SHALL pass the title, data, and style fields from the Visual_Instruction to the Manim_Scene constructor

### Requirement 3: Technical Data Chart Templates

**User Story:** As a content producer, I want reusable Manim templates for technical data charts, so that I can generate consistent, code-based visualizations for video content.

#### Acceptance Criteria

1. THE Chart_Template SHALL render bar charts with labeled axes, a title, and data bars with values displayed above each bar
2. THE Chart_Template SHALL render line charts with labeled axes, a title, data points, and connecting lines
3. THE Chart_Template SHALL render pie charts with labeled segments, a title, and percentage values
4. WHEN data contains more than 10 categories, THE Chart_Template SHALL group the smallest categories into an "Other" segment
5. THE Chart_Template SHALL apply a consistent dark-background color scheme suitable for video production (dark gray background, white text, accent colors for data)
6. THE Chart_Template SHALL render all animations at 1080p resolution (1920x1080) and 30fps frame rate
7. WHEN a chart title exceeds 60 characters, THE Chart_Template SHALL truncate the title and append an ellipsis
8. THE Chart_Template SHALL output rendered animations as MP4 files to a configurable output directory

### Requirement 4: Manim Scene Rendering

**User Story:** As a pipeline operator, I want Manim Scenes rendered to MP4 files, so that the animations can be composed with audio in the final video.

#### Acceptance Criteria

1. WHEN a Manim_Scene is rendered, THE Asset_Orchestrator SHALL output an MP4 file at 1080p resolution (1920x1080) and 30fps
2. THE Asset_Orchestrator SHALL write rendered MP4 files to a configurable output directory with filenames derived from the Visual_Instruction type and title
3. IF Manim rendering fails, THEN THE Asset_Orchestrator SHALL raise a RenderError with the Manim error output and the Visual_Instruction that caused the failure
4. WHEN rendering is complete, THE Asset_Orchestrator SHALL return the absolute file path of the rendered MP4
5. THE Asset_Orchestrator SHALL sanitize Visual_Instruction titles for use in filenames by replacing non-alphanumeric characters with underscores

### Requirement 5: FFmpeg Audio/Video Composition

**User Story:** As a pipeline operator, I want to combine an audio file with an MP4 animation into a single video file, so that narration and visuals are synchronized in the final output.

#### Acceptance Criteria

1. THE FFmpeg_Wrapper SHALL accept an audio file path and an MP4 video file path as inputs and produce a single composed MP4 output
2. WHEN the audio track is longer than the video track, THE FFmpeg_Wrapper SHALL loop the video to match the audio duration
3. WHEN the video track is longer than the audio track, THE FFmpeg_Wrapper SHALL trim the video to match the audio duration
4. THE FFmpeg_Wrapper SHALL preserve the original video resolution (1080p) and frame rate (30fps) in the composed output
5. IF the audio file does not exist at the provided path, THEN THE FFmpeg_Wrapper SHALL raise a FileNotFoundError with the missing file path
6. IF the video file does not exist at the provided path, THEN THE FFmpeg_Wrapper SHALL raise a FileNotFoundError with the missing file path
7. IF FFmpeg is not installed or not found on the system PATH, THEN THE FFmpeg_Wrapper SHALL raise an EnvironmentError with instructions to install FFmpeg
8. WHEN composition is complete, THE FFmpeg_Wrapper SHALL return the absolute file path of the composed MP4 file
9. THE FFmpeg_Wrapper SHALL use the H.264 video codec and AAC audio codec for the composed output

### Requirement 6: FFmpeg Composition Configuration

**User Story:** As a pipeline operator, I want to configure FFmpeg composition parameters, so that I can control output quality and format.

#### Acceptance Criteria

1. THE FFmpeg_Wrapper SHALL accept a Composition_Config with configurable video bitrate, audio bitrate, and output codec
2. WHEN no Composition_Config is provided, THE FFmpeg_Wrapper SHALL use defaults: H.264 video codec, AAC audio codec, 5 Mbps video bitrate, 192 kbps audio bitrate
3. WHERE a custom output path is specified, THE FFmpeg_Wrapper SHALL write the composed file to that path
4. WHEN the output directory does not exist, THE FFmpeg_Wrapper SHALL create the directory before writing

### Requirement 7: Visual Instruction Serialization

**User Story:** As a pipeline operator, I want Visual_Instructions serialized to and from JSON, so that they can be passed between pipeline stages.

#### Acceptance Criteria

1. THE Scene_Mapper SHALL serialize Visual_Instructions to JSON format
2. THE Scene_Mapper SHALL deserialize JSON strings into Visual_Instruction dictionaries
3. FOR ALL valid Visual_Instructions, serializing then deserializing SHALL produce an equivalent Visual_Instruction (round-trip property)
4. WHEN deserializing invalid JSON, THE Scene_Mapper SHALL raise a ParseError with the position of the syntax error

### Requirement 8: Error Handling and Resilience

**User Story:** As a pipeline operator, I want robust error handling, so that failures in one asset do not block the entire pipeline.

#### Acceptance Criteria

1. WHEN processing a batch of Visual_Instructions, THE Asset_Orchestrator SHALL continue processing remaining instructions when a single instruction fails
2. WHEN any component raises an exception, THE Asset_Orchestrator SHALL log the full stack trace with the Visual_Instruction context
3. THE Asset_Orchestrator SHALL return a summary of successful and failed renders after batch processing
4. IF a temporary file is created during rendering, THEN THE Asset_Orchestrator SHALL clean up the temporary file when rendering fails

### Requirement 9: Logging and Observability

**User Story:** As a pipeline operator, I want detailed logging, so that I can debug rendering issues and monitor asset production.

#### Acceptance Criteria

1. THE Asset_Orchestrator SHALL log each Visual_Instruction received with its type and title
2. THE Asset_Orchestrator SHALL log rendering start and completion with elapsed time in milliseconds
3. THE Asset_Orchestrator SHALL log FFmpeg composition commands before execution
4. WHEN errors occur, THE Asset_Orchestrator SHALL log at ERROR level with full context including the Visual_Instruction and error details
5. THE Asset_Orchestrator SHALL support configurable log levels: DEBUG, INFO, WARNING, ERROR
