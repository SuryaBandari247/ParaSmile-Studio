"""Audio Splitter — transcribe master audio with Whisper, align to script scenes, split."""

from __future__ import annotations

import logging
import os
import subprocess
from dataclasses import dataclass
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


@dataclass
class WordTimestamp:
    word: str
    start: float
    end: float


@dataclass
class SceneBoundary:
    scene_number: int
    narration_text: str
    start_time: float
    end_time: float
    audio_path: str | None = None


def transcribe_with_timestamps(
    audio_path: str,
    model_size: str = "base",
    device: str = "auto",
) -> list[WordTimestamp]:
    """Transcribe audio and return word-level timestamps using faster-whisper."""
    from faster_whisper import WhisperModel

    logger.info("Loading Whisper model '%s' (device=%s)...", model_size, device)
    compute_type = "int8" if device == "cpu" else "auto"
    model = WhisperModel(model_size, device=device, compute_type=compute_type)

    logger.info("Transcribing %s ...", audio_path)
    segments, _info = model.transcribe(audio_path, word_timestamps=True)

    words: list[WordTimestamp] = []
    for segment in segments:
        if segment.words:
            for w in segment.words:
                words.append(WordTimestamp(word=w.word.strip(), start=w.start, end=w.end))

    logger.info("Transcribed %d words (%.1fs - %.1fs)",
                len(words), words[0].start if words else 0, words[-1].end if words else 0)
    return words


def _normalize(text: str) -> str:
    """Lowercase, strip punctuation for fuzzy matching."""
    import re
    return re.sub(r"[^\w\s]", "", text.lower()).strip()


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalize(a), _normalize(b)).ratio()


def align_to_scenes(
    words: list[WordTimestamp],
    scene_narrations: list[tuple[int, str]],
) -> list[SceneBoundary]:
    """Align word-level transcript to script scenes using sliding-window text similarity.

    Args:
        words: Word-level timestamps from Whisper.
        scene_narrations: List of (scene_number, narration_text) in order.

    Returns:
        List of SceneBoundary with start/end times for each scene.
    """
    if not words or not scene_narrations:
        return []

    boundaries: list[SceneBoundary] = []
    word_idx = 0
    total_words = len(words)

    for i, (scene_num, narration) in enumerate(scene_narrations):
        narration_words = _normalize(narration).split()
        target_len = len(narration_words)

        if target_len == 0:
            continue

        # For the last scene, consume all remaining words
        if i == len(scene_narrations) - 1:
            if word_idx < total_words:
                boundaries.append(SceneBoundary(
                    scene_number=scene_num,
                    narration_text=narration,
                    start_time=words[word_idx].start,
                    end_time=words[-1].end,
                ))
            continue

        # Sliding window: find the best-matching end position
        best_score = -1.0
        best_end = min(word_idx + target_len, total_words)

        # Search window: target_len ± 40%
        search_min = max(word_idx + max(1, int(target_len * 0.6)), word_idx + 1)
        search_max = min(word_idx + int(target_len * 1.4) + 1, total_words + 1)

        for end in range(search_min, search_max):
            candidate = " ".join(w.word for w in words[word_idx:end])
            score = _similarity(narration, candidate)
            if score > best_score:
                best_score = score
                best_end = end

        start_time = words[word_idx].start if word_idx < total_words else 0.0
        end_time = words[min(best_end - 1, total_words - 1)].end

        boundaries.append(SceneBoundary(
            scene_number=scene_num,
            narration_text=narration,
            start_time=start_time,
            end_time=end_time,
        ))

        logger.debug("Scene %d: words[%d:%d] (%.1fs-%.1fs) score=%.2f",
                      scene_num, word_idx, best_end, start_time, end_time, best_score)
        word_idx = best_end

    return boundaries


def split_audio(
    audio_path: str,
    boundaries: list[SceneBoundary],
    output_dir: str,
) -> list[SceneBoundary]:
    """Split master audio into per-scene files using ffmpeg.

    Returns updated boundaries with audio_path populated.
    """
    os.makedirs(output_dir, exist_ok=True)
    results: list[SceneBoundary] = []

    for b in boundaries:
        out_file = os.path.join(output_dir, f"segment_{b.scene_number:03d}.wav")
        duration = b.end_time - b.start_time

        cmd = [
            "ffmpeg", "-y",
            "-i", audio_path,
            "-ss", f"{b.start_time:.3f}",
            "-t", f"{duration:.3f}",
            "-acodec", "pcm_s16le",
            "-ar", "24000",
            "-ac", "1",
            out_file,
        ]

        logger.info("Splitting scene %d: %.1fs-%.1fs → %s",
                     b.scene_number, b.start_time, b.end_time, out_file)

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error("ffmpeg failed for scene %d: %s", b.scene_number, result.stderr)
            results.append(b)
            continue

        b.audio_path = os.path.abspath(out_file)
        results.append(b)

    return results
