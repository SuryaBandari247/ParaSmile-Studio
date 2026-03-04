"""
Unit tests for the Cross-Reference Engine.

Tests authority channel fetching, topic matching, stock ticker extraction,
company name extraction, finance context building, and macro bonus application.
"""

import pytest
from unittest.mock import MagicMock, patch

from research_agent.cross_reference import CrossReferenceEngine


@pytest.fixture
def mock_api_client():
    """Create a mock YouTube API client."""
    client = MagicMock()
    client.search_videos = MagicMock(return_value=[])
    return client


@pytest.fixture
def engine(mock_api_client):
    """Create a CrossReferenceEngine with a mock API client."""
    return CrossReferenceEngine(mock_api_client)


# --- Authority Channel Fetching ---

class TestFetchAuthorityContent:
    def test_fetches_from_all_authority_channels(self, engine, mock_api_client):
        """Each authority channel should be queried."""
        mock_api_client.search_videos.return_value = [
            {"title": "Test Video", "description": "desc", "video_id": "v1"}
        ]

        result = engine.fetch_authority_content(max_videos_per_channel=5)

        assert mock_api_client.search_videos.call_count == len(engine.AUTHORITY_CHANNELS)
        # 7 channels × 1 video each
        assert len(result) == 7

    def test_tags_videos_with_authority_channel_name(self, engine, mock_api_client):
        """Returned videos should have an 'authority_channel' field."""
        # Return a fresh dict each call so the mutation doesn't collide
        mock_api_client.search_videos.side_effect = lambda **kw: [
            {"title": "Video", "description": "d", "video_id": "v1"}
        ]

        result = engine.fetch_authority_content(max_videos_per_channel=1)

        channel_names = {v["authority_channel"] for v in result}
        assert channel_names == set(engine.AUTHORITY_CHANNELS.keys())

    def test_continues_on_channel_failure(self, engine, mock_api_client):
        """If one channel fails, the rest should still be fetched."""
        call_count = [0]

        def side_effect(**kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("Channel unavailable")
            return [{"title": "OK", "description": "d", "video_id": f"v{call_count[0]}"}]

        mock_api_client.search_videos.side_effect = side_effect

        result = engine.fetch_authority_content(max_videos_per_channel=1)

        # 6 successful channels (1 failed)
        assert len(result) == 6
        assert mock_api_client.search_videos.call_count == 7

    def test_respects_max_videos_per_channel(self, engine, mock_api_client):
        """max_videos_per_channel should be passed to search_videos."""
        mock_api_client.search_videos.return_value = []

        engine.fetch_authority_content(max_videos_per_channel=3)

        for call in mock_api_client.search_videos.call_args_list:
            assert call.kwargs.get("max_results") == 3 or call[1].get("max_results") == 3


# --- Topic Matching ---

class TestMatchTopics:
    def test_high_similarity_matches(self, engine):
        """Topics with high keyword overlap should match."""
        topics = [{"topic_name": "kubernetes docker cloud deployment"}]
        authority_videos = [
            {"title": "kubernetes docker cloud deployment guide", "description": ""}
        ]

        result = engine.match_topics(topics, authority_videos, similarity_threshold=0.3)

        assert result["kubernetes docker cloud deployment"] is True

    def test_low_similarity_no_match(self, engine):
        """Topics with no keyword overlap should not match."""
        topics = [{"topic_name": "quantum physics research"}]
        authority_videos = [
            {"title": "cooking recipes for beginners", "description": "food tips"}
        ]

        result = engine.match_topics(topics, authority_videos, similarity_threshold=0.3)

        assert result["quantum physics research"] is False

    def test_empty_authority_videos(self, engine):
        """With no authority videos, nothing should match."""
        topics = [
            {"topic_name": "python programming"},
            {"topic_name": "aws cloud"},
        ]

        result = engine.match_topics(topics, [], similarity_threshold=0.3)

        assert all(v is False for v in result.values())

    def test_empty_topics(self, engine):
        """With no topics, result should be empty dict."""
        authority_videos = [{"title": "some video", "description": "desc"}]

        result = engine.match_topics([], authority_videos, similarity_threshold=0.3)

        assert result == {}

    def test_threshold_boundary(self, engine):
        """Similarity exactly at threshold should match."""
        # Use identical text to guarantee similarity >= threshold
        topics = [{"topic_name": "cloud infrastructure"}]
        authority_videos = [{"title": "cloud infrastructure", "description": ""}]

        result = engine.match_topics(topics, authority_videos, similarity_threshold=0.0)

        assert result["cloud infrastructure"] is True


# --- Stock Ticker Extraction ---

class TestExtractStockTickers:
    def test_extracts_valid_tickers(self, engine):
        """Should extract $SYMBOL format tickers."""
        text = "Check out $NVDA and $AMZN for great returns"
        result = engine.extract_stock_tickers(text)

        assert set(result) == {"NVDA", "AMZN"}

    def test_ignores_lowercase_dollar_symbols(self, engine):
        """Lowercase after $ should not be extracted."""
        text = "This costs $money and $price"
        result = engine.extract_stock_tickers(text)

        assert result == []

    def test_ignores_too_long_symbols(self, engine):
        """Symbols longer than 5 chars should not match."""
        text = "Not a ticker: $TOOLONG"
        result = engine.extract_stock_tickers(text)

        assert result == []

    def test_single_char_ticker(self, engine):
        """Single uppercase letter after $ is valid (1-5 chars)."""
        text = "Stock $X is interesting"
        result = engine.extract_stock_tickers(text)

        assert result == ["X"]

    def test_deduplicates_tickers(self, engine):
        """Duplicate tickers should appear only once."""
        text = "$AAPL is great, $AAPL again"
        result = engine.extract_stock_tickers(text)

        assert result == ["AAPL"]

    def test_empty_text(self, engine):
        """Empty text should return empty list."""
        assert engine.extract_stock_tickers("") == []


# --- Company Name Extraction ---

class TestExtractCompanies:
    def test_extracts_known_companies(self, engine):
        """Should find companies from the TECH_COMPANIES list."""
        text = "NVIDIA and Microsoft are leading the AI race"
        result = engine.extract_companies(text)

        assert "NVIDIA" in result
        assert "Microsoft" in result

    def test_case_insensitive_matching(self, engine):
        """Company matching should be case-insensitive."""
        text = "nvidia chips are in high demand"
        result = engine.extract_companies(text)

        assert "NVIDIA" in result

    def test_no_companies_found(self, engine):
        """Text without company names returns empty list."""
        text = "The weather is nice today"
        result = engine.extract_companies(text)

        assert result == []

    def test_deduplicates_companies(self, engine):
        """Duplicate company mentions should appear only once."""
        text = "Amazon Web Services by Amazon is great, Amazon rocks"
        result = engine.extract_companies(text)

        assert result.count("Amazon") == 1


# --- Finance Context Building ---

class TestBuildFinanceContext:
    def test_structure_has_required_keys(self, engine):
        """Finance context must have all required keys."""
        topic = {"topic_name": "AI chips", "category": "Technology"}
        result = engine.build_finance_context(topic, False, [])

        assert "stock_tickers" in result
        assert "mentioned_companies" in result
        assert "macro_relevance_score" in result
        assert "authority_channel_match" in result

    def test_authority_match_boosts_score(self, engine):
        """Authority match should increase macro_relevance_score."""
        topic = {"topic_name": "test topic", "category": "Tech"}

        no_match = engine.build_finance_context(topic, False, [])
        with_match = engine.build_finance_context(topic, True, [])

        assert with_match["macro_relevance_score"] > no_match["macro_relevance_score"]
        assert with_match["authority_channel_match"] is True
        assert no_match["authority_channel_match"] is False

    def test_extracts_tickers_from_topic_videos(self, engine):
        """Should extract tickers from top_videos metadata."""
        topic = {
            "topic_name": "stock market",
            "category": "Finance",
            "top_videos": [
                {"title": "$NVDA surges", "description": "$AMZN earnings"}
            ]
        }

        result = engine.build_finance_context(topic, False, [])

        assert "NVDA" in result["stock_tickers"]
        assert "AMZN" in result["stock_tickers"]

    def test_score_capped_at_one(self, engine):
        """macro_relevance_score should never exceed 1.0."""
        topic = {
            "topic_name": "$NVDA NVIDIA stock",
            "category": "Finance",
            "top_videos": [
                {"title": "$AAPL Apple", "description": "Microsoft $MSFT"}
            ]
        }

        result = engine.build_finance_context(topic, True, [])

        assert result["macro_relevance_score"] <= 1.0


# --- Macro Bonus Application ---

class TestApplyMacroBonus:
    def test_doubles_matched_topic_score(self, engine):
        """Matched topics should get 2x trend_score."""
        topics = [{"topic_name": "ai", "trend_score": 40.0}]
        match_status = {"ai": True}

        result = engine.apply_macro_bonus(topics, match_status)

        assert result[0]["trend_score"] == 80.0

    def test_caps_score_at_100(self, engine):
        """Score should never exceed 100 after bonus."""
        topics = [{"topic_name": "ai", "trend_score": 60.0}]
        match_status = {"ai": True}

        result = engine.apply_macro_bonus(topics, match_status)

        assert result[0]["trend_score"] == 100.0

    def test_unmatched_topics_unchanged(self, engine):
        """Unmatched topics should keep their original score."""
        topics = [{"topic_name": "cooking", "trend_score": 45.0}]
        match_status = {"cooking": False}

        result = engine.apply_macro_bonus(topics, match_status)

        assert result[0]["trend_score"] == 45.0

    def test_missing_from_match_status_unchanged(self, engine):
        """Topics not in match_status should keep their original score."""
        topics = [{"topic_name": "unknown", "trend_score": 30.0}]
        match_status = {}

        result = engine.apply_macro_bonus(topics, match_status)

        assert result[0]["trend_score"] == 30.0

    def test_mixed_matched_and_unmatched(self, engine):
        """Only matched topics should get the bonus."""
        topics = [
            {"topic_name": "ai", "trend_score": 40.0},
            {"topic_name": "cooking", "trend_score": 50.0},
            {"topic_name": "cloud", "trend_score": 30.0},
        ]
        match_status = {"ai": True, "cooking": False, "cloud": True}

        result = engine.apply_macro_bonus(topics, match_status)

        assert result[0]["trend_score"] == 80.0   # ai: 40 * 2
        assert result[1]["trend_score"] == 50.0   # cooking: unchanged
        assert result[2]["trend_score"] == 60.0   # cloud: 30 * 2
