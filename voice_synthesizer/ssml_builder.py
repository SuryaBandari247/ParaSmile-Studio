"""SSML builder for converting narration text to SSML markup."""

from __future__ import annotations

import re


class SSMLBuilder:
    """Transforms narration text into valid SSML with pacing controls."""

    VALID_RATES = {"x-slow", "slow", "medium", "fast", "x-fast"}
    PERCENTAGE_PATTERN = re.compile(r"^\d+%$")

    # Sentence boundary: . ! ? followed by whitespace or end-of-string
    SENTENCE_BOUNDARY = re.compile(r"([.!?])(\s+|$)")

    # Paragraph boundary: double newline
    PARAGRAPH_BOUNDARY = re.compile(r"\n\n+")

    # Pause marker from FillerInjector: {{pause:Nms}}
    PAUSE_MARKER = re.compile(r"\{\{pause:(\d+)ms\}\}")

    def __init__(
        self,
        sentence_pause_ms: int = 400,
        paragraph_pause_ms: int = 800,
        speaking_rate: str = "medium",
    ):
        self.sentence_pause_ms = sentence_pause_ms
        self.paragraph_pause_ms = paragraph_pause_ms
        self.speaking_rate = speaking_rate

    def build(self, text: str) -> str:
        """Convert narration text to valid SSML string.

        1. Escape XML special characters
        2. Convert pause markers to <break> elements
        3. Insert sentence-boundary breaks
        4. Insert paragraph-boundary breaks
        5. Wrap in <prosody> and <speak> elements
        """
        if not text or not text.strip():
            return '<speak><prosody rate="medium"></prosody></speak>'

        result = self._escape_xml(text)
        result = self._convert_pause_markers(result)
        result = self._insert_paragraph_breaks(result)
        result = self._insert_sentence_breaks(result)
        result = f'<prosody rate="{self.speaking_rate}">{result}</prosody>'
        result = f"<speak>{result}</speak>"
        return result

    def _escape_xml(self, text: str) -> str:
        """Escape XML special characters.

        Order matters: & must be escaped first to avoid double-escaping.
        We also must not escape & inside our {{pause:Nms}} markers,
        so we handle those separately.
        """
        # Temporarily replace pause markers
        markers: list[str] = []

        def _save_marker(m: re.Match) -> str:
            markers.append(m.group(0))
            return f"\x00PAUSE{len(markers) - 1}\x00"

        text = self.PAUSE_MARKER.sub(_save_marker, text)

        # Escape XML chars
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
        text = text.replace('"', "&quot;")
        text = text.replace("'", "&apos;")

        # Restore pause markers
        for i, marker in enumerate(markers):
            text = text.replace(f"\x00PAUSE{i}\x00", marker)

        return text

    def _convert_pause_markers(self, text: str) -> str:
        """Convert {{pause:Nms}} markers to <break time="Nms"/> elements."""
        return self.PAUSE_MARKER.sub(
            lambda m: f'<break time="{m.group(1)}ms"/>', text
        )

    def _insert_sentence_breaks(self, text: str) -> str:
        """Insert <break> after sentence boundaries."""

        def _add_break(m: re.Match) -> str:
            punct = m.group(1)
            trailing = m.group(2)
            return f'{punct}<break time="{self.sentence_pause_ms}ms"/>{trailing}'

        return self.SENTENCE_BOUNDARY.sub(_add_break, text)

    def _insert_paragraph_breaks(self, text: str) -> str:
        """Insert <break> after paragraph boundaries (double newline)."""
        return self.PARAGRAPH_BOUNDARY.sub(
            f' <break time="{self.paragraph_pause_ms}ms"/> ', text
        )
