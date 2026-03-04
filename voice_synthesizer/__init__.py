"""
Voice Synthesizer — Converts VideoScript narrations to production-ready audio.

Supports three TTS backends:
- Fish Speech (default): Local server, zero cost, same quality
- Fish Audio: Cloud API with voice cloning and prosody control
- ElevenLabs: Cloud API with SSML pacing control

Generates narration with conversational filler injection and natural pacing.
Outputs per-scene audio files with an AudioManifest for downstream composition.
"""

__version__ = "0.4.0"

from voice_synthesizer.synthesizer import VoiceSynthesizer
from voice_synthesizer.config import VoiceConfig
from voice_synthesizer.models import SceneAudio, AudioManifest
from voice_synthesizer.ssml_builder import SSMLBuilder
from voice_synthesizer.filler_injector import FillerInjector
from voice_synthesizer.fish_speech_client import FishSpeechClient
from voice_synthesizer.fish_audio_client import FishAudioClient
from voice_synthesizer.elevenlabs_client import ElevenLabsClient
from voice_synthesizer.exceptions import (
    VoiceSynthesizerError,
    AuthenticationError,
    SynthesisError,
    NetworkError,
    ValidationError,
)

__all__ = [
    "VoiceSynthesizer",
    "VoiceConfig",
    "SceneAudio",
    "AudioManifest",
    "SSMLBuilder",
    "FillerInjector",
    "FishSpeechClient",
    "FishAudioClient",
    "ElevenLabsClient",
    "VoiceSynthesizerError",
    "AuthenticationError",
    "SynthesisError",
    "NetworkError",
    "ValidationError",
]
