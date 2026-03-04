"""Unit tests for the ElevenLabsClient."""

from unittest.mock import MagicMock, patch

import pytest

from voice_synthesizer.elevenlabs_client import ElevenLabsClient
from voice_synthesizer.exceptions import (
    AuthenticationError,
    NetworkError,
    SynthesisError,
)


class TestElevenLabsClientAuth:
    """Authentication tests."""

    def test_empty_api_key_raises(self):
        with pytest.raises(AuthenticationError, match="missing or empty"):
            ElevenLabsClient(api_key="")

    def test_none_api_key_raises(self):
        with pytest.raises(AuthenticationError, match="missing or empty"):
            ElevenLabsClient(api_key=None)

    def test_valid_api_key_accepted(self):
        client = ElevenLabsClient(api_key="test-key-123")
        assert client.api_key == "test-key-123"


class TestElevenLabsClientSynthesize:
    """Synthesis tests with mocked HTTP."""

    @patch("voice_synthesizer.elevenlabs_client.requests.post")
    def test_successful_synthesis(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"fake-audio-bytes"
        mock_post.return_value = mock_response

        client = ElevenLabsClient(api_key="test-key")
        result = client.synthesize("<speak>Hello</speak>", scene_number=1)

        assert result == b"fake-audio-bytes"
        mock_post.assert_called_once()

    @patch("voice_synthesizer.elevenlabs_client.requests.post")
    def test_voice_settings_in_request(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"audio"
        mock_post.return_value = mock_response

        client = ElevenLabsClient(
            api_key="test-key",
            voice_id="custom-voice",
            model_id="custom-model",
            stability=0.7,
            similarity_boost=0.9,
            style=0.3,
        )
        client.synthesize("<speak>Test</speak>", scene_number=1)

        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert payload["model_id"] == "custom-model"
        assert payload["voice_settings"]["stability"] == 0.7
        assert payload["voice_settings"]["similarity_boost"] == 0.9
        assert payload["voice_settings"]["style"] == 0.3

    @patch("voice_synthesizer.elevenlabs_client.time.sleep")
    @patch("voice_synthesizer.elevenlabs_client.requests.post")
    def test_retry_on_429(self, mock_post, mock_sleep):
        # First two calls return 429, third returns 200
        resp_429 = MagicMock()
        resp_429.status_code = 429
        resp_429.text = "rate limited"

        resp_200 = MagicMock()
        resp_200.status_code = 200
        resp_200.content = b"audio-after-retry"

        mock_post.side_effect = [resp_429, resp_429, resp_200]

        client = ElevenLabsClient(api_key="test-key")
        result = client.synthesize("<speak>Test</speak>", scene_number=1)

        assert result == b"audio-after-retry"
        assert mock_post.call_count == 3
        assert mock_sleep.call_count == 2

    @patch("voice_synthesizer.elevenlabs_client.time.sleep")
    @patch("voice_synthesizer.elevenlabs_client.requests.post")
    def test_synthesis_error_after_retries(self, mock_post, mock_sleep):
        resp_429 = MagicMock()
        resp_429.status_code = 429
        resp_429.text = "rate limited"
        mock_post.return_value = resp_429

        client = ElevenLabsClient(api_key="test-key")
        with pytest.raises(SynthesisError, match="Scene 3"):
            client.synthesize("<speak>Test</speak>", scene_number=3)

    @patch("voice_synthesizer.elevenlabs_client.requests.post")
    def test_non_retryable_error(self, mock_post):
        resp_400 = MagicMock()
        resp_400.status_code = 400
        resp_400.text = "bad request"
        mock_post.return_value = resp_400

        client = ElevenLabsClient(api_key="test-key")
        with pytest.raises(SynthesisError, match="HTTP 400"):
            client.synthesize("<speak>Test</speak>", scene_number=1)

    @patch("voice_synthesizer.elevenlabs_client.time.sleep")
    @patch("voice_synthesizer.elevenlabs_client.requests.post")
    def test_network_error_after_retries(self, mock_post, mock_sleep):
        import requests as req
        mock_post.side_effect = req.ConnectionError("connection refused")

        client = ElevenLabsClient(api_key="test-key")
        with pytest.raises(NetworkError, match="Network error"):
            client.synthesize("<speak>Test</speak>", scene_number=1)
