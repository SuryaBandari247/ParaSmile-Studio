"""
ScriptConverter orchestrator for the Script Converter pipeline.

Accepts raw script text, uses GPT-4o-mini to convert it into a structured
VideoScript JSON, validates visual instructions, and returns a render-ready
script with retry logic on parse/validation failures.

Requirements: 1.1, 1.2, 1.3, 2.1, 2.4, 2.5, 2.6, 3.1, 4.1, 6.1, 6.2, 6.4, 6.5, 7.1, 7.4, 8.1, 8.2, 8.3
"""

from __future__ import annotations

from script_generator.config import ConverterConfig
from script_generator.exceptions import AuthenticationError, ParseError, ValidationError
from script_generator.llm_client import LLMClient
from script_generator.logger import get_logger
from script_generator.models import VideoScript
from script_generator.serializer import ScriptSerializer
from script_generator.validator import Validator

VALID_VISUAL_TYPES = ["bar_chart", "line_chart", "pie_chart", "code_snippet", "text_overlay"]

VALID_EMOTIONS = [
    "neutral", "happy", "excited", "confident", "curious", "calm",
    "serious", "surprised", "empathetic", "sarcastic", "worried",
    "frustrated", "satisfied", "proud", "determined", "nostalgic",
]

SYSTEM_PROMPT = """\
You are a script formatting assistant. Convert the user's raw video script into a JSON object matching the VideoScript schema below. Do NOT add or remove substantive narration content — preserve the original narration.

**VideoScript JSON Schema:**
```json
{
  "title": "<string: video title>",
  "scenes": [
    {
      "scene_number": "<int: 1-based index>",
      "narration_text": "<string: spoken narration for this scene>",
      "emotion": "<string: emotional tone for TTS voice synthesis>",
      "visual_instruction": {
        "type": "<string: one of the valid types below>",
        "title": "<string: short label for the visual>",
        "data": "<object: type-specific data, see below>"
      }
    }
  ],
  "generated_at": "<string: ISO 8601 UTC timestamp>",
  "total_word_count": "<int: total narration words across all scenes>",
  "metadata": {}
}
```

**Valid visual instruction types and their `data` object schemas:**
- bar_chart: `"data": {"labels": ["str", ...], "values": [number, ...]}` (labels and values must be equal length)
- line_chart: `"data": {"labels": ["str", ...], "values": [number, ...]}` (labels and values must be equal length)
- pie_chart: `"data": {"labels": ["str", ...], "values": [number, ...]}` (equal length, all values > 0)
- code_snippet: `"data": {"code": "non-empty string", "language": "string"}`
- text_overlay: `"data": {"text": "A short summary or key point displayed on screen"}`

**IMPORTANT:** The `data` object MUST always contain the required keys for its type. For text_overlay, `data.text` MUST be a non-empty string — never leave it empty or omit it.

**Example scene (text_overlay):**
```json
{
  "scene_number": 1,
  "narration_text": "Welcome to today's deep dive into the latest market trends.",
  "emotion": "confident",
  "visual_instruction": {
    "type": "text_overlay",
    "title": "Market Trends",
    "data": {"text": "Deep Dive: Latest Market Trends"}
  }
}
```

**Valid emotion values:**
neutral, happy, excited, confident, curious, calm, serious, surprised, empathetic, sarcastic, worried, frustrated, satisfied, proud, determined, nostalgic

**Emotion tagging rules:**
- Analyze the TONE and CONTENT of each scene's narration to pick the best-fitting emotion.
- Use "confident" for authoritative statements and presentations of facts.
- Use "curious" for rhetorical questions and exploratory narration.
- Use "excited" for reveals, surprising data, and enthusiastic moments.
- Use "serious" for warnings, critical points, and sobering statistics.
- Use "calm" for neutral explanations and step-by-step walkthroughs.
- Use "sarcastic" for ironic observations or dry humor.
- Default to "neutral" only when no other emotion clearly fits.
- Do NOT use the same emotion for every scene — vary it based on the narration's natural tone shifts.

**CRITICAL LENGTH RULE — READ THIS FIRST:**
You MUST NOT summarize, condense, or shorten the narration. Your output narration word count MUST be at least 90% of the input word count. If the input has 1000 words, the output MUST have at least 900 narration words total. Dropping below this threshold is a FAILURE.

**Rules:**
1. Return ONLY the JSON object, no markdown fences or extra text.
2. Produce one scene per major paragraph, topic shift, OR emotional tone change. If a paragraph starts excited and turns serious, split it into two scenes. Each scene should have ONE consistent emotional tone. Create as many scenes as needed to faithfully represent the input — there is no minimum or maximum.
3. Map visual cues from the raw script to one of the 5 valid types above.
4. Transfer ALL narration content from the input into scene narration_text fields. Include every detail, example, question, and explanation. Do NOT paraphrase into shorter form. Copy the substance verbatim when possible.
5. Set generated_at to the current UTC time in ISO 8601 format.
6. Compute total_word_count as the sum of words in all narration_text fields. This number MUST be close to the input word count.
7. Set emotion for each scene based on the narration's tone. The narration_text itself must NOT contain emotion tags — keep them in the emotion field only.
8. narration_text MUST be clean, speakable text — NO hashtags (#trending), NO markdown formatting (*bold*, `code`), NO URLs, NO special symbols. Write as if a human narrator is reading it aloud. Use words like "hashtag" or "number sign" only if the concept needs to be spoken. Numbers should be written as words when short (e.g. "three out of four") or digits when long (e.g. "73 percent").
"""


