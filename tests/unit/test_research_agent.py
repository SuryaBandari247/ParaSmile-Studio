"""
Unit tests for the ResearchAgent main interface.

Tests the orchestration of components and the get_trending_topics method.
"""

import os
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock

from research_agent.agent import ResearchAgent
from research_agent.exceptions import AuthenticationError, SchemaValidationError
from research_agent.models import TrendingTopic, VideoMetadata


class TestResearchAgentInit:
    """Tests for ResearchAgent initialization."""
    
    def test_init_with_valid_config(self):
        """Test initialization with valid configuration."""
        config = {
            "youtube_api_key": "test_api_key_12345",
            "daily_quota_limit": 10000,
            "cache_ttl_hours": 6
        }
        
        # Prevent load_dotenv from overriding the test API key
        with patch('research_agent.agent.load_dotenv'):
            with patch('research_agent.api_client.load_dotenv'):
                with patch.dict(os.environ, {}, clear=True):
                    agent = ResearchAgent(config=config)
        
        assert agent.config.youtube_api_key == "test_api_key_12345"
        assert agent.config.daily_quota_limit == 10000
        assert agent.config.cache_ttl_hours == 6
        assert agent.api_client is not None
        assert agent.rate_limiter is not None
        assert agent.analyzer is not None
        assert agent.cache is not None
    
    def test_init_with_missing_api_key(self):
        """Test initialization fails with missing API key."""
        from research_agent.config import ConfigValidationError
        
        config = {
            "youtube_api_key": ""
        }
        
        # Prevent load_dotenv from populating a real API key
        with patch('research_agent.agent.load_dotenv'):
            with patch('research_agent.api_client.load_dotenv'):
                with patch.dict(os.environ, {}, clear=True):
                    with pytest.raises(ConfigValidationError):
                        ResearchAgent(config=config)
    
    def test_init_with_default_config(self):
        """Test initialization with default configuration."""
        # Mock environment variable
        with patch.dict('os.environ', {'YOUTUBE_API_KEY': 'test_key_from_env'}):
            agent = ResearchAgent()
            
            assert agent.config.youtube_api_key == 'test_key_from_env'
            assert agent.config.search_days_back == 7
            assert agent.config.min_view_count == 1000
            assert agent.config.min_trend_score == 30


