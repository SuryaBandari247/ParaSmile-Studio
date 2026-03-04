"""Coqui XTTS-v2 TTS client — local inference via the TTS library.

XTTS-v2 is a multilingual text-to-speech model with voice cloning from
a short reference audio clip.  It runs locally on GPU (MPS/CUDA) with
no API costs.

Requires: pip install coqui-tts
Also install PyTorch separately first: pip install torch torchaudio
Model downloads automatically on first use (~1.8GB).
"""

from __future__ import annotations

import logging
import os
import tempfile

from voice_synthesizer.exceptions import SynthesisError

logger = logging.getLogger(__name__)


class CoquiXTTSClient:
    """TTS client using Coqui XTTS-v2 for local voice synthesis."""

    def __init__(
        self,
        ref_audio_path: str | None = None,
        language: str = "en",
        output_format: str = "wav",
        output_dir: str = "output/audio",
        gpu: bool = True,
    ):
        self.ref_audio_path = ref_audio_path
        self.language = language
        self.output_format = output_format
        self.output_dir = output_dir
        self.gpu = gpu
        self._tts = None

        logger.info(
            "CoquiXTTSClient initialized (ref=%s, lang=%s, gpu=%s)",
            ref_audio_path or "none", language, gpu,
        )

    def _get_tts(self):
        """Lazy-load the TTS model (downloads on first use)."""
        if self._tts is None:
            # Patch transformers compatibility — transformers 5.x removed
            # isin_mps_friendly which coqui-tts's tortoise layer imports.
            try:
                from transformers import pytorch_utils
                if not hasattr(pytorch_utils, "isin_mps_friendly"):
                    import torch
                    pytorch_utils.isin_mps_friendly = torch.isin
            except Exception:
                pass

            try:
                from TTS.api import TTS
            except ImportError as exc:
                raise SynthesisError(
                    0, "Coqui TTS not installed. Run: pip install coqui-tts"
                ) from exc

            self._tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
            if self.gpu:
                self._tts = self._tts.to("mps" if _is_mps_available() else "cuda")
            logger.info("XTTS-v2 model loaded (gpu=%s)", self.gpu)
        return self._tts

    def synthesize(self, text: str, scene_number: int = 0) -> str:
        """Generate speech from text using XTTS-v2.

        Args:
            text: Plain narration text.
            scene_number: Scene number for file naming.

        Returns:
            Absolute path to the generated audio file.
        """
        os.makedirs(self.output_dir, exist_ok=True)
        filename = f"scene_{scene_number:03d}.{self.output_format}"
        output_path = os.path.join(self.output_dir, filename)

        tts = self._get_tts()

        try:
            if self.ref_audio_path and os.path.isfile(self.ref_audio_path):
                tts.tts_to_file(
                    text=text,
                    speaker_wav=self.ref_audio_path,
                    language=self.language,
                    file_path=output_path,
                )
            else:
                # No reference — use default speaker
                tts.tts_to_file(
                    text=text,
                    language=self.language,
                    file_path=output_path,
                )
        except Exception as exc:
            raise SynthesisError(
                scene_number, f"XTTS-v2 synthesis failed: {exc}"
            ) from exc

        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise SynthesisError(scene_number, "XTTS-v2 produced empty output")

        return os.path.abspath(output_path)


def _is_mps_available() -> bool:
    """Check if Apple MPS (Metal) is available."""
    try:
        import torch
        return torch.backends.mps.is_available()
    except Exception:
        return False
