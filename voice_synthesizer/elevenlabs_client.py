"""ElevenLabs TTS API client."""

from __future__ import annotations

import logging
import time

import requests

from voice_synthesizer.exceptions import (
    AuthenticationError,
    NetworkError,
    SynthesisError,
)

logger = logging.getLogger(__name__)


class ElevenLabsClient:
    """Thin wrapper around the ElevenLabs Text-to-Speech API."""

    BASE_URL = "https://api.elevenlabs.io/v1"
    SUPPORTED_FORMATS = {
        "mp3_44100_128",
        "mp3_44100_192",
        "pcm_16000",
        "pcm_24000",
    }
    MAX_RETRIES = 3
    BACKOFF_DELAYS = [1, 2, 4]  # seconds

    def __init__(
        self,
        api_key: str,
        voice_id: str = "21m00Tcm4TlvDq8ikWAM",
        model_id: str = "eleven_multilingual_v2",
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        style: float = 0.0,
        output_format: str = "mp3_44100_128",
    ):
        if not api_key:
            raise AuthenticationError(
                "ELEVENLABS_API_KEY is missing or empty. "
                "Set it in your .env file or pass it directly."
            )
        self.api_key = api_key
        self.voice_id = voice_id
        self.model_id = model_id
        self.stability = stability
        self.similarity_boost = similarity_boost
        self.style = style
        self.output_format = output_format

    def synthesize(self, ssml_text: str, scene_number: int = 0) -> bytes:
        """Synthesize SSML text to audio bytes.

        Args:
            ssml_text: SSML-annotated narration text.
            scene_number: Scene number for error context.

        Returns:
            Raw audio bytes.

        Raises:
            SynthesisError: After retry exhaustion on API errors.
            NetworkError: After retry exhaustion on connectivity failures.
        """
        return self._call_api(ssml_text, scene_number)

    def _call_api(self, ssml_text: str, scene_number: int) -> bytes:
        """Make HTTP request with retry logic for rate limits."""
        url = f"{self.BASE_URL}/text-to-speech/{self.voice_id}"
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }
        payload = {
            "text": ssml_text,
            "model_id": self.model_id,
            "voice_settings": {
                "stability": self.stability,
                "similarity_boost": self.similarity_boost,
                "style": self.style,
            },
        }
        params = {"output_format": self.output_format}

        last_error: Exception | None = None
        for attempt in range(self.MAX_RETRIES):
            try:
                response = requests.post(
                    url,
                    json=payload,
                    headers=headers,
                    params=params,
                    timeout=60,
                )

                if response.status_code == 200:
                    return response.content

                if response.status_code == 429:
                    delay = self.BACKOFF_DELAYS[attempt] if attempt < len(self.BACKOFF_DELAYS) else 4
                    logger.warning(
                        "Rate limited (429), retrying in %ds (attempt %d/%d)",
                        delay, attempt + 1, self.MAX_RETRIES,
                    )
                    time.sleep(delay)
                    last_error = SynthesisError(
                        scene_number,
                        f"Rate limited (HTTP 429): {response.text}",
                    )
                    continue

                # Non-retryable API error
                raise SynthesisError(
                    scene_number,
                    f"ElevenLabs API error (HTTP {response.status_code}): {response.text}",
                )

            except requests.ConnectionError as exc:
                delay = self.BACKOFF_DELAYS[attempt] if attempt < len(self.BACKOFF_DELAYS) else 4
                logger.warning(
                    "Connection error, retrying in %ds (attempt %d/%d): %s",
                    delay, attempt + 1, self.MAX_RETRIES, exc,
                )
                time.sleep(delay)
                last_error = exc
            except requests.Timeout as exc:
                delay = self.BACKOFF_DELAYS[attempt] if attempt < len(self.BACKOFF_DELAYS) else 4
                logger.warning(
                    "Timeout, retrying in %ds (attempt %d/%d): %s",
                    delay, attempt + 1, self.MAX_RETRIES, exc,
                )
                time.sleep(delay)
                last_error = exc
            except SynthesisError:
                raise

        # All retries exhausted
        if isinstance(last_error, (requests.ConnectionError, requests.Timeout)):
            raise NetworkError(
                f"Network error after {self.MAX_RETRIES} retries: {last_error}"
            ) from last_error
        if isinstance(last_error, SynthesisError):
            raise last_error
        raise SynthesisError(scene_number, f"Failed after {self.MAX_RETRIES} retries")