class TestGetTrendingTopics:
    """Tests for get_trending_topics method."""
    
    @pytest.fixture
    def mock_agent(self):
        """Create a ResearchAgent with mocked components."""
        config = {
            "youtube_api_key": "test_api_key_12345",
            "daily_quota_limit": 10000,
            "cache_ttl_hours": 6,
            "default_keywords": ["python tutorial", "devops"],
            "min_trend_score": 30,
            "max_videos_per_query": 50
        }
        
        agent = ResearchAgent(config=config)
        
        # Mock components
        agent.cache = Mock()
        agent.api_client = Mock()
        agent.analyzer = Mock()
        
        return agent
    
    def test_cache_hit_returns_cached_data(self, mock_agent):
        """Test that cache hit returns cached data without API calls."""
        # Setup cache to return data
        cached_data = {
            "topics": [],
            "metadata": {
                "query_date": "2024-01-15T10:00:00Z",
                "total_videos_analyzed": 0,
                "average_trend_score": 0.0
            }
        }
        mock_agent.cache.get.return_value = cached_data
        
        # Call method
        result = mock_agent.get_trending_topics()
        
        # Verify cache was checked
        assert mock_agent.cache.get.called
        
        # Verify API client was NOT called
        assert not mock_agent.api_client.search_videos.called
        
        # Verify result matches cached data
        assert result == cached_data
    
    def test_cache_miss_triggers_api_calls(self, mock_agent):
        """Test that cache miss triggers API calls and analysis."""
        # Setup cache to return None (cache miss)
        mock_agent.cache.get.return_value = None
        
        # Setup API client mock responses
        mock_agent.api_client.search_videos.return_value = [
            {
                'video_id': 'video1',
                'title': 'Python Tutorial',
                'description': 'Learn Python',
                'channel_id': 'channel1',
                'channel_title': 'Tech Channel',
                'published_at': '2024-01-10T10:00:00Z'
            }
        ]
        
        mock_agent.api_client.get_video_details.return_value = [
            {
                'video_id': 'video1',
                'title': 'Python Tutorial',
                'description': 'Learn Python',
                'channel_title': 'Tech Channel',
                'published_at': datetime(2024, 1, 10, 10, 0, 0, tzinfo=timezone.utc),
                'view_count': 5000,
                'like_count': 100,
                'comment_count': 20
            }
        ]
        
        # Setup analyzer mock response
        mock_trending_topic = Mock(spec=TrendingTopic)
        mock_trending_topic.topic_name = "Python Tutorial"
        mock_trending_topic.category = "Programming Languages"
        mock_trending_topic.trend_score = 75.0
        mock_trending_topic.video_count = 1
        mock_trending_topic.to_dict.return_value = {
            "topic_name": "Python Tutorial",
            "category": "Programming Languages",
            "trend_score": 75.0,
            "video_count": 1,
            "top_videos": [],
            "fetched_at": "2024-01-15T10:00:00Z"
        }
        
        mock_agent.analyzer.analyze_trends.return_value = [mock_trending_topic]
        
        # Call method
        result = mock_agent.get_trending_topics(
            keywords=["python tutorial"],
            days_back=7,
            min_views=1000
        )
        
        # Verify cache was checked
        assert mock_agent.cache.get.called
        
        # Verify API client was called
        assert mock_agent.api_client.search_videos.called
        assert mock_agent.api_client.get_video_details.called
        
        # Verify analyzer was called
        assert mock_agent.analyzer.analyze_trends.called
        
        # Verify cache was updated
        assert mock_agent.cache.set.called
        
        # Verify result structure
        assert "topics" in result
        assert "metadata" in result
        assert len(result["topics"]) == 1
    
    def test_uses_default_keywords_when_none_provided(self, mock_agent):
        """Test that default keywords are used when none provided."""
        mock_agent.cache.get.return_value = None
        mock_agent.api_client.search_videos.return_value = []
        
        # Call without keywords
        result = mock_agent.get_trending_topics()
        
        # Verify search was called with default keywords
        assert mock_agent.api_client.search_videos.call_count == len(
            mock_agent.config.default_keywords
        )
    
    def test_filters_by_minimum_view_count(self, mock_agent):
        """Test that videos are filtered by minimum view count."""
        mock_agent.cache.get.return_value = None
        
        mock_agent.api_client.search_videos.return_value = [
            {'video_id': 'video1', 'title': 'Video 1', 'description': '', 
             'channel_id': 'ch1', 'channel_title': 'Channel 1', 'published_at': '2024-01-10T10:00:00Z'}
        ]
        
        # Return videos with different view counts
        mock_agent.api_client.get_video_details.return_value = [
            {
                'video_id': 'video1',
                'title': 'Low Views Video',
                'description': '',
                'channel_title': 'Channel',
                'published_at': datetime(2024, 1, 10, tzinfo=timezone.utc),
                'view_count': 500,  # Below threshold
                'like_count': 10,
                'comment_count': 2
            },
            {
                'video_id': 'video2',
                'title': 'High Views Video',
                'description': '',
                'channel_title': 'Channel',
                'published_at': datetime(2024, 1, 10, tzinfo=timezone.utc),
                'view_count': 5000,  # Above threshold
                'like_count': 100,
                'comment_count': 20
            }
        ]
        
        mock_agent.analyzer.analyze_trends.return_value = []
        
        # Call with min_views=1000
        result = mock_agent.get_trending_topics(min_views=1000)
        
        # Verify analyzer received only filtered videos
        call_args = mock_agent.analyzer.analyze_trends.call_args
        filtered_videos = call_args[1]['videos']
        
        # Should only have the high views video
        assert len(filtered_videos) == 1
        assert filtered_videos[0]['view_count'] >= 1000
    
    def test_empty_response_when_no_videos_found(self, mock_agent):
        """Test that empty response is returned when no videos found."""
        mock_agent.cache.get.return_value = None
        mock_agent.api_client.search_videos.return_value = []
        
        result = mock_agent.get_trending_topics()
        
        assert result["topics"] == []
        assert result["metadata"]["total_videos_analyzed"] == 0
        assert result["metadata"]["average_trend_score"] == 0.0


