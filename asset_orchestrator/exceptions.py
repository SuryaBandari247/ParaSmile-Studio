"""Custom exception hierarchy for the Asset Orchestrator module."""


class AssetOrchestratorError(Exception):
    """Base exception for all asset orchestrator errors."""
    pass


class ValidationError(AssetOrchestratorError):
    """Raised when a Visual_Instruction is missing required fields."""

    def __init__(self, missing_fields: list[str]):
        self.missing_fields = missing_fields
        super().__init__(f"Missing required fields: {', '.join(missing_fields)}")


class UnknownSceneTypeError(AssetOrchestratorError):
    """Raised when instruction type is not in the Scene Registry."""

    def __init__(self, invalid_type: str, valid_types: list[str]):
        self.invalid_type = invalid_type
        self.valid_types = valid_types
        super().__init__(
            f"Unknown scene type '{invalid_type}'. "
            f"Valid types: {', '.join(valid_types)}"
        )


class DuplicateSceneTypeError(AssetOrchestratorError):
    """Raised when registering a scene type that already exists."""

    def __init__(self, type_key: str):
        self.type_key = type_key
        super().__init__(f"Scene type '{type_key}' is already registered")


class RenderError(AssetOrchestratorError):
    """Raised when Manim rendering fails."""

    def __init__(self, error_output: str, instruction: dict):
        self.error_output = error_output
        self.instruction = instruction
        super().__init__(f"Render failed: {error_output}")


class CompositionError(AssetOrchestratorError):
    """Raised when FFmpeg composition fails."""

    def __init__(self, error_output: str, command: str):
        self.error_output = error_output
        self.command = command
        super().__init__(f"FFmpeg composition failed: {error_output}")


class ParseError(AssetOrchestratorError):
    """Raised when JSON deserialization fails."""

    def __init__(self, position: int, message: str):
        self.position = position
        super().__init__(f"JSON parse error at position {position}: {message}")


class ConfigurationError(AssetOrchestratorError):
    """Raised when required configuration (API keys, etc.) is missing."""

    def __init__(self, key_name: str, message: str = ""):
        self.key_name = key_name
        msg = f"Missing required configuration: {key_name}"
        if message:
            msg += f". {message}"
        super().__init__(msg)


class StockFootageError(AssetOrchestratorError):
    """Raised when stock footage search or download fails."""

    def __init__(self, message: str, query: str = ""):
        self.query = query
        super().__init__(f"Stock footage error: {message}")
