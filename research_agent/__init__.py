"""
Research Agent - Multi-source trend discovery and story pitch generation.

This module provides functionality to discover and analyze trending topics
from multiple data sources (YouTube, Google Trends, Reddit, Yahoo Finance,
Wikipedia) and generate story pitches using GPT-4o-mini for Calm Capitalist.
"""

__version__ = "0.2.0"

# Main interface
from research_agent.agent import ResearchAgent

# Data source clients
from research_agent.google_trends_client import GoogleTrendsClient
from research_agent.reddit_client import RedditClient
from research_agent.yahoo_finance_client import YahooFinanceClient
from research_agent.wikipedia_events_client import WikipediaEventsClient

# Pitch generation and selection
from research_agent.pitch_generator import PitchGenerator
from research_agent.topic_selector import TopicSelector

# Data models
from research_agent.models import (
    TrendingTopic,
    VideoMetadata,
    SourceTrend,
    StoryPitch,
    StoryPitchBoard,
)

# Exceptions
from research_agent.exceptions import (
    ResearchAgentError,
    AuthenticationError,
    QuotaExceededError,
    NetworkError,
    ParseError,
    SchemaValidationError,
    CacheCorruptionError,
    SourceUnavailableError,
    PitchGenerationError,
)

__all__ = [
    # Main interface
    "ResearchAgent",
    # Data source clients
    "GoogleTrendsClient",
    "RedditClient",
    "YahooFinanceClient",
    "WikipediaEventsClient",
    # Pitch generation and selection
    "PitchGenerator",
    "TopicSelector",
    # Data models
    "TrendingTopic",
    "VideoMetadata",
    "SourceTrend",
    "StoryPitch",
    "StoryPitchBoard",
    # Exceptions
    "ResearchAgentError",
    "AuthenticationError",
    "QuotaExceededError",
    "NetworkError",
    "ParseError",
    "SchemaValidationError",
    "CacheCorruptionError",
    "SourceUnavailableError",
    "PitchGenerationError",
]