class TestCacheKeyGeneration:
    """Tests for cache key generation."""
    
    def test_cache_key_consistent_for_same_params(self):
        """Test that same parameters generate same cache key."""
        config = {"youtube_api_key": "test_key"}
        agent = ResearchAgent(config=config)
        
        key1 = agent._generate_cache_key(["python", "devops"], 7, 1000)
        key2 = agent._generate_cache_key(["python", "devops"], 7, 1000)
        
        assert key1 == key2
    
    def test_cache_key_different_for_different_params(self):
        """Test that different parameters generate different cache keys."""
        config = {"youtube_api_key": "test_key"}
        agent = ResearchAgent(config=config)
        
        key1 = agent._generate_cache_key(["python"], 7, 1000)
        key2 = agent._generate_cache_key(["devops"], 7, 1000)
        
        assert key1 != key2
    
    def test_cache_key_order_independent(self):
        """Test that keyword order doesn't affect cache key."""
        config = {"youtube_api_key": "test_key"}
        agent = ResearchAgent(config=config)
        
        key1 = agent._generate_cache_key(["python", "devops"], 7, 1000)
        key2 = agent._generate_cache_key(["devops", "python"], 7, 1000)
        
        assert key1 == key2


class TestOutputValidation:
    """Tests for output schema validation."""
    
    def test_valid_output_passes_validation(self):
        """Test that valid output passes validation."""
        config = {"youtube_api_key": "test_key"}
        agent = ResearchAgent(config=config)
        
        valid_output = {
            "topics": [
                {
                    "topic_name": "Python Tutorial",
                    "category": "Programming Languages",
                    "trend_score": 75.0,
                    "video_count": 1,
                    "top_videos": [
                        {
                            "video_id": "video1",
                            "title": "Python Tutorial",
                            "channel": "Tech Channel",
                            "view_count": 5000,
                            "published_at": "2024-01-10T10:00:00Z"
                        }
                    ],
                    "fetched_at": "2024-01-15T10:00:00Z",
                    "finance_context": {
                        "stock_tickers": [],
                        "mentioned_companies": [],
                        "macro_relevance_score": 0.0,
                        "authority_channel_match": False
                    }
                }
            ],
            "metadata": {
                "query_date": "2024-01-15T10:00:00Z",
                "total_videos_analyzed": 1,
                "average_trend_score": 75.0,
                "macro_mode_enabled": False,
                "authority_channels_checked": 0
            }
        }
        
        # Should not raise exception
        agent._validate_output(valid_output)
    
    def test_missing_topics_field_raises_error(self):
        """Test that missing topics field raises validation error."""
        config = {"youtube_api_key": "test_key"}
        agent = ResearchAgent(config=config)
        
        invalid_output = {
            "metadata": {
                "query_date": "2024-01-15T10:00:00Z",
                "total_videos_analyzed": 0,
                "average_trend_score": 0.0
            }
        }
        
        with pytest.raises(SchemaValidationError) as exc_info:
            agent._validate_output(invalid_output)
        
        assert "topics" in str(exc_info.value)
    
    def test_too_many_top_videos_raises_error(self):
        """Test that more than 5 top videos raises validation error."""
        config = {"youtube_api_key": "test_key"}
        agent = ResearchAgent(config=config)
        
        invalid_output = {
            "topics": [
                {
                    "topic_name": "Test",
                    "category": "Test",
                    "trend_score": 50.0,
                    "video_count": 6,
                    "top_videos": [{"video_id": f"v{i}", "title": f"Video {i}", 
                                   "channel": "Ch", "view_count": 1000, 
                                   "published_at": "2024-01-10T10:00:00Z"} 
                                  for i in range(6)],  # 6 videos (too many)
                    "fetched_at": "2024-01-15T10:00:00Z"
                }
            ],
            "metadata": {
                "query_date": "2024-01-15T10:00:00Z",
                "total_videos_analyzed": 6,
                "average_trend_score": 50.0
            }
        }
        
        with pytest.raises(SchemaValidationError) as exc_info:
            agent._validate_output(invalid_output)
        
        assert "too many top_videos" in str(exc_info.value)


