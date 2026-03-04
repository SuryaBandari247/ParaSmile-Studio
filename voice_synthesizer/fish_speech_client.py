"""Fish Speech local TTS client — self-hosted inference via HTTP API.

Connects to a locally running Fish Speech server (e.g. via Pinokio or
`python -m tools.api_server --listen 0.0.0.0:8080`).

The local server exposes the same /v1/tts endpoint as the cloud API
but requires no API key and has no usage costs.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
import time

import requests

from voice_synthesizer.exceptions import (
    NetworkError,
    SynthesisError,
)

logger = logging.getLogger(__name__)


class FishSpeechClient:
    """TTS client for a locally running Fish Speech server.

    Sends plain text to the local /v1/tts endpoint and writes the
    streamed audio response to disk.
    """

    MAX_RETRIES = 6
    BACKOFF_DELAYS = [2, 4, 6, 8, 10, 10]

    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        reference_id: str | None = None,
        ref_audio_path: str | None = None,
        ref_audio_text: str | None = None,
        speed: float = 1.0,
        volume: float = 0.0,
        output_format: str = "wav",
        mp3_bitrate: int = 128,
        latency: str = "normal",
        temperature: float = 0.6,
        top_p: float = 0.7,
        repetition_penalty: float = 1.4,
        chunk_length: int = 200,
        output_dir: str = "output/audio",
    ):
        self.base_url = base_url.rstrip("/")
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
        self.repetition_penalty = repetition_penalty
        self.chunk_length = chunk_length
        self.output_dir = output_dir

        logger.info(
            "FishSpeechClient initialized (url=%s, ref_id=%s, format=%s)",
            self.base_url,
            reference_id or "none",
            output_format,
        )

    def synthesize(self, text: str, scene_number: int = 0) -> str:
        """Generate speech from text using the local Fish Speech server.

        Args:
            text: Plain narration text (may include inline emotion tags).
            scene_number: Scene number for file naming.

        Returns:
            Absolute path to the generated audio file.

        Raises:
            SynthesisError: If generation fails after retries.
            NetworkError: If the local server is unreachable after retries.
        """
        os.makedirs(self.output_dir, exist_ok=True)
        ext = self.output_format
        filename = f"scene_{scene_number:03d}.{ext}"
        output_path = os.path.join(self.output_dir, filename)

        payload = self._build_payload(text)

        # Scale timeout based on text length — Fish Speech local runs ~8 tokens/sec
        # Base: 120s for short text, +60s per 200 chars over 200
        base_timeout = 120
        extra_chars = max(0, len(text) - 200)
        timeout = base_timeout + (extra_chars // 200) * 60
        timeout = min(timeout, 300)  # Cap at 5 minutes

        last_error: Exception | None = None
        for attempt in range(self.MAX_RETRIES):
            try:
                resp = requests.post(
                    f"{self.base_url}/v1/tts",
                    json=payload,
                    stream=True,
                    timeout=timeout,
                )

                if resp.status_code != 200:
                    raise SynthesisError(
                        scene_number,
                        f"Fish Speech local server returned HTTP {resp.status_code}: {resp.text[:200]}",
                    )

                with open(output_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

                if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                    raise SynthesisError(
                        scene_number,
                        "Fish Speech produced empty output",
                    )

                # Apply speed adjustment via ffmpeg if not 1.0
                if self.speed != 1.0:
                    self._apply_speed(output_path)

                return os.path.abspath(output_path)

            except SynthesisError:
                raise
            except requests.exceptions.ConnectionError as exc:
                delay = self.BACKOFF_DELAYS[attempt] if attempt < len(self.BACKOFF_DELAYS) else 4
                logger.warning(
                    "Fish Speech server unreachable (attempt %d/%d), retrying in %ds: %s",
                    attempt + 1, self.MAX_RETRIES, delay, exc,
                )
                time.sleep(delay)
                last_error = exc
            except requests.exceptions.ReadTimeout as exc:
                # Timeout — Fish Speech is slow, retry once with longer timeout
                if attempt < 1:
                    logger.warning(
                        "Fish Speech timed out after %ds (attempt %d/%d), retrying with longer timeout: %s",
                        timeout, attempt + 1, self.MAX_RETRIES, exc,
                    )
                    timeout = min(timeout + 120, 420)  # Add 2 more minutes, cap at 7 min
                    time.sleep(2)
                    last_error = exc
                else:
                    raise SynthesisError(
                        scene_number,
                        f"Fish Speech TTS timed out after {timeout}s (text length: {len(text)} chars)",
                    ) from exc
            except Exception as exc:
                raise SynthesisError(
                    scene_number,
                    f"Fish Speech TTS failed: {exc}",
                ) from exc

        if last_error:
            raise NetworkError(
                f"Fish Speech local server unreachable after {self.MAX_RETRIES} retries. "
                f"Is it running at {self.base_url}? Error: {last_error}"
            ) from last_error
        raise SynthesisError(scene_number, f"Failed after {self.MAX_RETRIES} retries")

    def _apply_speed(self, file_path: str) -> None:
        """Apply speed adjustment to audio file using ffmpeg atempo filter.

        The atempo filter accepts values between 0.5 and 2.0.
        For values outside that range, multiple filters are chained.
        """
        if not shutil.which("ffmpeg"):
            logger.warning("ffmpeg not found — skipping speed adjustment")
            return

        # Build atempo filter chain (each filter limited to 0.5–2.0)
        tempo = self.speed
        filters = []
        while tempo < 0.5:
            filters.append("atempo=0.5")
            tempo /= 0.5
        while tempo > 2.0:
            filters.append("atempo=2.0")
            tempo /= 2.0
        filters.append(f"atempo={tempo:.4f}")
        filter_chain = ",".join(filters)

        # Write to temp file then replace original
        fd, tmp_path = tempfile.mkstemp(suffix=os.path.splitext(file_path)[1])
        os.close(fd)
        try:
            cmd = [
                "ffmpeg", "-y", "-i", file_path,
                "-filter:a", filter_chain,
                "-vn", tmp_path,
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=60)
            if result.returncode != 0:
                logger.warning(
                    "ffmpeg speed adjustment failed (rc=%d): %s",
                    result.returncode, result.stderr[:200],
                )
                return
            # Replace original with speed-adjusted version
            shutil.move(tmp_path, file_path)
            logger.info("Applied speed %.2fx to %s", self.speed, file_path)
        except Exception as exc:
            logger.warning("ffmpeg speed adjustment error: %s", exc)
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def _build_payload(self, text: str) -> dict:
        """Build the JSON payload for the local Fish Speech /v1/tts endpoint.

        The local server accepts ServeTTSRequest fields:
        text, chunk_length, format, references, reference_id, seed,
        normalize, streaming, max_new_tokens, top_p, repetition_penalty,
        temperature.
        """
        payload: dict = {
            "text": text,
            "format": self.output_format,
            "chunk_length": min(self.chunk_length, 150),  # Lower = fewer swallowed words
            "normalize": True,
            # Generation quality tuning — uses instance params (overridable per-segment)
            "temperature": self.temperature,
            "top_p": self.top_p,
            "repetition_penalty": self.repetition_penalty,
            "max_new_tokens": 2048,
            "seed": 42,
            "use_memory_cache": "on" if self.reference_id else "off",
        }

        if self.reference_id:
            payload["reference_id"] = self.reference_id

        return payload