class ScriptConverter:
    """Orchestrates raw script to VideoScript conversion via LLM."""

    def __init__(self, config: ConverterConfig | None = None) -> None:
        """
        Initialize the ScriptConverter.

        Loads config (env vars + overrides), initializes LLMClient,
        Validator, Serializer, and Logger.

        Args:
            config: Optional converter configuration. If None, defaults are
                    loaded from environment variables.

        Raises:
            AuthenticationError: If OPENAI_API_KEY is missing after config loading.
            ValidationError: If config values are invalid.
        """
        if config is None:
            config = ConverterConfig()

        self._config = config
        self._logger = get_logger("converter", config.log_level)

        if not config.openai_api_key:
            raise AuthenticationError(
                "OPENAI_API_KEY is required. Set it as an environment variable "
                "or pass it via ConverterConfig."
            )

        self._llm = LLMClient(api_key=config.openai_api_key, model=config.llm_model)
        self._validator = Validator()
        self._serializer = ScriptSerializer()
        self._system_prompt = SYSTEM_PROMPT

    def convert(self, raw_script: str) -> VideoScript:
        """
        Convert a raw script string into a validated VideoScript.

        Args:
            raw_script: The raw script text to convert.

        Returns:
            A validated VideoScript instance.

        Raises:
            ValidationError: If raw_script is empty or whitespace-only.
            ParseError: If the LLM response cannot be parsed/validated after one retry.
        """
        if not raw_script or not raw_script.strip():
            raise ValidationError("raw_script must not be empty or whitespace-only")

        self._logger.info("Conversion requested: raw_script length=%d chars", len(raw_script))

        last_error: Exception | None = None

        for attempt in range(2):
            try:
                if attempt == 0:
                    prompt = raw_script
                else:
                    prompt = (
                        f"The previous response had an error:\n{last_error}\n\n"
                        f"Please fix the output and return valid JSON.\n\n"
                        f"Original script:\n{raw_script}"
                    )

                response = self._llm.complete(self._system_prompt, prompt)

                self._logger.info(
                    "LLM call: model=%s, prompt_tokens=%d, completion_tokens=%d",
                    response.model,
                    response.prompt_tokens,
                    response.completion_tokens,
                )

                script = self._serializer.deserialize(response.content)

                violations = self._validator.validate_script(script)
                if violations:
                    error_msg = "; ".join(violations)
                    raise ValidationError(f"Visual instruction validation failed: {error_msg}")

                return script

            except (ParseError, ValidationError) as exc:
                last_error = exc
                self._logger.error(
                    "Attempt %d failed: %s (raw_script length=%d)",
                    attempt + 1,
                    exc,
                    len(raw_script),
                )
                if attempt == 1:
                    raise ParseError(
                        f"Failed to produce valid VideoScript after retry: {exc}"
                    ) from exc

        # Should never reach here, but satisfy type checker
        raise ParseError("Unexpected converter failure")  # pragma: no cover
