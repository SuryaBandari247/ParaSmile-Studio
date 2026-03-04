"""
LLM client wrapper for OpenAI API.

Provides a thin wrapper around the OpenAI Python SDK with JSON mode
enabled, token usage tracking, and proper error mapping to the
script converter exception hierarchy.
"""

from dataclasses import dataclass

from openai import OpenAI, BadRequestError

from script_generator.exceptions import AuthenticationError, LLMError


@dataclass
class LLMResponse:
    """Response from an LLM completion call."""

    content: str  # Raw JSON string from the LLM
    prompt_tokens: int
    completion_tokens: int
    model: str


class LLMClient:
    """Thin wrapper around the OpenAI chat completions API."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        """
        Initialize the OpenAI client.

        Args:
            api_key: OpenAI API key.
            model: Model name to use for completions.

        Raises:
            AuthenticationError: If api_key is empty or None.
        """
        if not api_key:
            raise AuthenticationError("OpenAI API key is required")

        self._model = model
        self._client = OpenAI(api_key=api_key)

    def complete(self, system_prompt: str, user_message: str) -> LLMResponse:
        """
        Call OpenAI chat completions with JSON mode.

        Args:
            system_prompt: System-level instructions for the LLM.
            user_message: User message (raw script text).

        Returns:
            LLMResponse with content, token counts, and model name.

        Raises:
            LLMError: For non-retryable API errors (e.g., 400 bad request).
        """
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                response_format={"type": "json_object"},
                max_tokens=16000,
            )
        except BadRequestError as exc:
            raise LLMError(f"OpenAI API error: {exc}") from exc

        return LLMResponse(
            content=response.choices[0].message.content,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            model=response.model,
        )
