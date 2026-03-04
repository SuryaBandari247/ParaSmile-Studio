"""Unit tests for the SSMLBuilder."""

import xml.etree.ElementTree as ET

import pytest

from voice_synthesizer.ssml_builder import SSMLBuilder


class TestSSMLBuilderBasic:
    """Basic SSML generation tests."""

    def test_empty_text_produces_valid_ssml(self):
        sb = SSMLBuilder()
        result = sb.build("")
        assert result.startswith("<speak>")
        assert result.endswith("</speak>")
        # Should be parseable XML
        ET.fromstring(result)

    def test_whitespace_only_produces_valid_ssml(self):
        sb = SSMLBuilder()
        result = sb.build("   ")
        ET.fromstring(result)

    def test_simple_text_wrapped_in_speak(self):
        sb = SSMLBuilder()
        result = sb.build("Hello world")
        assert "<speak>" in result
        assert "</speak>" in result
        assert "Hello world" in result

    def test_prosody_rate_wrapping(self):
        sb = SSMLBuilder(speaking_rate="slow")
        result = sb.build("Test text")
        assert '<prosody rate="slow">' in result

    def test_default_rate_is_medium(self):
        sb = SSMLBuilder()
        result = sb.build("Test text")
        assert '<prosody rate="medium">' in result

    def test_output_is_valid_xml(self):
        sb = SSMLBuilder()
        text = "First sentence. Second sentence! Third sentence?"
        result = sb.build(text)
        # Should parse without error
        root = ET.fromstring(result)
        assert root.tag == "speak"


class TestSSMLBuilderSentenceBreaks:
    """Sentence boundary break tests."""

    def test_period_gets_break(self):
        sb = SSMLBuilder(sentence_pause_ms=400)
        result = sb.build("First sentence. Second sentence.")
        assert '<break time="400ms"/>' in result

    def test_exclamation_gets_break(self):
        sb = SSMLBuilder(sentence_pause_ms=400)
        result = sb.build("Wow! That is great.")
        assert '<break time="400ms"/>' in result

    def test_question_gets_break(self):
        sb = SSMLBuilder(sentence_pause_ms=400)
        result = sb.build("Is this working? Yes it is.")
        assert '<break time="400ms"/>' in result

    def test_custom_pause_duration(self):
        sb = SSMLBuilder(sentence_pause_ms=600)
        result = sb.build("First. Second.")
        assert '<break time="600ms"/>' in result


class TestSSMLBuilderParagraphBreaks:
    """Paragraph boundary break tests."""

    def test_double_newline_gets_break(self):
        sb = SSMLBuilder(paragraph_pause_ms=800)
        result = sb.build("First paragraph.\n\nSecond paragraph.")
        assert '<break time="800ms"/>' in result

    def test_custom_paragraph_pause(self):
        sb = SSMLBuilder(paragraph_pause_ms=1200)
        result = sb.build("Para one.\n\nPara two.")
        assert '<break time="1200ms"/>' in result


class TestSSMLBuilderXMLEscaping:
    """XML special character escaping tests."""

    def test_ampersand_escaped(self):
        sb = SSMLBuilder()
        result = sb.build("Tom & Jerry")
        assert "&amp;" in result
        ET.fromstring(result)

    def test_less_than_escaped(self):
        sb = SSMLBuilder()
        result = sb.build("x < y")
        assert "&lt;" in result
        ET.fromstring(result)

    def test_greater_than_escaped(self):
        sb = SSMLBuilder()
        result = sb.build("x > y")
        assert "&gt;" in result
        ET.fromstring(result)

    def test_double_quote_escaped(self):
        sb = SSMLBuilder()
        result = sb.build('He said "hello"')
        assert "&quot;" in result
        ET.fromstring(result)

    def test_single_quote_escaped(self):
        sb = SSMLBuilder()
        result = sb.build("It's fine")
        assert "&apos;" in result
        ET.fromstring(result)

    def test_multiple_special_chars(self):
        sb = SSMLBuilder()
        result = sb.build("A & B < C > D")
        assert "&amp;" in result
        assert "&lt;" in result
        assert "&gt;" in result
        ET.fromstring(result)


class TestSSMLBuilderPauseMarkers:
    """Pause marker conversion tests."""

    def test_pause_marker_converted(self):
        sb = SSMLBuilder()
        result = sb.build("Hello {{pause:300ms}} world")
        assert '<break time="300ms"/>' in result
        assert "{{pause:" not in result

    def test_multiple_pause_markers(self):
        sb = SSMLBuilder()
        result = sb.build("A {{pause:200ms}} B {{pause:400ms}} C")
        assert '<break time="200ms"/>' in result
        assert '<break time="400ms"/>' in result

    def test_pause_marker_with_xml_chars(self):
        sb = SSMLBuilder()
        result = sb.build("A & B {{pause:300ms}} C < D")
        assert '<break time="300ms"/>' in result
        assert "&amp;" in result
        assert "&lt;" in result
        ET.fromstring(result)
