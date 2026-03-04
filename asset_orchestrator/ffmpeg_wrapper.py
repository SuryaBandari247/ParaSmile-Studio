"""FFmpeg wrapper for composing audio and video files."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess

from asset_orchestrator.config import CompositionConfig
from asset_orchestrator.exceptions import CompositionError

logger = logging.getLogger(__name__)


class FFmpegWrapper:
    """Composes audio and video files using FFmpeg."""

    def __init__(self, config: CompositionConfig | None = None):
        """
        Args:
            config: Composition config. Uses defaults if None.

        Raises:
            EnvironmentError: If FFmpeg is not found on PATH.
        """
        if shutil.which("ffmpeg") is None:
            raise EnvironmentError(
                "FFmpeg is not installed or not found on the system PATH. "
                "Please install FFmpeg: https://ffmpeg.org/download.html"
            )
        self.config = config if config is not None else CompositionConfig()

    def compose(
        self,
        audio_path: str,
        video_path: str,
        output_path: str | None = None,
    ) -> str:
        """
        Combine audio and video into a single MP4.

        Loops video if audio is longer. Trims video if audio is shorter.
        Preserves 1080p/30fps.

        Args:
            audio_path: Path to audio file.
            video_path: Path to MP4 video file.
            output_path: Optional output path. Derived from video filename
                in the configured output_dir if None.

        Returns:
            Absolute file path of the composed MP4.

        Raises:
            FileNotFoundError: If audio or video file missing.
            CompositionError: If FFmpeg command fails.
        """
        if not os.path.isfile(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        if not os.path.isfile(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        if output_path is None:
            video_basename = os.path.splitext(os.path.basename(video_path))[0]
            output_path = os.path.join(
                self.config.output_dir, f"{video_basename}_composed.mp4"
            )

        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        cmd = self._build_command(audio_path, video_path, output_path)

        logger.info("Running FFmpeg command: %s", " ".join(cmd))

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            raise CompositionError(
                error_output=exc.stderr or exc.stdout or str(exc),
                command=" ".join(cmd),
            ) from exc

        return os.path.abspath(output_path)

    def _build_command(
        self, audio_path: str, video_path: str, output_path: str
    ) -> list[str]:
        """Build the FFmpeg command list."""
        cfg = self.config
        return [
            "ffmpeg",
            "-y",
            "-stream_loop", "-1",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", cfg.video_codec,
            "-c:a", cfg.audio_codec,
            "-b:v", cfg.video_bitrate,
            "-b:a", cfg.audio_bitrate,
            "-vf", "scale=1920:1080",
            "-r", "30",
            "-shortest",
            "-map", "0:v:0",
            "-map", "1:a:0",
            output_path,
        ]
