"""Custom exceptions for the Voice Synthesizer module."""


class VoiceSynthesizerError(Exception):
    """Base exception for all voice synthesizer errors."""


class AuthenticationError(VoiceSynthesizerError):
    """Raised when ELEVENLABS_API_KEY is missing or invalid."""


class SynthesisError(VoiceSynthesizerError):
    """Raised when ElevenLabs API returns an error after retries."""

    def __init__(self, scene_number: int, message: str):
        self.scene_number = scene_number
        super().__init__(f"Scene {scene_number}: {message}")


class NetworkError(VoiceSynthesizerError):
    """Raised when network connectivity fails after retries."""


class ValidationError(VoiceSynthesizerError):
    """Raised for invalid configuration values."""
