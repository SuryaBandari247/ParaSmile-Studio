"""Fish Audio TTS client — cloud text-to-speech via Fish Audio API."""

from __future__ import annotations

import logging
import os
import time

from voice_synthesizer.exceptions import (
    AuthenticationError,
    NetworkError,
    SynthesisError,
)

logger = logging.getLogger(__name__)


class FishAudioClient:
    """TTS client using the Fish Audio API.

    Generates speech from plain text using Fish Audio's cloud TTS service.
    Supports voice cloning via reference_id or inline reference audio.
    """

    MAX_RETRIES = 3
    BACKOFF_DELAYS = [1, 2, 4]

    def __init__(
        self,
        api_key: str,
        reference_id: str | None = None,
        ref_audio_path: str | None = None,
        ref_audio_text: str | None = None,
        speed: float = 1.0,
        volume: float = 0.0,
        output_format: str = "mp3",
        mp3_bitrate: int = 128,
        latency: str = "balanced",
        temperature: float = 0.7,
        top_p: float = 0.7,
        chunk_length: int = 200,
        output_dir: str = "output/audio",
    ):
        if not api_key:
            raise AuthenticationError(
                "FISH_API_KEY is missing or empty. "
                "Set it in your .env file or pass it via VoiceConfig."
            )

        self.api_key = api_key
        self.reference_id = reference_id
        self.ref_audio_path = ref_audio_path
        self.ref_audio_text = ref_audio_text
        self.speed = speed
        self.volume = volume
        self.output_format = output_format
        self.mp3_bitrate = mp3_bitrate
        self.latency = latency
        self.temperature = temperature
        self.top_p = top_p
        self.chunk_length = chunk_length
        self.output_dir = output_dir

        self._client = None
        self._config = None

        logger.info(
            "FishAudioClient initialized (ref_id=%s, speed=%.1f, format=%s)",
            reference_id or "none",
            speed,
            output_format,
        )

    def _get_client(self):
        """Lazy-initialize the Fish Audio client."""
        if self._client is None:
            try:
                from fishaudio import FishAudio
                self._client = FishAudio(api_key=self.api_key)
            except ImportError as exc:
                raise SynthesisError(
                    0,
                    "fish-audio-sdk is not installed. Run: pip install fish-audio-sdk",
                ) from exc
        return self._client

    def _get_config(self):
        """Build a reusable TTSConfig."""
        if self._config is None:
            from fishaudio.types import TTSConfig, Prosody

            prosody = Prosody(speed=self.speed, volume=self.volume)

            config_kwargs = {
                "format": self.output_format,
                "mp3_bitrate": self.mp3_bitrate,
                "latency": self.latency,
                "prosody": prosody,
                "temperature": self.temperature,
                "top_p": self.top_p,
                "chunk_length": self.chunk_length,
            }

            if self.reference_id:
                config_kwargs["reference_id"] = self.reference_id

            self._config = TTSConfig(**config_kwargs)
        return self._config

    def _build_references(self) -> list | None:
        """Build inline reference audio list for voice cloning."""
        if not self.ref_audio_path:
            return None

        from fishaudio.types import ReferenceAudio

        with open(self.ref_audio_path, "rb") as f:
            audio_bytes = f.read()

        return [ReferenceAudio(audio=audio_bytes, text=self.ref_audio_text or "")]

    def synthesize(self, text: str, scene_number: int = 0) -> str:
        """Generate speech from plain text using Fish Audio.

        Args:
            text: Plain narration text.
            scene_number: Scene number for file naming.

        Returns:
            Absolute path to the generated audio file.

        Raises:
            SynthesisError: If generation fails after retries.
            NetworkError: If connectivity fails after retries.
        """
        client = self._get_client()
        config = self._get_config()

        os.makedirs(self.output_dir, exist_ok=True)
        ext = "wav" if self.output_format == "wav" else self.output_format
        filename = f"scene_{scene_number:03d}.{ext}"
        output_path = os.path.join(self.output_dir, filename)

        convert_kwargs = {"text": text, "config": config}

        # Add inline references if configured (and no reference_id)
        if not self.reference_id and self.ref_audio_path:
            refs = self._build_references()
            if refs:
                convert_kwargs["references"] = refs

        last_error: Exception | None = None
        for attempt in range(self.MAX_RETRIES):
            try:
                audio = client.tts.convert(**convert_kwargs)

                with open(output_path, "wb") as f:
                    for chunk in audio:
                        f.write(chunk)

                if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                    raise SynthesisError(
                        scene_number,
                        "Fish Audio produced empty output",
                    )

                return os.path.abspath(output_path)

            except SynthesisError:
                raise
            except Exception as exc:
                exc_str = str(exc).lower()
                is_rate_limit = "rate" in exc_str and "limit" in exc_str
                is_network = any(
                    kw in exc_str
                    for kw in ("connection", "timeout", "network", "refused")
                )

                if is_rate_limit or is_network:
                    delay = (
                        self.BACKOFF_DELAYS[attempt]
                        if attempt < len(self.BACKOFF_DELAYS)
                        else 4
                    )
                    logger.warning(
                        "Fish Audio error (attempt %d/%d), retrying in %ds: %s",
                        attempt + 1,
                        self.MAX_RETRIES,
                        delay,
                        exc,
                    )
                    time.sleep(delay)
                    last_error = exc
                    continue

                raise SynthesisError(
                    scene_number,
                    f"Fish Audio TTS failed: {exc}",
                ) from exc

        if last_error:
            raise NetworkError(
                f"Fish Audio failed after {self.MAX_RETRIES} retries: {last_error}"
            ) from last_error
        raise SynthesisError(
            scene_number, f"Failed after {self.MAX_RETRIES} retries"
        )
