"""Unit tests for FishAudioClient."""

import os
from unittest.mock import MagicMock, patch

import pytest

from voice_synthesizer.exceptions import AuthenticationError, SynthesisError
from voice_synthesizer.fish_audio_client import FishAudioClient


class TestFishAudioClientInit:
    """Initialization tests."""

    def test_missing_api_key_raises(self):
        with pytest.raises(AuthenticationError, match="FISH_API_KEY"):
            FishAudioClient(api_key="")

    def test_default_init(self):
        client = FishAudioClient(api_key="test-key")
        assert client.api_key == "test-key"
        assert client.speed == 1.0
        assert client.output_format == "mp3"
        assert client.reference_id is None
        assert client._client is None  # lazy init

    def test_custom_init(self):
        client = FishAudioClient(
            api_key="test-key",
            reference_id="voice-123",
            speed=1.5,
            output_format="wav",
            temperature=0.5,
        )
        assert client.reference_id == "voice-123"
        assert client.speed == 1.5
        assert client.output_format == "wav"
        assert client.temperature == 0.5


class TestFishAudioClientSynthesize:
    """Synthesis tests."""

    @patch("voice_synthesizer.fish_audio_client.FishAudioClient._get_config")
    @patch("voice_synthesizer.fish_audio_client.FishAudioClient._get_client")
    def test_synthesize_writes_audio(self, mock_get_client, mock_get_config, tmp_path):
        mock_client = MagicMock()
        mock_client.tts.convert.return_value = [b"fake-audio-chunk"]
        mock_get_client.return_value = mock_client
        mock_get_config.return_value = MagicMock()

        client = FishAudioClient(api_key="test-key", output_dir=str(tmp_path))
        result = client.synthesize("Hello world.", scene_number=1)

        assert os.path.isabs(result)
        assert "scene_001.mp3" in result
        assert os.path.exists(result)
        with open(result, "rb") as f:
            assert f.read() == b"fake-audio-chunk"

    @patch("voice_synthesizer.fish_audio_client.FishAudioClient._get_config")
    @patch("voice_synthesizer.fish_audio_client.FishAudioClient._get_client")
    def test_synthesize_wav_format(self, mock_get_client, mock_get_config, tmp_path):
        mock_client = MagicMock()
        mock_client.tts.convert.return_value = [b"RIFF"]
        mock_get_client.return_value = mock_client
        mock_get_config.return_value = MagicMock()

        client = FishAudioClient(
            api_key="test-key", output_format="wav", output_dir=str(tmp_path)
        )
        result = client.synthesize("Test.", scene_number=3)

        assert "scene_003.wav" in result

    @patch("voice_synthesizer.fish_audio_client.FishAudioClient._get_config")
    @patch("voice_synthesizer.fish_audio_client.FishAudioClient._get_client")
    def test_synthesize_failure_raises(self, mock_get_client, mock_get_config, tmp_path):
        mock_client = MagicMock()
        mock_client.tts.convert.side_effect = RuntimeError("API error")
        mock_get_client.return_value = mock_client
        mock_get_config.return_value = MagicMock()

        client = FishAudioClient(api_key="test-key", output_dir=str(tmp_path))

        with pytest.raises(SynthesisError, match="Fish Audio TTS failed"):
            client.synthesize("Hello.", scene_number=1)

    @patch("voice_synthesizer.fish_audio_client.FishAudioClient._get_config")
    @patch("voice_synthesizer.fish_audio_client.FishAudioClient._get_client")
    def test_synthesize_empty_output_raises(self, mock_get_client, mock_get_config, tmp_path):
        mock_client = MagicMock()
        mock_client.tts.convert.return_value = []  # no chunks
        mock_get_client.return_value = mock_client
        mock_get_config.return_value = MagicMock()

        client = FishAudioClient(api_key="test-key", output_dir=str(tmp_path))

        with pytest.raises(SynthesisError, match="empty output"):
            client.synthesize("Hello.", scene_number=1)

    @patch("voice_synthesizer.fish_audio_client.FishAudioClient._get_config")
    @patch("voice_synthesizer.fish_audio_client.FishAudioClient._get_client")
    def test_scene_number_in_filename(self, mock_get_client, mock_get_config, tmp_path):
        mock_client = MagicMock()
        mock_client.tts.convert.return_value = [b"audio"]
        mock_get_client.return_value = mock_client
        mock_get_config.return_value = MagicMock()

        client = FishAudioClient(api_key="test-key", output_dir=str(tmp_path))
        result = client.synthesize("Test.", scene_number=5)

        assert "scene_005.mp3" in result

    @patch("voice_synthesizer.fish_audio_client.FishAudioClient._get_config")
    @patch("voice_synthesizer.fish_audio_client.FishAudioClient._get_client")
    def test_multiple_chunks_concatenated(self, mock_get_client, mock_get_config, tmp_path):
        mock_client = MagicMock()
        mock_client.tts.convert.return_value = [b"chunk1", b"chunk2", b"chunk3"]
        mock_get_client.return_value = mock_client
        mock_get_config.return_value = MagicMock()

        client = FishAudioClient(api_key="test-key", output_dir=str(tmp_path))
        result = client.synthesize("Hello world.", scene_number=1)

        with open(result, "rb") as f:
            assert f.read() == b"chunk1chunk2chunk3"
