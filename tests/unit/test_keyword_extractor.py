"""Unit tests for KeywordExtractor."""

from unittest.mock import MagicMock, patch

from asset_orchestrator.keyword_extractor import KeywordExtractor


class TestKeywordExtractor:
    """Test KeywordExtractor."""

    def test_simple_extraction_returns_keywords(self):
        ext = KeywordExtractor(use_llm=False)
        keywords = ext.extract(
            "People filing taxes at the IRS office worried about money",
            title="Tax Season",
        )
        assert len(keywords) >= 2
        assert len(keywords) <= 4

    def test_simple_extraction_skips_stop_words(self):
        ext = KeywordExtractor(use_llm=False)
        keywords = ext.extract("the quick brown fox jumps over the lazy dog")
        for kw in keywords:
            assert kw not in {"the", "over"}

    def test_caching_returns_same_result(self):
        ext = KeywordExtractor(use_llm=False)
        kw1 = ext.extract("test narration about finance", "Finance")
        kw2 = ext.extract("test narration about finance", "Finance")
        assert kw1 == kw2

    def test_empty_narration_returns_fallback(self):
        ext = KeywordExtractor(use_llm=False)
        keywords = ext.extract("", "")
        assert len(keywords) >= 1

    def test_llm_extraction_with_mock(self):
        ext = KeywordExtractor(use_llm=True)
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = "taxes, IRS office, worried person"
        mock_client.chat.completions.create.return_value = mock_resp
        ext._openai_client = mock_client

        keywords = ext.extract("People filing taxes at the IRS office", "Tax Trap")
        assert "taxes" in keywords
        assert len(keywords) <= 4

    def test_llm_failure_falls_back_to_simple(self):
        ext = KeywordExtractor(use_llm=True)
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API error")
        ext._openai_client = mock_client

        keywords = ext.extract("People filing taxes at the IRS office", "Tax Trap")
        assert len(keywords) >= 2  # Simple extraction still works
