"""Configuration for the Voice Synthesizer module."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

from voice_synthesizer.exceptions import ValidationError


@dataclass
class VoiceConfig:
    """Configuration for the Voice Synthesizer.

    Supports four TTS backends:
    - "fishspeech" (default): Local Fish Speech server (no API key needed)
    - "fishaudio": Fish Audio cloud API (requires FISH_API_KEY)
    - "coqui_xtts": Local Coqui XTTS-v2 (no API key, pip install TTS)
    - "elevenlabs": ElevenLabs cloud API (requires ELEVENLABS_API_KEY)
    """

    # TTS backend selection
    tts_backend: str = "fishspeech"  # "fishspeech", "fishaudio", "elevenlabs", or "coqui_xtts"

    # Fish Speech local server settings
    fish_speech_url: str = "http://localhost:8080"

    # Fish Audio / Fish Speech shared settings
    fish_api_key: str = ""
    fish_reference_id: str | None = None     # Voice model ID on fish.audio
    fish_ref_audio_path: str | None = None   # Path to reference WAV for inline cloning
    fish_ref_audio_text: str | None = None   # Transcript of reference audio
    fish_speed: float = 0.9                  # Speed factor (0.5–2.0)
    fish_volume: float = 0.0                 # Volume adjustment in dB (-20.0 to 20.0)
    fish_format: str = "mp3"                 # "mp3", "wav", "pcm", "opus"
    fish_mp3_bitrate: int = 128              # 64, 128, or 192
    fish_latency: str = "balanced"           # "normal" or "balanced"
    fish_temperature: float = 0.7            # 0.0–1.0
    fish_top_p: float = 0.7                  # 0.0–1.0
    fish_chunk_length: int = 200             # 100–300

    # ElevenLabs settings (optional, for backward compat)
    elevenlabs_api_key: str = ""
    voice_id: str = "21m00Tcm4TlvDq8ikWAM"  # "Rachel" default
    model_id: str = "eleven_multilingual_v2"

    # Voice tuning (ElevenLabs only)
    stability: float = 0.5
    similarity_boost: float = 0.75
    style: float = 0.0

    # Pacing
    sentence_pause_ms: int = 500
    paragraph_pause_ms: int = 1000

    # Coqui XTTS-v2 settings
    coqui_language: str = "en"
    coqui_gpu: bool = True

    speaking_rate: str = "medium"

    # Filler injection
    filler_enabled: bool = True
    filler_density: float = 0.15
    restart_probability: float = 0.05
    min_thinking_pause_ms: int = 150
    max_thinking_pause_ms: int = 500
    filler_seed: int | None = None
    filler_vocabulary: list[str] | None = None

    # Output
    output_format: str = "mp3_44100_128"
    output_dir: str = "output/audio"
    log_level: str = "INFO"

    def __post_init__(self) -> None:
        load_dotenv()

        # Load TTS backend from env if not set via constructor
        env_backend = os.getenv("TTS_BACKEND", "")
        if env_backend and self.tts_backend == "fishspeech":
            self.tts_backend = env_backend

        # Fish Speech local server URL from env
        env_url = os.getenv("FISH_SPEECH_URL", "")
        if env_url and self.fish_speech_url == "http://localhost:8080":
            self.fish_speech_url = env_url

        # Fish Audio env overrides
        if not self.fish_api_key:
            self.fish_api_key = os.getenv("FISH_API_KEY", "")
        env_ref_id = os.getenv("FISH_REFERENCE_ID")
        if env_ref_id and self.fish_reference_id is None:
            self.fish_reference_id = env_ref_id
        if self.fish_ref_audio_path is None:
            self.fish_ref_audio_path = os.getenv("FISH_REF_AUDIO_PATH") or None
        if self.fish_ref_audio_text is None:
            self.fish_ref_audio_text = os.getenv("FISH_REF_AUDIO_TEXT") or None
        env_speed = os.getenv("FISH_SPEED")
        if env_speed and self.fish_speed == 0.9:
            self.fish_speed = float(env_speed)
        env_temp = os.getenv("FISH_TEMPERATURE")
        if env_temp and self.fish_temperature == 0.7:
            self.fish_temperature = float(env_temp)

        # ElevenLabs API key from env (only needed for elevenlabs backend)
        if not self.elevenlabs_api_key:
            self.elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY", "")

        # Coqui XTTS env overrides
        env_coqui_lang = os.getenv("COQUI_LANGUAGE")
        if env_coqui_lang:
            self.coqui_language = env_coqui_lang
        env_coqui_gpu = os.getenv("COQUI_GPU")
        if env_coqui_gpu is not None:
            self.coqui_gpu = env_coqui_gpu.lower() not in ("0", "false", "no")

        # ElevenLabs voice ID from env
        env_voice_id = os.getenv("ELEVENLABS_VOICE_ID", "")
        if env_voice_id and self.voice_id == "21m00Tcm4TlvDq8ikWAM":
            self.voice_id = env_voice_id

        # Validate Fish Audio settings
        if not (0.5 <= self.fish_speed <= 2.0):
            raise ValidationError(
                f"fish_speed must be between 0.5 and 2.0, got {self.fish_speed}"
            )
        if not (-20.0 <= self.fish_volume <= 20.0):
            raise ValidationError(
                f"fish_volume must be between -20.0 and 20.0, got {self.fish_volume}"
            )
        if not (0.0 <= self.fish_temperature <= 1.0):
            raise ValidationError(
                f"fish_temperature must be between 0.0 and 1.0, got {self.fish_temperature}"
            )
        if not (0.0 <= self.fish_top_p <= 1.0):
            raise ValidationError(
                f"fish_top_p must be between 0.0 and 1.0, got {self.fish_top_p}"
            )
        if not (100 <= self.fish_chunk_length <= 300):
            raise ValidationError(
                f"fish_chunk_length must be between 100 and 300, got {self.fish_chunk_length}"
            )
        if self.fish_format not in ("mp3", "wav", "pcm", "opus"):
            raise ValidationError(
                f"fish_format must be mp3, wav, pcm, or opus, got {self.fish_format}"
            )

        # Validate ElevenLabs float ranges (still needed for backward compat)
        for name, value in [
            ("stability", self.stability),
            ("similarity_boost", self.similarity_boost),
            ("style", self.style),
        ]:
            if not (0.0 <= value <= 1.0):
                raise ValidationError(
                    f"{name} must be between 0.0 and 1.0, got {value}"
                )

        for name, value in [
            ("filler_density", self.filler_density),
            ("restart_probability", self.restart_probability),
        ]:
            if not (0.0 <= value <= 1.0):
                raise ValidationError(
                    f"{name} must be between 0.0 and 1.0, got {value}"
                )