class TestMacroModeIntegration:
    """Integration tests for macro mode in ResearchAgent (Task 19.8)."""

    @pytest.fixture
    def macro_agent(self):
        """Create a ResearchAgent with mocked components for macro mode testing."""
        config = {
            "youtube_api_key": "test_api_key_macro",
            "daily_quota_limit": 100000,
            "cache_ttl_hours": 6,
            "default_keywords": ["python tutorial"],
            "min_trend_score": 30,
            "max_videos_per_query": 50,
            "max_videos_per_authority_channel": 5,
            "topic_similarity_threshold": 0.3,
            "macro_bonus_multiplier": 2.0,
        }
        agent = ResearchAgent(config=config)
        agent.cache = Mock()
        agent.api_client = Mock()
        agent.analyzer = Mock()
        return agent

    def _make_mock_trending(self, name, score=50.0):
        """Helper to create a mock TrendingTopic."""
        mt = Mock(spec=TrendingTopic)
        mt.topic_name = name
        mt.trend_score = score
        mt.to_dict.return_value = {
            "topic_name": name,
            "category": "Programming Languages",
            "trend_score": score,
            "video_count": 1,
            "top_videos": [
                {
                    "video_id": "v1",
                    "title": name,
                    "channel": "TechCh",
                    "view_count": 5000,
                    "published_at": "2024-01-10T00:00:00Z",
                }
            ],
            "fetched_at": "2024-01-15T00:00:00Z",
        }
        return mt

    def _setup_api_mocks(self, agent, video_title="Python Tutorial"):
        """Set up common API mock responses."""
        agent.cache.get.return_value = None
        agent.api_client.search_videos.return_value = [
            {
                "video_id": "v1",
                "title": video_title,
                "description": "Learn Python $NVDA NVIDIA",
                "channel_id": "ch1",
                "channel_title": "TechCh",
                "published_at": "2024-01-10T00:00:00Z",
            }
        ]
        agent.api_client.get_video_details.return_value = [
            {
                "video_id": "v1",
                "title": video_title,
                "description": "Learn Python $NVDA NVIDIA",
                "channel_title": "TechCh",
                "published_at": datetime(2024, 1, 10, tzinfo=timezone.utc),
                "view_count": 5000,
                "like_count": 100,
                "comment_count": 20,
            }
        ]

    def test_macro_mode_true_end_to_end(self, macro_agent):
        """Test end-to-end flow with macro_mode=True."""
        self._setup_api_mocks(macro_agent)
        mock_topic = self._make_mock_trending("Python Tutorial", 50.0)
        macro_agent.analyzer.analyze_trends.return_value = [mock_topic]

        # Mock the CrossReferenceEngine
        mock_engine = Mock()
        mock_engine.fetch_authority_content.return_value = [
            {
                "video_id": "auth_v1",
                "title": "Python in Finance",
                "description": "Python for trading $NVDA",
                "authority_channel": "Bloomberg Technology",
            }
        ]
        mock_engine.match_topics.return_value = {"Python Tutorial": True}
        mock_engine.apply_macro_bonus.return_value = [
            {
                "topic_name": "Python Tutorial",
                "category": "Programming Languages",
                "trend_score": 100.0,
                "video_count": 1,
                "top_videos": [
                    {
                        "video_id": "v1",
                        "title": "Python Tutorial",
                        "channel": "TechCh",
                        "view_count": 5000,
                        "published_at": "2024-01-10T00:00:00Z",
                    }
                ],
                "fetched_at": "2024-01-15T00:00:00Z",
            }
        ]
        mock_engine.calculate_similarity.return_value = 0.5
        mock_engine.build_finance_context.return_value = {
            "stock_tickers": ["NVDA"],
            "mentioned_companies": ["NVIDIA"],
            "macro_relevance_score": 0.75,
            "authority_channel_match": True,
        }
        macro_agent.cross_reference_engine = mock_engine

        result = macro_agent.get_trending_topics(
            keywords=["python"], macro_mode=True
        )

        # Verify macro mode metadata
        assert result["metadata"]["macro_mode_enabled"] is True
        assert result["metadata"]["authority_channels_checked"] == 7

        # Verify finance_context is populated
        assert len(result["topics"]) == 1
        fc = result["topics"][0]["finance_context"]
        assert fc["authority_channel_match"] is True
        assert fc["macro_relevance_score"] > 0.0
        assert "NVDA" in fc["stock_tickers"]
        assert "NVIDIA" in fc["mentioned_companies"]

        # Verify cross-reference engine was called
        mock_engine.fetch_authority_content.assert_called_once()
        mock_engine.match_topics.assert_called_once()
        mock_engine.apply_macro_bonus.assert_called_once()

    def test_macro_mode_false_end_to_end(self, macro_agent):
        """Test end-to-end flow with macro_mode=False."""
        self._setup_api_mocks(macro_agent)
        mock_topic = self._make_mock_trending("Python Tutorial", 50.0)
        macro_agent.analyzer.analyze_trends.return_value = [mock_topic]

        result = macro_agent.get_trending_topics(
            keywords=["python"], macro_mode=False
        )

        # Verify standard mode metadata
        assert result["metadata"]["macro_mode_enabled"] is False
        assert result["metadata"]["authority_channels_checked"] == 0

        # Verify empty finance_context
        for topic in result["topics"]:
            fc = topic["finance_context"]
            assert fc["stock_tickers"] == []
            assert fc["mentioned_companies"] == []
            assert fc["macro_relevance_score"] == 0.0
            assert fc["authority_channel_match"] is False

        # Verify cross-reference engine was NOT used
        assert macro_agent.cross_reference_engine is None

    def test_macro_mode_quota_consumption(self, macro_agent):
        """Test quota consumption in macro mode."""
        self._setup_api_mocks(macro_agent)
        mock_topic = self._make_mock_trending("Python Tutorial", 50.0)
        macro_agent.analyzer.analyze_trends.return_value = [mock_topic]

        # Mock the CrossReferenceEngine
        mock_engine = Mock()
        authority_videos = [
            {
                "video_id": f"auth_v{i}",
                "title": f"Authority Video {i}",
                "description": "market analysis",
                "authority_channel": "Bloomberg Technology",
            }
            for i in range(35)  # 7 channels * 5 videos
        ]
        mock_engine.fetch_authority_content.return_value = authority_videos
        mock_engine.match_topics.return_value = {"Python Tutorial": False}
        mock_engine.apply_macro_bonus.return_value = [
            {
                "topic_name": "Python Tutorial",
                "category": "Programming Languages",
                "trend_score": 50.0,
                "video_count": 1,
                "top_videos": [
                    {
                        "video_id": "v1",
                        "title": "Python Tutorial",
                        "channel": "TechCh",
                        "view_count": 5000,
                        "published_at": "2024-01-10T00:00:00Z",
                    }
                ],
                "fetched_at": "2024-01-15T00:00:00Z",
            }
        ]
        mock_engine.calculate_similarity.return_value = 0.0
        mock_engine.build_finance_context.return_value = {
            "stock_tickers": [],
            "mentioned_companies": [],
            "macro_relevance_score": 0.0,
            "authority_channel_match": False,
        }
        macro_agent.cross_reference_engine = mock_engine

        result = macro_agent.get_trending_topics(
            keywords=["python"], macro_mode=True
        )

        # Verify authority content was fetched (this is the extra quota cost)
        mock_engine.fetch_authority_content.assert_called_once_with(
            max_videos_per_channel=5
        )

        # Verify the search API was also called (standard search cost)
        assert macro_agent.api_client.search_videos.called

        # Verify result is valid
        assert "topics" in result
        assert result["metadata"]["macro_mode_enabled"] is True

    def test_macro_mode_cache_behavior(self, macro_agent):
        """Test cache behavior with macro mode data."""
        # Setup cache to return macro mode cached data
        cached_macro_data = {
            "topics": [
                {
                    "topic_name": "AI Chips",
                    "category": "Technology",
                    "trend_score": 90.0,
                    "video_count": 3,
                    "top_videos": [
                        {
                            "video_id": "v1",
                            "title": "AI Chips",
                            "channel": "TechCh",
                            "view_count": 50000,
                            "published_at": "2024-01-10T00:00:00Z",
                        }
                    ],
                    "fetched_at": "2024-01-15T00:00:00Z",
                    "finance_context": {
                        "stock_tickers": ["NVDA", "AMD"],
                        "mentioned_companies": ["NVIDIA", "AMD"],
                        "macro_relevance_score": 0.75,
                        "authority_channel_match": True,
                    },
                }
            ],
            "metadata": {
                "query_date": "2024-01-15T10:00:00Z",
                "total_videos_analyzed": 50,
                "average_trend_score": 90.0,
                "macro_mode_enabled": True,
                "authority_channels_checked": 7,
            },
        }
        macro_agent.cache.get.return_value = cached_macro_data

        # Call with macro_mode=True — should hit cache
        result = macro_agent.get_trending_topics(
            keywords=["AI chips"], macro_mode=True
        )

        # Verify cache was used (no API calls)
        assert not macro_agent.api_client.search_videos.called
        assert not macro_agent.api_client.get_video_details.called

        # Verify cached data returned intact
        assert result == cached_macro_data
        assert result["metadata"]["macro_mode_enabled"] is True
        assert result["topics"][0]["finance_context"]["authority_channel_match"] is True

        # Now call with macro_mode=False — different cache key, should miss
        macro_agent.cache.get.return_value = None
        macro_agent.api_client.search_videos.return_value = []

        result_standard = macro_agent.get_trending_topics(
            keywords=["AI chips"], macro_mode=False
        )

        # This time API was called (cache miss for standard mode key)
        assert result_standard["metadata"]["macro_mode_enabled"] is False
