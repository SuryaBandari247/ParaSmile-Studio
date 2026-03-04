"""
Research Agent - Main interface for trending topic discovery.

This module provides the ResearchAgent class that orchestrates all components
(API client, rate limiter, analyzer, cache, config, logger) to provide a simple
get_trending_topics() method for discovering trending technical topics from YouTube.
"""

import hashlib
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

from research_agent.analyzer import TopicAnalyzer
from research_agent.api_client import YouTubeAPIClient
from research_agent.cache import TopicCache
from research_agent.config import ConfigManager
from research_agent.cross_reference import CrossReferenceEngine
from research_agent.exceptions import (
    AuthenticationError,
    SchemaValidationError,
    SourceUnavailableError,
)
from research_agent.google_trends_client import GoogleTrendsClient
from research_agent.logger import setup_logging
from research_agent.models import ResearchAgentConfig, StoryPitch
from research_agent.pitch_generator import PitchGenerator
from research_agent.rate_limiter import APIRateLimiter
from research_agent.reddit_client import RedditClient
from research_agent.topic_selector import TopicSelector
from research_agent.wikipedia_events_client import WikipediaEventsClient
from research_agent.yahoo_finance_client import YahooFinanceClient


class ResearchAgent:
    """
    Main interface for trending topic discovery.
    Orchestrates API client, analyzer, and cache components.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize research agent with configuration.
        
        Args:
            config: Configuration dictionary or None for defaults
            
        Raises:
            AuthenticationError: If YouTube API key missing/invalid
        """
        # Load environment variables
        load_dotenv()
        
        # Load configuration
        config_manager = ConfigManager()
        if config:
            self.config = config_manager.load_from_dict(config)
        else:
            self.config = config_manager.load_config()
        
        # Set up logging
        self.logger = setup_logging(
            log_level=self.config.log_level,
            structured=self.config.structured_logging
        )
        
        self.logger.info("Initializing Research Agent")
        
        # Initialize rate limiter
        self.rate_limiter = APIRateLimiter(daily_quota=self.config.daily_quota_limit)
        
        # Initialize YouTube API client
        self.api_client = YouTubeAPIClient(
            api_key=self.config.youtube_api_key,
            rate_limiter=self.rate_limiter
        )
        
        # Initialize topic analyzer
        self.analyzer = TopicAnalyzer()
        
        # Initialize cache
        self.cache = TopicCache(
            cache_file=self.config.cache_file_path,
            ttl_hours=self.config.cache_ttl_hours
        )
        
        # Initialize cross-reference engine (lazy initialization)
        self.cross_reference_engine = None
        
        # Initialize multi-source data clients (all keyless)
        self.google_trends_client = GoogleTrendsClient(
            geo=getattr(self.config, 'google_trends_geo', ''),
        )
        self.reddit_client = RedditClient()
        self.yahoo_finance_client = YahooFinanceClient()
        self.wikipedia_events_client = WikipediaEventsClient()

        # Initialize PitchGenerator (requires OPENAI_API_KEY)
        self.pitch_generator = None
        self.topic_selector = None
        try:
            self.pitch_generator = PitchGenerator()
            self.topic_selector = TopicSelector(self.pitch_generator)
            self.logger.info("PitchGenerator and TopicSelector initialized")
        except (AuthenticationError, SourceUnavailableError) as e:
            self.logger.warning(
                "PitchGenerator unavailable (OPENAI_API_KEY missing?): %s", e
            )

        self.logger.info("Research Agent initialized successfully")
    
    def get_trending_topics(
        self,
        keywords: Optional[List[str]] = None,
        days_back: int = 7,
        min_views: int = 1000,
        macro_mode: bool = False
    ) -> Dict[str, Any]:
        """
        Discover trending technical topics from YouTube.
        
        Args:
            keywords: Seed keywords for search (None for defaults)
            days_back: Number of days to look back for videos (default: 7)
            min_views: Minimum view count threshold (default: 1000)
            macro_mode: Enable authority channel cross-referencing (default: False)
            
        Returns:
            Dictionary with structure:
            {
                "topics": [
                    {
                        "topic_name": str,
                        "category": str,
                        "trend_score": float,
                        "video_count": int,
                        "top_videos": [...],
                        "fetched_at": str (ISO 8601),
                        "finance_context": {
                            "stock_tickers": List[str],
                            "mentioned_companies": List[str],
                            "macro_relevance_score": float,
                            "authority_channel_match": bool
                        }
                    }
                ],
                "metadata": {
                    "query_date": str,
                    "total_videos_analyzed": int,
                    "average_trend_score": float,
                    "macro_mode_enabled": bool,
                    "authority_channels_checked": int
                }
            }
            
        Raises:
            QuotaExceededError: If API quota exhausted
            NetworkError: If network connectivity lost
            SchemaValidationError: If output validation fails
        """
        # Use default keywords if none provided
        if keywords is None:
            keywords = self.config.default_keywords
        
        # Generate cache key from query parameters
        cache_key = self._generate_cache_key(keywords, days_back, min_views, macro_mode)
        
        self.logger.info(
            f"get_trending_topics called: keywords={keywords}, "
            f"days_back={days_back}, min_views={min_views}, macro_mode={macro_mode}"
        )
        
        # Check cache for fresh data (< 6 hours)
        cached_data = self.cache.get(cache_key)
        if cached_data is not None:
            self.logger.info("Cache hit: returning cached results")
            return cached_data
        
        self.logger.info("Cache miss: fetching fresh data from YouTube API")
        
        # Calculate date range
        now = datetime.now(timezone.utc)
        published_after = now - timedelta(days=days_back)
        
        # Format dates in RFC 3339 format for YouTube API
        published_after_str = published_after.isoformat()
        published_before_str = now.isoformat()
        
        # Execute search query for each keyword
        all_videos = []
        for keyword in keywords:
            try:
                self.logger.debug(f"Searching for keyword: {keyword}")
                videos = self.api_client.search_videos(
                    query=keyword,
                    published_after=published_after_str,
                    published_before=published_before_str,
                    max_results=self.config.max_videos_per_query
                )
                all_videos.extend(videos)
            except Exception as e:
                self.logger.error(f"Failed to search for keyword '{keyword}': {e}")
                # Continue with other keywords
                continue
        
        if not all_videos:
            self.logger.warning("No videos found for any keywords")
            return self._create_empty_response(macro_mode)
        
        # Extract video IDs
        video_ids = [v['video_id'] for v in all_videos]
        
        # Fetch video details for all results
        self.logger.info(f"Fetching details for {len(video_ids)} videos")
        video_details = self.api_client.get_video_details(video_ids)
        
        # Filter by minimum view count
        filtered_videos = [
            v for v in video_details
            if v['view_count'] >= min_views
        ]
        
        self.logger.info(
            f"Filtered videos: {len(filtered_videos)}/{len(video_details)} "
            f"meet minimum view count of {min_views}"
        )
        
        # Analyze trends and calculate scores
        trending_topics = self.analyzer.analyze_trends(
            videos=filtered_videos,
            min_score=self.config.min_trend_score
        )
        
        # Convert to dictionaries for processing
        topics_dicts = [topic.to_dict() for topic in trending_topics]
        
        # Macro mode processing
        authority_channels_checked = 0
        if macro_mode:
            self.logger.info("Macro mode enabled: fetching authority channel content")
            
            # Initialize cross-reference engine if needed
            if self.cross_reference_engine is None:
                self.cross_reference_engine = CrossReferenceEngine(self.api_client)
            
            try:
                # Fetch authority content
                authority_videos = self.cross_reference_engine.fetch_authority_content(
                    max_videos_per_channel=self.config.max_videos_per_authority_channel
                )
                authority_channels_checked = len(self.config.authority_channels)
                
                # Match topics with authority content
                match_status = self.cross_reference_engine.match_topics(
                    technical_topics=topics_dicts,
                    authority_videos=authority_videos,
                    similarity_threshold=self.config.topic_similarity_threshold
                )
                
                # Apply macro bonus to matched topics
                topics_dicts = self.cross_reference_engine.apply_macro_bonus(
                    topics=topics_dicts,
                    match_status=match_status
                )
                
                # Build finance context for each topic
                for topic_dict in topics_dicts:
                    topic_name = topic_dict['topic_name']
                    is_matched = match_status.get(topic_name, False)
                    
                    # Get matched authority videos for this topic
                    matched_videos = [v for v in authority_videos 
                                    if self.cross_reference_engine.calculate_similarity(topic_dict, v) 
                                    >= self.config.topic_similarity_threshold]
                    
                    finance_context = self.cross_reference_engine.build_finance_context(
                        topic=topic_dict,
                        authority_match=is_matched,
                        authority_videos=matched_videos
                    )
                    topic_dict['finance_context'] = finance_context
                
                self.logger.info("Macro mode processing complete")
                
            except Exception as e:
                self.logger.error(f"Macro mode processing failed: {e}")
                # Fall back to standard mode with empty finance context
                for topic_dict in topics_dicts:
                    topic_dict['finance_context'] = self._create_empty_finance_context()
        else:
            # Standard mode: add empty finance context
            for topic_dict in topics_dicts:
                topic_dict['finance_context'] = self._create_empty_finance_context()
        
        # Store results in cache with timestamp
        result = self._format_output(topics_dicts, len(video_details), macro_mode, authority_channels_checked)
        self.cache.set(cache_key, result)
        
        self.logger.info(
            f"Analysis complete: {len(topics_dicts)} trending topics identified"
        )
        
        return result

    def get_trending_topics_multi_source(self) -> List[Dict[str, Any]]:
        """
        Fetch trending topics from all 5 data sources, merge, deduplicate,
        score, and return a unified list sorted by trend_score descending.

        Sources: Google Trends, Reddit, Yahoo Finance, Wikipedia, YouTube.
        Each source is wrapped in try/except so a single failure doesn't
        break the pipeline.

        Returns:
            List of unified TrendingTopic dicts with source attribution,
            sorted by trend_score descending.
        """
        result = self.get_trending_topics_multi_source_detailed()
        return result["unified"]

    def get_trending_topics_multi_source_detailed(self) -> Dict[str, Any]:
        """
        Fetch trending topics from all 5 data sources and return both
        per-source raw results and the unified/aggregated list.

        Returns:
            Dict with keys:
                - "google_trends": raw Google Trends list
                - "reddit": raw Reddit posts list
                - "yahoo_finance": raw Yahoo Finance dict
                - "wikipedia": raw Wikipedia events list
                - "youtube": raw YouTube topics list
                - "unified": merged, deduped, scored list (same as get_trending_topics_multi_source)
        """
        self.logger.info("Starting multi-source trending topic fetch")

        # Ensure cross-reference engine is initialized
        if self.cross_reference_engine is None:
            self.cross_reference_engine = CrossReferenceEngine(self.api_client)

        # -- 1. Fetch from each source independently --
        google_trends: List[Dict[str, Any]] = []
        reddit_posts: List[Dict[str, Any]] = []
        yahoo_finance: Dict[str, Any] = {}
        wikipedia_events: List[Dict[str, Any]] = []
        youtube_topics: List[Dict[str, Any]] = []

        # Google Trends
        try:
            google_trends = self.google_trends_client.fetch_trends()
            self.logger.info("Google Trends: fetched %d trends", len(google_trends))
        except Exception as e:
            self.logger.warning("Google Trends unavailable: %s", e)

        # Reddit
        try:
            reddit_posts = self.reddit_client.fetch_hot_posts()
            self.logger.info("Reddit: fetched %d posts", len(reddit_posts))
        except Exception as e:
            self.logger.warning("Reddit unavailable: %s", e)

        # Yahoo Finance
        try:
            yahoo_finance = self.yahoo_finance_client.fetch_market_movers()
            self.logger.info("Yahoo Finance: fetched market movers")
        except Exception as e:
            self.logger.warning("Yahoo Finance unavailable: %s", e)

        # Wikipedia
        try:
            wikipedia_events = self.wikipedia_events_client.fetch_current_events()
            self.logger.info("Wikipedia: fetched %d events", len(wikipedia_events))
        except Exception as e:
            self.logger.warning("Wikipedia unavailable: %s", e)

        # YouTube (reuse existing pipeline)
        try:
            yt_result = self.get_trending_topics()
            youtube_topics = yt_result.get("topics", [])
            self.logger.info("YouTube: fetched %d topics", len(youtube_topics))
        except Exception as e:
            self.logger.warning("YouTube unavailable: %s", e)

        # -- 2. Merge all sources --
        unified = self.cross_reference_engine.merge_all_sources(
            google_trends=google_trends,
            reddit_posts=reddit_posts,
            yahoo_finance=yahoo_finance,
            wikipedia_events=wikipedia_events,
            youtube_topics=youtube_topics,
        )
        self.logger.info("Merged %d topics from all sources", len(unified))

        # -- 3. Deduplicate with 0.75 similarity threshold --
        unified = self.cross_reference_engine.deduplicate_topics(
            unified, similarity_threshold=0.75
        )
        self.logger.info("After deduplication: %d topics", len(unified))

        # -- 4. Calculate cross-source scores --
        for topic in unified:
            topic["trend_score"] = self.cross_reference_engine.calculate_cross_source_score(topic)

        # -- 5. Mark high-confidence topics (3+ sources) --
        unified = self.cross_reference_engine.mark_high_confidence(unified)

        # -- 6. Sort by trend_score descending --
        unified.sort(key=lambda t: t.get("trend_score", 0), reverse=True)

        # -- 7. Enrich finance_context with Yahoo Finance real-time data --
        for topic in unified:
            fc = topic.get("finance_context", self._create_empty_finance_context())
            tickers = fc.get("stock_tickers", [])
            if tickers:
                enrichment = self.yahoo_finance_client.enrich_finance_context(tickers)
                fc["real_time_data"] = enrichment
            topic["finance_context"] = fc

        self.logger.info(
            "Multi-source pipeline complete: %d unified topics", len(unified)
        )
        return {
            "google_trends": google_trends,
            "reddit": reddit_posts,
            "yahoo_finance": yahoo_finance,
            "wikipedia": wikipedia_events,
            "youtube": youtube_topics,
            "unified": unified,
        }

    def generate_and_select_pitch(
        self,
        unified_topics: List[Dict[str, Any]],
    ) -> StoryPitch:
        """
        Generate story pitches from unified topics and present for human selection.

        Args:
            unified_topics: Unified topic list from get_trending_topics_multi_source().

        Returns:
            The selected StoryPitch dataclass.

        Raises:
            RuntimeError: If PitchGenerator or TopicSelector is not available.
        """
        if self.pitch_generator is None or self.topic_selector is None:
            raise RuntimeError(
                "PitchGenerator/TopicSelector not available. "
                "Ensure OPENAI_API_KEY is set in the environment."
            )

        self.logger.info(
            "Generating pitches from %d unified topics", len(unified_topics)
        )

        # Generate pitch board
        board = self.pitch_generator.generate_pitches(unified_topics)

        # Present board and get human selection
        selected = self.topic_selector.present_and_select(board, unified_topics)

        self.logger.info("Selected pitch: %s", selected.title)
        return selected

    def _generate_cache_key(
        self,
        keywords: List[str],
        days_back: int,
        min_views: int,
        macro_mode: bool = False
    ) -> str:
        """
        Generate cache key from query parameters.
        
        Args:
            keywords: Search keywords
            days_back: Number of days to look back
            min_views: Minimum view count
            macro_mode: Whether macro mode is enabled
            
        Returns:
            Cache key string (hash of parameters)
        """
        # Sort keywords for consistent hashing
        sorted_keywords = sorted(keywords)
        
        # Create parameter string
        params = f"{','.join(sorted_keywords)}|{days_back}|{min_views}|{macro_mode}"
        
        # Generate hash
        return hashlib.md5(params.encode()).hexdigest()
    
    def _format_output(
        self,
        trending_topics: List,
        total_videos: int,
        macro_mode: bool = False,
        authority_channels_checked: int = 0
    ) -> Dict[str, Any]:
        """
        Format trending topics into output structure.
        
        Args:
            trending_topics: List of TrendingTopic objects or dictionaries
            total_videos: Total number of videos analyzed
            macro_mode: Whether macro mode was enabled
            authority_channels_checked: Number of authority channels checked
            
        Returns:
            Formatted output dictionary
        """
        # Convert TrendingTopic objects to dictionaries if needed
        if trending_topics and hasattr(trending_topics[0], 'to_dict'):
            topics_list = [topic.to_dict() for topic in trending_topics]
        else:
            topics_list = trending_topics
        
        # Calculate average trend score
        if topics_list:
            avg_score = sum(t['trend_score'] for t in topics_list) / len(topics_list)
        else:
            avg_score = 0.0
        
        # Create output structure
        output = {
            "topics": topics_list,
            "metadata": {
                "query_date": datetime.now(timezone.utc).isoformat(),
                "total_videos_analyzed": total_videos,
                "average_trend_score": avg_score,
                "macro_mode_enabled": macro_mode,
                "authority_channels_checked": authority_channels_checked
            }
        }
        
        # Validate output schema
        self._validate_output(output)
        
        return output
    
    def _validate_output(self, output: Dict[str, Any]) -> None:
        """
        Validate output schema before returning results.
        
        Args:
            output: Output dictionary to validate
            
        Raises:
            SchemaValidationError: If validation fails
        """
        violations = []
        
        # Check top-level structure
        if "topics" not in output:
            violations.append("Missing 'topics' field")
        if "metadata" not in output:
            violations.append("Missing 'metadata' field")
        
        # Check topics structure
        if "topics" in output:
            for i, topic in enumerate(output["topics"]):
                required_fields = [
                    "topic_name", "category", "trend_score",
                    "video_count", "top_videos", "fetched_at", "finance_context"
                ]
                for field in required_fields:
                    if field not in topic:
                        violations.append(f"Topic {i}: missing '{field}' field")
                
                # Check finance_context structure
                if "finance_context" in topic:
                    fc = topic["finance_context"]
                    fc_required = [
                        "stock_tickers", "mentioned_companies",
                        "macro_relevance_score", "authority_channel_match"
                    ]
                    for field in fc_required:
                        if field not in fc:
                            violations.append(f"Topic {i}: finance_context missing '{field}' field")
                    
                    # Validate macro_relevance_score bounds
                    if "macro_relevance_score" in fc:
                        score = fc["macro_relevance_score"]
                        if not (0.0 <= score <= 1.0):
                            violations.append(
                                f"Topic {i}: macro_relevance_score {score} outside valid range [0, 1]"
                            )
                
                # Check top_videos structure
                if "top_videos" in topic:
                    if len(topic["top_videos"]) > 5:
                        violations.append(f"Topic {i}: too many top_videos (max 5)")
                    
                    for j, video in enumerate(topic["top_videos"]):
                        video_required = [
                            "video_id", "title", "channel",
                            "view_count", "published_at"
                        ]
                        for field in video_required:
                            if field not in video:
                                violations.append(
                                    f"Topic {i}, video {j}: missing '{field}' field"
                                )
        
        # Check metadata structure
        if "metadata" in output:
            metadata_required = [
                "query_date", "total_videos_analyzed", "average_trend_score",
                "macro_mode_enabled", "authority_channels_checked"
            ]
            for field in metadata_required:
                if field not in output["metadata"]:
                    violations.append(f"Metadata: missing '{field}' field")
        
        if violations:
            raise SchemaValidationError(violations)
    
    def _create_empty_response(self, macro_mode: bool = False) -> Dict[str, Any]:
        """
        Create empty response when no videos found.
        
        Args:
            macro_mode: Whether macro mode was enabled
            
        Returns:
            Empty response dictionary
        """
        return {
            "topics": [],
            "metadata": {
                "query_date": datetime.now(timezone.utc).isoformat(),
                "total_videos_analyzed": 0,
                "average_trend_score": 0.0,
                "macro_mode_enabled": macro_mode,
                "authority_channels_checked": 0
            }
        }
    
    def _create_empty_finance_context(self) -> Dict[str, Any]:
        """
        Create empty finance context for standard mode.
        
        Returns:
            Empty finance context dictionary
        """
        return {
            'stock_tickers': [],
            'mentioned_companies': [],
            'macro_relevance_score': 0.0,
            'authority_channel_match': False
        }
