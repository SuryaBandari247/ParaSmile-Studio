"""Unit tests for FFmpegCompositor."""

import os
from unittest.mock import patch, MagicMock

import pytest

from asset_orchestrator.ffmpeg_compositor import FFmpegCompositor
from asset_orchestrator.exceptions import CompositionError


class TestFFmpegCompositorInit:
    def test_creates_output_dir(self, tmp_path):
        out = tmp_path / "composed"
        FFmpegCompositor(output_dir=str(out))
        assert out.is_dir()


class TestTextOverlay:
    @patch("asset_orchestrator.ffmpeg_compositor.subprocess.run")
    def test_compose_text_overlay_creates_png_and_calls_ffmpeg(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0)
        comp = FFmpegCompositor(output_dir=str(tmp_path / "out"))
        video = tmp_path / "input.mp4"
        video.write_bytes(b"fake")

        result = comp.compose_text_overlay(str(video), heading="Test", body="Body")
        assert result.endswith(".mp4")
        mock_run.assert_called_once()
        cmd_str = " ".join(mock_run.call_args[0][0])
        assert "overlay" in cmd_str
        assert "1920:1080" in cmd_str

    @patch("asset_orchestrator.ffmpeg_compositor.subprocess.run")
    def test_heading_only(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0)
        comp = FFmpegCompositor(output_dir=str(tmp_path / "out"))
        video = tmp_path / "input.mp4"
        video.write_bytes(b"fake")

        result = comp.compose_text_overlay(str(video), heading="Just Heading")
        assert result.endswith(".mp4")


class TestStatOverlay:
    @patch("asset_orchestrator.ffmpeg_compositor.subprocess.run")
    def test_stat_overlay(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0)
        comp = FFmpegCompositor(output_dir=str(tmp_path / "out"))
        video = tmp_path / "input.mp4"
        video.write_bytes(b"fake")

        result = comp.compose_stat_overlay(str(video), value="$10K", label="TAX", subtitle="2026")
        assert result.endswith(".mp4")
        mock_run.assert_called_once()


class TestQuoteOverlay:
    @patch("asset_orchestrator.ffmpeg_compositor.subprocess.run")
    def test_quote_overlay(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0)
        comp = FFmpegCompositor(output_dir=str(tmp_path / "out"))
        video = tmp_path / "input.mp4"
        video.write_bytes(b"fake")

        result = comp.compose_quote_overlay(str(video), quote="Be brave", attribution="Someone")
        assert result.endswith(".mp4")
        mock_run.assert_called_once()


class TestSolidBackground:
    @patch("asset_orchestrator.ffmpeg_compositor.subprocess.run")
    def test_generates_solid_bg(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0)
        comp = FFmpegCompositor(output_dir=str(tmp_path / "out"))

        result = comp.generate_solid_background(duration=5.0)
        assert result.endswith(".mp4")
        cmd_str = " ".join(mock_run.call_args[0][0])
        assert "color=" in cmd_str
        assert "1920x1080" in cmd_str


class TestFontAndWrap:
    def test_get_font_returns_font(self):
        font = FFmpegCompositor._get_font(48)
        assert font is not None

    def test_wrap_text(self):
        font = FFmpegCompositor._get_font(32)
        lines = FFmpegCompositor._wrap_text("This is a test of word wrapping", font, 200)
        assert len(lines) >= 1
        assert all(isinstance(l, str) for l in lines)

    def test_wrap_empty_text(self):
        font = FFmpegCompositor._get_font(32)
        lines = FFmpegCompositor._wrap_text("", font, 500)
        assert lines == [""]

    def test_position_to_y(self):
        assert FFmpegCompositor._position_to_y("top") < FFmpegCompositor._position_to_y("center")
        assert FFmpegCompositor._position_to_y("center") < FFmpegCompositor._position_to_y("bottom")


class TestErrorHandling:
    @patch("asset_orchestrator.ffmpeg_compositor.subprocess.run")
    def test_composition_error_on_ffmpeg_failure(self, mock_run, tmp_path):
        import subprocess
        mock_run.side_effect = subprocess.CalledProcessError(1, "ffmpeg", stderr="error")
        comp = FFmpegCompositor(output_dir=str(tmp_path / "out"))

        with pytest.raises(CompositionError):
            comp.generate_solid_background()
