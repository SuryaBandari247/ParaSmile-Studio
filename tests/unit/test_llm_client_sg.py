"""Unit tests for the LLM client wrapper."""

from unittest.mock import MagicMock, patch

import pytest
from openai import BadRequestError

from script_generator.exceptions import AuthenticationError, LLMError
from script_generator.llm_client import LLMClient, LLMResponse


class TestLLMClientInit:
    """Tests for LLMClient initialization."""

    def test_empty_api_key_raises_authentication_error(self):
        with pytest.raises(AuthenticationError, match="API key is required"):
            LLMClient(api_key="")

    def test_none_api_key_raises_authentication_error(self):
        with pytest.raises(AuthenticationError, match="API key is required"):
            LLMClient(api_key=None)

    @patch("script_generator.llm_client.OpenAI")
    def test_valid_api_key_creates_client(self, mock_openai_cls):
        client = LLMClient(api_key="sk-test-key")
        mock_openai_cls.assert_called_once_with(api_key="sk-test-key")
        assert client._model == "gpt-4o-mini"


class TestLLMClientComplete:
    """Tests for LLMClient.complete()."""

    @patch("script_generator.llm_client.OpenAI")
    def test_successful_completion_returns_llm_response(self, mock_openai_cls):
        # Build mock response matching OpenAI's structure
        mock_message = MagicMock()
        mock_message.content = '{"title": "Test"}'

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 50
        mock_usage.completion_tokens = 100

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage
        mock_response.model = "gpt-4o-mini"

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        client = LLMClient(api_key="sk-test-key")
        result = client.complete("system prompt", "user message")

        assert isinstance(result, LLMResponse)
        assert result.content == '{"title": "Test"}'
        assert result.prompt_tokens == 50
        assert result.completion_tokens == 100
        assert result.model == "gpt-4o-mini"

    @patch("script_generator.llm_client.OpenAI")
    def test_bad_request_raises_llm_error(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = BadRequestError(
            message="Invalid request",
            response=MagicMock(status_code=400),
            body=None,
        )
        mock_openai_cls.return_value = mock_client

        client = LLMClient(api_key="sk-test-key")
        with pytest.raises(LLMError, match="OpenAI API error"):
            client.complete("system prompt", "user message")

    @patch("script_generator.llm_client.OpenAI")
    def test_json_mode_is_set_in_api_call(self, mock_openai_cls):
        mock_message = MagicMock()
        mock_message.content = "{}"

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=20)
        mock_response.model = "gpt-4o-mini"

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        client = LLMClient(api_key="sk-test-key")
        client.complete("system prompt", "user message")

        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["response_format"] == {"type": "json_object"}
