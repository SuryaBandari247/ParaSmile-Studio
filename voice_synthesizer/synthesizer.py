"""Voice Synthesizer — main orchestrator for narration-to-audio conversion."""

from __future__ import annotations

import os
import re

from voice_synthesizer.config import VoiceConfig
from voice_synthesizer.coqui_xtts_client import CoquiXTTSClient
from voice_synthesizer.elevenlabs_client import ElevenLabsClient
from voice_synthesizer.exceptions import AuthenticationError
from voice_synthesizer.fish_audio_client import FishAudioClient
from voice_synthesizer.fish_speech_client import FishSpeechClient
from voice_synthesizer.filler_injector import FillerInjector
from voice_synthesizer.logger import get_logger
from voice_synthesizer.models import AudioManifest, SceneAudio
from voice_synthesizer.ssml_builder import SSMLBuilder


# Regex to strip {{pause:Nms}} markers from text before sending to Fish Audio
_PAUSE_MARKER = re.compile(r"\{\{pause:\d+ms\}\}")


class VoiceSynthesizer:
    """Orchestrates narration-to-audio conversion for a VideoScript.

    Supports three TTS backends:
    - Fish Speech (default): Local server, no API key, zero cost
    - Fish Audio: Cloud API with voice cloning and prosody control
    - ElevenLabs: Cloud API with SSML pacing (requires ELEVENLABS_API_KEY)
    """

    def __init__(self, config: VoiceConfig | None = None):
        self.config = config if config is not None else VoiceConfig()
        self.logger = get_logger("voice_synthesizer", self.config.log_level)

        # Filler injector (shared by both backends)
        self.filler_injector = FillerInjector(
            filler_density=self.config.filler_density,
            restart_probability=self.config.restart_probability,
            min_thinking_pause_ms=self.config.min_thinking_pause_ms,
            max_thinking_pause_ms=self.config.max_thinking_pause_ms,
            filler_vocabulary=self.config.filler_vocabulary,
            seed=self.config.filler_seed,
        ) if self.config.filler_enabled else None

        # Initialize TTS backend
        if self.config.tts_backend == "fishspeech":
            self._init_fishspeech()
        elif self.config.tts_backend == "fishaudio":
            self._init_fishaudio()
        elif self.config.tts_backend == "coqui_xtts":
            self._init_coqui()
        else:
            self._init_elevenlabs()

        self.logger.info(
            "VoiceSynthesizer initialized (backend=%s)", self.config.tts_backend
        )

    def _init_fishspeech(self) -> None:
        """Initialize Fish Speech local backend."""
        self.client = FishSpeechClient(
            base_url=self.config.fish_speech_url,
            reference_id=self.config.fish_reference_id,
            ref_audio_path=self.config.fish_ref_audio_path,
            ref_audio_text=self.config.fish_ref_audio_text,
            speed=self.config.fish_speed,
            volume=self.config.fish_volume,
            output_format=self.config.fish_format,
            mp3_bitrate=self.config.fish_mp3_bitrate,
            latency=self.config.fish_latency,
            temperature=self.config.fish_temperature,
            top_p=self.config.fish_top_p,
            chunk_length=self.config.fish_chunk_length,
            output_dir=self.config.output_dir,
        )
        self.ssml_builder = None

    def _init_fishaudio(self) -> None:
        """Initialize Fish Audio backend."""
        if not self.config.fish_api_key:
            raise AuthenticationError(
                "FISH_API_KEY is missing. "
                "Set it in your .env file or pass it via VoiceConfig."
            )

        self.client = FishAudioClient(
            api_key=self.config.fish_api_key,
            reference_id=self.config.fish_reference_id,
            ref_audio_path=self.config.fish_ref_audio_path,
            ref_audio_text=self.config.fish_ref_audio_text,
            speed=self.config.fish_speed,
            volume=self.config.fish_volume,
            output_format=self.config.fish_format,
            mp3_bitrate=self.config.fish_mp3_bitrate,
            latency=self.config.fish_latency,
            temperature=self.config.fish_temperature,
            top_p=self.config.fish_top_p,
            chunk_length=self.config.fish_chunk_length,
            output_dir=self.config.output_dir,
        )
        self.ssml_builder = None

    def _init_elevenlabs(self) -> None:
        """Initialize ElevenLabs backend."""
        if not self.config.elevenlabs_api_key:
            raise AuthenticationError(
                "ELEVENLABS_API_KEY is missing. "
                "Set it in your .env file or pass it via VoiceConfig."
            )

        self.client = ElevenLabsClient(
            api_key=self.config.elevenlabs_api_key,
            voice_id=self.config.voice_id,
            model_id=self.config.model_id,
            stability=self.config.stability,
            similarity_boost=self.config.similarity_boost,
            style=self.config.style,
            output_format=self.config.output_format,
        )
        self.ssml_builder = SSMLBuilder(
            sentence_pause_ms=self.config.sentence_pause_ms,
            paragraph_pause_ms=self.config.paragraph_pause_ms,
            speaking_rate=self.config.speaking_rate,
        )
    def _init_coqui(self) -> None:
        """Initialize Coqui XTTS-v2 backend."""
        self.client = CoquiXTTSClient(
            ref_audio_path=self.config.fish_ref_audio_path,
            language=self.config.coqui_language,
            output_dir=self.config.output_dir,
            gpu=self.config.coqui_gpu,
        )
        self.ssml_builder = None

    def synthesize(self, video_script) -> AudioManifest:
        """Synthesize narration audio for all scenes in a VideoScript."""
        entries: list[SceneAudio] = []
        total_chars = 0
        scenes_ok = 0
        scenes_fail = 0

        sorted_scenes = sorted(video_script.scenes, key=lambda s: s.scene_number)

        for scene in sorted_scenes:
            narration = scene.narration_text
            sn = scene.scene_number
            emotion = getattr(scene, "emotion", "neutral") or "neutral"

            if not narration or not narration.strip():
                self.logger.warning("Scene %d: empty narration, skipping", sn)
                continue

            char_count = len(narration)
            total_chars += char_count
            self.logger.info("Scene %d: synthesizing (%d chars)", sn, char_count)

            try:
                # 1. Inject fillers (if enabled)
                text = narration
                if self.filler_injector is not None:
                    text = self.filler_injector.inject(text)

                # 2. Synthesize via selected backend
                if self.config.tts_backend in ("fishaudio", "fishspeech"):
                    file_path = self._synthesize_fishaudio(text, sn, emotion)
                elif self.config.tts_backend == "coqui_xtts":
                    file_path = self._synthesize_coqui(text, sn)
                else:
                    file_path = self._synthesize_elevenlabs(text, sn)

                # 3. Calculate duration
                duration = self._calculate_duration(file_path)

                self.logger.info(
                    "Scene %d: done (%.1fs, %s)", sn, duration, file_path
                )

                entries.append(
                    SceneAudio(
                        scene_number=sn,
                        file_path=file_path,
                        duration_seconds=duration,
                        char_count=char_count,
                    )
                )
                scenes_ok += 1

            except Exception as exc:
                self.logger.error(
                    "Scene %d: synthesis failed — %s", sn, exc, exc_info=True
                )
                entries.append(
                    SceneAudio(
                        scene_number=sn,
                        file_path=None,
                        duration_seconds=0.0,
                        char_count=char_count,
                        error=str(exc),
                    )
                )
                scenes_fail += 1

        total_duration = sum(e.duration_seconds for e in entries)

        self.logger.info(
            "Synthesis complete: %d ok, %d failed, %.1fs total, %d chars",
            scenes_ok, scenes_fail, total_duration, total_chars,
        )

        return AudioManifest(
            entries=entries,
            total_duration_seconds=total_duration,
            total_scenes_synthesized=scenes_ok,
            total_scenes_failed=scenes_fail,
            total_characters_processed=total_chars,
        )

    def _synthesize_fishaudio(self, text: str, scene_number: int, emotion: str = "neutral") -> str:
        """Fish Audio path: clean text → add pauses → prepend emotion tag → API."""
        clean_text = _PAUSE_MARKER.sub("", text).strip()
        # Strip non-speakable characters: hashtags, markdown, URLs, etc.
        clean_text = re.sub(r"#\w+", "", clean_text)          # #hashtags
        clean_text = re.sub(r"\*+", "", clean_text)            # **bold**/italic
        clean_text = re.sub(r"`[^`]*`", "", clean_text)        # `code`
        clean_text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", clean_text)  # [text](url) → text
        clean_text = re.sub(r"https?://\S+", "", clean_text)   # bare URLs
        clean_text = re.sub(r"[#*_~|>]", "", clean_text)       # leftover markdown chars
        # Punctuation pause enhancement — Fish Speech treats "..." as a natural breath
        clean_text = re.sub(r",\s*", ", ... ", clean_text)     # comma → comma + pause
        clean_text = re.sub(r";\s*", "; ... ", clean_text)     # semicolon → pause
        clean_text = re.sub(r":\s*", ": ... ", clean_text)     # colon → pause
        clean_text = re.sub(r"—\s*", "... ", clean_text)       # em dash → pause
        clean_text = re.sub(r"-\s+-", "... ", clean_text)      # spaced hyphens → pause
        # Collapse multiple spaces / multiple ellipses
        clean_text = re.sub(r"(\.\.\.[\s.]*){2,}", "... ", clean_text)
        clean_text = re.sub(r"  +", " ", clean_text).strip()
        # Prepend emotion tag at the start of the text (required placement per docs).
        # Both s1-mini (local) and S1 (cloud) officially support 64+ emotion tags.
        # Higher temperature (≥0.7) improves emotion expressiveness.
        if emotion and emotion != "neutral":
            clean_text = f"({emotion}) {clean_text}"
        return self.client.synthesize(clean_text, scene_number=scene_number)

    def _synthesize_elevenlabs(self, text: str, scene_number: int) -> str:
        """ElevenLabs path: build SSML → call API → write MP3."""
        ssml = self.ssml_builder.build(text)
        audio_bytes = self.client.synthesize(ssml, scene_number=scene_number)
        return self._write_audio(audio_bytes, scene_number)
    def _synthesize_coqui(self, text: str, scene_number: int) -> str:
        """Coqui XTTS-v2 path: clean text → synthesize locally."""
        clean_text = _PAUSE_MARKER.sub("", text).strip()
        clean_text = re.sub(r"#\w+", "", clean_text)
        clean_text = re.sub(r"\*+", "", clean_text)
        clean_text = re.sub(r"`[^`]*`", "", clean_text)
        clean_text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", clean_text)
        clean_text = re.sub(r"https?://\S+", "", clean_text)
        clean_text = re.sub(r"[#*_~|>]", "", clean_text)
        clean_text = re.sub(r"  +", " ", clean_text).strip()
        return self.client.synthesize(clean_text, scene_number=scene_number)

    def _write_audio(self, audio_bytes: bytes, scene_number: int) -> str:
        """Write audio bytes to disk (ElevenLabs path)."""
        os.makedirs(self.config.output_dir, exist_ok=True)
        filename = f"scene_{scene_number:03d}.mp3"
        file_path = os.path.join(self.config.output_dir, filename)
        with open(file_path, "wb") as f:
            f.write(audio_bytes)
        return os.path.abspath(file_path)

    def _calculate_duration(self, file_path: str) -> float:
        """Calculate audio duration in seconds."""
        if file_path.endswith(".wav"):
            return self._wav_duration(file_path)
        return self._mp3_duration(file_path)

    @staticmethod
    def _wav_duration(file_path: str) -> float:
        try:
            import soundfile as sf
            info = sf.info(file_path)
            return info.duration
        except Exception:
            size_bytes = os.path.getsize(file_path)
            return (size_bytes - 44) / (24000 * 2)

    @staticmethod
    def _mp3_duration(file_path: str) -> float:
        try:
            from mutagen.mp3 import MP3
            audio = MP3(file_path)
            return audio.info.length
        except Exception:
            size_bytes = os.path.getsize(file_path)
            return size_bytes / (128 * 1000 / 8)
