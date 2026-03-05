# Implementation Plan: Research Agent

## Overview

This plan implements a Python-based YouTube Data API scraper for discovering trending technical topics. The implementation prioritizes API client functionality (Requirement 1) and rate limiting (Requirement 4) as the foundation, then builds out trend analysis, caching, and supporting components.

The architecture follows a modular design with clear separation of concerns: API client handles external communication, rate limiter manages quota, analyzer processes data, and cache reduces API calls.

## Tasks

- [x] 1. Set up project structure and dependencies
  - Create `research_agent/` package directory with `__init__.py`
  - Create `.env.example` file with `YOUTUBE_API_KEY` placeholder
  - Create `requirements.txt` with dependencies: `google-api-python-client`, `python-dotenv`, `hypothesis`, `pytest`, `responses`
  - Create `.cache/` directory for topic cache storage
  - _Requirements: 1.1, 4.1_

- [x] 2. Implement API Rate Limiter
  - [x] 2.1 Create `research_agent/rate_limiter.py` with `APIRateLimiter` class
    - Implement `__init__` to set daily quota limit (default 10,000 units)
    - Implement `check_quota(cost)` to verify sufficient quota available
    - Implement `consume_quota(cost)` to track quota consumption
    - Implement `get_remaining_quota()` to return remaining units
    - Implement quota state persistence to track consumption across restarts
    - Add 80% warning threshold logging
    - Add 95% circuit breaker logic to prevent new calls
    - _Requirements: 4.1, 4.2, 4.3, 4.4_
  
  - [x] 2.2 Write property test for quota tracking accuracy
    - **Property 12: Quota consumption tracking accuracy**
    - **Validates: Requirements 4.1**
  
  - [x] 2.3 Write unit tests for rate limiter edge cases
    - Test quota at exactly 80% threshold (warning logged)
    - Test quota at exactly 95% threshold (calls blocked)
    - Test quota reset functionality
    - _Requirements: 4.2, 4.3_

- [x] 3. Implement exception hierarchy
  - [x] 3.1 Create `research_agent/exceptions.py` with custom exceptions
    - Implement `ResearchAgentError` base exception
    - Implement `AuthenticationError` for invalid API keys
    - Implement `QuotaExceededError` with reset timestamp
    - Implement `NetworkError` for connectivity issues
    - Implement `ParseError` with raw response storage
    - Implement `SchemaValidationError` with violation list
    - Implement `CacheCorruptionError` for cache failures
    - _Requirements: 1.2, 1.4, 8.1, 8.2, 8.3, 9.5_

- [x] 4. Implement YouTube API Client
  - [x] 4.1 Create `research_agent/api_client.py` with `YouTubeAPIClient` class
    - Load `YOUTUBE_API_KEY` from `.env` file using `python-dotenv`
    - Implement `__init__` to authenticate with YouTube Data API v3
    - Validate API key is present and non-empty, raise `AuthenticationError` if invalid
    - Store reference to `APIRateLimiter` instance
    - _Requirements: 1.1, 1.2, 1.3_
  
  - [x] 4.2 Implement search functionality in `YouTubeAPIClient`
    - Implement `search_videos(query, published_after, published_before, max_results)` method
    - Pre-flight quota check (search costs 100 units)
    - Build YouTube API search request with date filters
    - Parse response into list of video metadata dictionaries
    - Handle 403 quota errors and raise `QuotaExceededError`
    - Consume quota after successful request
    - _Requirements: 1.3, 1.4, 2.1, 2.3, 4.4_
  
  - [x] 4.3 Implement video details fetching in `YouTubeAPIClient`
    - Implement `get_video_details(video_ids)` method
    - Pre-flight quota check (1 unit per video)
    - Batch video IDs into groups of 50 (API limit)
    - Parse response to extract view count, like count, comment count
    - _Requirements: 1.3, 3.1, 4.4_
  
  - [x] 4.4 Implement retry logic with exponential backoff
    - Add retry decorator for 5xx server errors
    - Retry up to 3 times with delays: 1s, 2s, 4s
    - Log each retry attempt with context
    - Raise `NetworkError` after final failure
    - Set 30-second timeout for all requests
    - _Requirements: 8.1, 8.2_
  
  - [x] 4.5 Write property test for API authentication
    - **Property 1: Invalid API keys raise AuthenticationError**
    - **Validates: Requirements 1.2**
  
  - [x] 4.6 Write property test for API version
    - **Property 2: API endpoints use v3 version**
    - **Validates: Requirements 1.3**
  
  - [x] 4.7 Write unit tests for API client
    - Test missing API key raises `AuthenticationError`
    - Test invalid API key raises `AuthenticationError`
    - Test quota exceeded returns `QuotaExceededError`
    - Test network timeout after 30 seconds
    - Test retry logic for 5xx errors
    - _Requirements: 1.2, 1.4, 8.1, 8.2_

- [x] 5. Checkpoint - Ensure API client and rate limiter work correctly
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement data models
  - [x] 6.1 Create `research_agent/models.py` with dataclasses
    - Implement `VideoMetadata` dataclass with all required fields
    - Implement `TrendingTopic` dataclass with `to_dict()` method
    - Implement `QuotaState` dataclass with `usage_percentage()` method
    - Implement `ResearchAgentConfig` dataclass with default values
    - _Requirements: 9.1, 9.2, 9.3_
  
  - [x] 6.2 Write property test for output schema completeness
    - **Property 28: Output schema completeness**
    - **Validates: Requirements 9.1**

- [x] 7. Implement Topic Analyzer
  - [x] 7.1 Create `research_agent/analyzer.py` with `TopicAnalyzer` class
    - Implement `calculate_trend_score(video)` method
    - Use weighted formula: 40% view count, 30% engagement rate, 30% recency
    - Apply 2x multiplier for videos published within 24 hours
    - Normalize score to 0-100 range
    - _Requirements: 3.1, 3.2, 3.3_
  
  - [x] 7.2 Implement topic classification in `TopicAnalyzer`
    - Implement `classify_topic(video)` method
    - Define keyword patterns for categories: Programming Languages, DevOps, Cloud Infrastructure, Software Architecture, Security, Data Engineering
    - Analyze title, description, and tags for classification
    - Return category and confidence score (0-1)
    - Mark as "Uncategorized" if confidence < 0.6
    - _Requirements: 6.1, 6.2, 6.3, 6.4_
  
  - [x] 7.3 Implement trend analysis in `TopicAnalyzer`
    - Implement `analyze_trends(videos, min_score)` method
    - Calculate trend score for each video
    - Classify each video into technical category
    - Filter videos with score < min_score (default 30)
    - Group videos by topic name
    - Rank topics by trend score (descending), tie-break by view count
    - Return list of `TrendingTopic` objects
    - _Requirements: 2.2, 2.4, 2.5, 3.4, 3.5, 6.5_
  
  - [x] 7.4 Write property test for trend score normalization
    - **Property 10: Trend score normalization**
    - **Validates: Requirements 3.3**
  
  - [x] 7.5 Write property test for recency boost
    - **Property 9: Recency boost for recent videos**
    - **Validates: Requirements 3.2**
  
  - [x] 7.6 Write property test for sorting with tie-breaking
    - **Property 7: Topics sorted by trend score with tie-breaking**
    - **Validates: Requirements 2.5, 3.4**
  
  - [x] 7.7 Write unit tests for analyzer
    - Test video with zero views/likes/comments
    - Test all videos have identical trend scores
    - Test classification confidence below 0.6 marked as "Uncategorized"
    - Test minimum trend score filtering (< 30 excluded)
    - _Requirements: 3.3, 3.5, 6.4_

- [x] 8. Implement Topic Cache
  - [x] 8.1 Create `research_agent/cache.py` with `TopicCache` class
    - Implement `__init__` with cache file path and TTL (default 6 hours)
    - Implement `get(key)` to retrieve cached data if fresh (< TTL)
    - Implement `set(key, data)` to store data with timestamp
    - Implement `invalidate(key)` to remove specific entry
    - Implement `clear()` to delete entire cache
    - Use atomic writes to prevent corruption
    - Handle JSON decode errors gracefully (delete and continue)
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_
  
  - [x] 8.2 Write property test for cache round-trip
    - **Property 14: Cache round-trip preserves data**
    - **Validates: Requirements 5.1, 5.4**
  
  - [x] 8.3 Write unit tests for cache
    - Test cache file doesn't exist on first run
    - Test cache corruption triggers fresh data fetch
    - Test fresh cache (< 6 hours) returns cached data
    - Test stale cache (> 6 hours) triggers API refresh
    - _Requirements: 5.2, 5.3, 5.5_

- [x] 9. Implement configuration management
  - [x] 9.1 Create `research_agent/config.py` with `ConfigManager` class
    - Implement `load_config(file_path)` to parse YAML/JSON config files
    - Implement default configuration values from `ResearchAgentConfig` dataclass
    - Support environment variable overrides for sensitive values
    - Validate configuration schema
    - _Requirements: 7.4, 7.5_
  
  - [x] 9.2 Write unit tests for configuration
    - Test default configuration applied when no file provided
    - Test YAML configuration file parsing
    - Test JSON configuration file parsing
    - Test invalid configuration raises validation error
    - _Requirements: 7.4, 7.5_

- [x] 10. Implement logging
  - [x] 10.1 Create `research_agent/logger.py` with logging setup
    - Configure Python logging with configurable levels (DEBUG, INFO, WARNING, ERROR)
    - Implement structured logging with JSON output option
    - Define log format with timestamp, level, component, operation fields
    - Add helper functions for logging API requests with quota cost
    - Add helper functions for logging errors with stack traces
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

- [x] 11. Implement main Research Agent interface
  - [x] 11.1 Create `research_agent/agent.py` with `ResearchAgent` class
    - Implement `__init__` to initialize all components (API client, rate limiter, analyzer, cache, config, logger)
    - Load configuration from file or use defaults
    - Initialize YouTube API client with API key from environment
    - _Requirements: 1.1, 7.4, 7.5_
  
  - [x] 11.2 Implement `get_trending_topics` method
    - Accept parameters: keywords (optional), days_back (default 7), min_views (default 1000)
    - Generate cache key from query parameters
    - Check cache for fresh data (< 6 hours)
    - If cache hit, return cached results without API calls
    - If cache miss, execute search query with date range
    - Fetch video details for all results
    - Analyze trends and calculate scores
    - Filter by minimum view count and minimum trend score
    - Store results in cache with timestamp
    - Return structured output with topics and metadata
    - _Requirements: 2.1, 2.3, 5.2, 5.3, 7.1, 7.2, 7.3, 9.1_
  
  - [x] 11.3 Implement output validation and formatting
    - Validate output schema before returning results
    - Format timestamps in ISO 8601 format
    - Include up to 5 top videos per topic
    - Include metadata: query_date, total_videos_analyzed, average_trend_score
    - Raise `SchemaValidationError` if validation fails
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_
  
  - [x] 11.4 Implement error handling and resilience
    - Wrap API calls in try-except blocks
    - Log all exceptions with full stack trace and context
    - Continue processing remaining topics when single topic fails
    - Include error count in metadata
    - Return partial results with error summary
    - _Requirements: 8.3, 8.4, 8.5_
  
  - [x] 11.5 Write property test for fresh cache prevents API calls
    - **Property 15: Fresh cache prevents API calls**
    - **Validates: Requirements 5.2**
  
  - [x] 11.6 Write property test for stale cache triggers refresh
    - **Property 16: Stale cache triggers API refresh**
    - **Validates: Requirements 5.3**
  
  - [x] 11.7 Write integration tests for end-to-end flow
    - Test complete flow: query → API → analysis → cache → output
    - Test partial failure resilience (one topic fails, others succeed)
    - Test schema validation with complete output
    - _Requirements: 8.5, 9.1, 9.5_

- [x] 12. Checkpoint - Ensure core functionality works end-to-end
  - Ensure all tests pass, ask the user if questions arise.

- [x] 13. Implement additional property tests for comprehensive coverage
  - [x] 13.1 Write property test for date filtering
    - **Property 3: Date filtering respects query parameters**
    - **Validates: Requirements 2.1, 7.2**
  
  - [x] 13.2 Write property test for technical topic filtering
    - **Property 4: Technical topic filtering**
    - **Validates: Requirements 2.2**
  
  - [x] 13.3 Write property test for minimum video count
    - **Property 5: Minimum video count per query**
    - **Validates: Requirements 2.3**
  
  - [x] 13.4 Write property test for trend score metrics
    - **Property 8: Trend score incorporates all required metrics**
    - **Validates: Requirements 3.1**
  
  - [x] 13.5 Write property test for minimum score filtering
    - **Property 11: Minimum trend score filtering**
    - **Validates: Requirements 3.5, 7.3**
  
  - [x] 13.6 Write property test for pre-flight quota calculation
    - **Property 13: Pre-flight quota cost calculation**
    - **Validates: Requirements 4.4**
  
  - [x] 13.7 Write property test for valid category classification
    - **Property 17: Valid category classification**
    - **Validates: Requirements 6.1**
  
  - [x] 13.8 Write property test for classification confidence bounds
    - **Property 18: Classification confidence bounds**
    - **Validates: Requirements 6.3**
  
  - [x] 13.9 Write property test for ISO 8601 timestamp formatting
    - **Property 29: ISO 8601 timestamp formatting**
    - **Validates: Requirements 9.2**
  
  - [x] 13.10 Write property test for top videos structure
    - **Property 30: Top videos structure and limit**
    - **Validates: Requirements 9.3**

- [x] 14. Create package initialization and exports
  - [x] 14.1 Update `research_agent/__init__.py` with public API
    - Export `ResearchAgent` class
    - Export all custom exceptions
    - Export data models (`TrendingTopic`, `VideoMetadata`)
    - Set package version
    - _Requirements: 9.1_

- [x] 15. Create example usage and documentation
  - [x] 15.1 Create `examples/basic_usage.py` with example code
    - Show how to initialize `ResearchAgent`
    - Show how to call `get_trending_topics()`
    - Show how to handle exceptions
    - Show how to access results
    - _Requirements: 1.1, 7.1, 7.5_
  
  - [x] 15.2 Create `README.md` with setup instructions
    - Document how to obtain YouTube API key
    - Document how to set up `.env` file
    - Document how to install dependencies
    - Document basic usage examples
    - Document configuration options
    - _Requirements: 1.1, 7.4_

- [x] 16. Final checkpoint - Ensure all tests pass and documentation is complete
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at key milestones
- Property tests validate universal correctness properties across all inputs
- Unit tests validate specific examples, edge cases, and error conditions
- The implementation prioritizes API client (Requirement 1) and rate limiting (Requirement 4) as foundational components
- All code follows product.md standards: data-driven, real-time API data, no generic AI content


## Macro Mode Enhancement Tasks

- [x] 17. Implement Cross-Reference Engine
  - [x] 17.1 Create `research_agent/cross_reference.py` with `CrossReferenceEngine` class
    - Implement `__init__` with API client reference
    - Define `AUTHORITY_CHANNELS` dictionary with channel IDs
    - _Requirements: 3.7_
  
  - [x] 17.2 Implement authority channel fetching
    - Implement `fetch_authority_content(max_videos_per_channel)` method
    - Fetch latest videos from each authority channel using channel ID search
    - Pre-flight quota check (cost: ~50 units for 7 channels × 5 videos)
    - Parse and return video metadata list
    - _Requirements: 3.6, 3.7_
  
  - [x] 17.3 Implement topic matching logic
    - Implement `match_topics(technical_topics, authority_videos, similarity_threshold)` method
    - Implement `calculate_similarity(topic, video)` method using keyword overlap
    - Use title, description, and tags for similarity calculation
    - Return dictionary mapping topic names to match status (True/False)
    - _Requirements: 3.8_
  
  - [x] 17.4 Implement stock ticker extraction
    - Implement `extract_stock_tickers(text)` method
    - Use regex pattern to find $SYMBOL format (e.g., $NVDA, $AMZN)
    - Validate ticker format: 1-5 uppercase letters after $
    - Return list of unique ticker symbols
    - _Requirements: 3.10_
  
  - [x] 17.5 Implement company name extraction
    - Implement `extract_companies(text)` method
    - Use pattern matching for common company names (NVIDIA, Amazon, Microsoft, etc.)
    - Return list of unique company names
    - _Requirements: 3.10_
  
  - [x] 17.6 Implement finance context builder
    - Implement `build_finance_context(topic, authority_match, authority_videos)` method
    - Extract stock tickers from topic metadata
    - Extract company names from topic metadata
    - Calculate macro_relevance_score based on authority match and similarity
    - Return FinanceContext dictionary
    - _Requirements: 3.11, 9.6_
  
  - [x] 17.7 Implement macro bonus application
    - Implement `apply_macro_bonus(topics, match_status)` method
    - Apply 2x multiplier to trend_score for matched topics
    - Cap final score at 100
    - Log bonus applications
    - _Requirements: 3.9_
  
  - [x] 17.8 Write property test for macro bonus
    - **Property 38: Cross-reference bonus application**
    - **Validates: Requirements 3.9**
  
  - [x] 17.9 Write property test for stock ticker format
    - **Property 39: Stock ticker extraction format**
    - **Validates: Requirements 3.10**
  
  - [x] 17.10 Write unit tests for cross-reference engine
    - Test authority channel fetching
    - Test topic matching with various similarity scores
    - Test stock ticker extraction with valid and invalid formats
    - Test company name extraction
    - Test finance context building
    - Test macro bonus application
    - _Requirements: 3.6, 3.7, 3.8, 3.9, 3.10, 3.11_

- [x] 18. Update data models for macro mode
  - [x] 18.1 Update `research_agent/models.py` with FinanceContext dataclass
    - Implement `FinanceContext` dataclass with fields: stock_tickers, mentioned_companies, macro_relevance_score, authority_channel_match
    - Implement `to_dict()` method for JSON serialization
    - _Requirements: 3.11, 9.6_
  
  - [x] 18.2 Update TrendingTopic dataclass
    - Add `finance_context: Dict[str, Any]` field to TrendingTopic
    - Update `to_dict()` method to include finance_context
    - _Requirements: 9.1, 9.6_
  
  - [x] 18.3 Update ResearchAgentConfig dataclass
    - Add macro mode configuration fields: macro_mode_enabled, authority_channels, max_videos_per_authority_channel, topic_similarity_threshold, macro_bonus_multiplier
    - Set default values for new fields
    - _Requirements: 3.7, 3.12_
  
  - [x] 18.4 Write property test for finance context completeness
    - **Property 40: Finance context structure completeness**
    - **Validates: Requirements 3.11, 9.6**
  
  - [x] 18.5 Write property test for macro relevance score bounds
    - **Property 42: Macro relevance score bounds**
    - **Validates: Requirements 3.11**

- [x] 19. Integrate macro mode into Research Agent
  - [x] 19.1 Update `research_agent/agent.py` to support macro_mode parameter
    - Add `macro_mode: bool = False` parameter to `get_trending_topics()` method
    - Initialize CrossReferenceEngine when macro_mode enabled
    - Update method signature and docstring
    - _Requirements: 3.6, 3.12_
  
  - [x] 19.2 Implement macro mode data flow
    - When macro_mode=True, fetch authority channel content
    - Pass authority videos to cross-reference engine
    - Match topics and apply macro bonus
    - Build finance_context for each topic
    - Update metadata to include macro_mode_enabled and authority_channels_checked
    - _Requirements: 3.6, 3.8, 3.9, 3.11_
  
  - [x] 19.3 Implement standard mode finance context
    - When macro_mode=False, create empty finance_context for each topic
    - Set stock_tickers and mentioned_companies to empty lists
    - Set macro_relevance_score to 0.0
    - Set authority_channel_match to False
    - _Requirements: 3.12, 9.7_
  
  - [x] 19.4 Update output validation
    - Validate finance_context structure in output schema
    - Ensure all required fields present
    - Validate macro_relevance_score is between 0 and 1
    - _Requirements: 9.4, 9.5, 9.6_
  
  - [x] 19.5 Write property test for authority channel fetching
    - **Property 37: Macro mode authority channel fetching**
    - **Validates: Requirements 3.6, 3.7**
  
  - [x] 19.6 Write property test for empty finance context in standard mode
    - **Property 41: Empty finance context in standard mode**
    - **Validates: Requirements 3.12, 9.7**
  
  - [x] 19.7 Write property test for authority match consistency
    - **Property 43: Authority channel match consistency**
    - **Validates: Requirements 3.9, 3.11**
  
  - [x] 19.8 Write integration tests for macro mode
    - Test end-to-end flow with macro_mode=True
    - Test end-to-end flow with macro_mode=False
    - Test quota consumption in macro mode
    - Test cache behavior with macro mode data
    - _Requirements: 3.6, 3.8, 3.9, 3.11, 3.12_

- [x] 20. Update configuration and documentation
  - [x] 20.1 Update `.env.example` with macro mode settings
    - Add example configuration for macro_mode_enabled
    - Add comments explaining authority channels
    - _Requirements: 3.7_
  
  - [x] 20.2 Update `examples/basic_usage.py` with macro mode example
    - Add example showing macro_mode=True usage
    - Show how to access finance_context in results
    - Demonstrate stock ticker and company extraction
    - _Requirements: 3.6, 3.11_
  
  - [x] 20.3 Update `README.md` with macro mode documentation
    - Document macro_mode parameter
    - Explain authority channels and cross-referencing
    - Document finance_context structure
    - Provide usage examples
    - _Requirements: 3.6, 3.7, 3.11_
  
  - [x] 20.4 Update `generate_trending_topics.py` to support macro mode
    - Add `--macro-mode` command-line flag
    - Display finance_context in output
    - Show stock tickers and companies in summary
    - _Requirements: 3.6, 3.11_

- [x] 21. Final checkpoint - Ensure macro mode works end-to-end
  - Ensure all macro mode tests pass
  - Verify quota consumption is reasonable
  - Test with real YouTube API in macro mode
  - Validate finance_context accuracy
  - Ask the user if questions arise

## Notes

- Macro mode adds ~50-100 API quota units per query (7 channels × 5 videos + details)
- Cross-referencing uses keyword matching and semantic similarity (threshold: 0.3)
- Stock ticker extraction uses regex pattern: `\$[A-Z]{1,5}`
- Macro bonus is multiplicative (2x) and applied before normalization to 100
- Authority channels can be customized via configuration
- Finance context is always present in output (empty in standard mode)


## Multi-Source Expansion Tasks (R11-R17)

- [x] 22. Update dependencies and environment configuration
  - [x] 22.1 Add new dependencies to `requirements.txt`
    - Add `pytrends>=4.9.0` for Google Trends integration
    - Add `yfinance>=0.2.0` for Yahoo Finance integration
    - Add `beautifulsoup4>=4.12.0` for Wikipedia HTML parsing
    - Add `openai>=1.0.0` for GPT-4o-mini pitch generation
    - _Requirements: 11.1, 12.1, 13.1, 14.1, 16.8_
  
  - [x] 22.2 Update `.env.example` with `OPENAI_API_KEY`
    - Add `OPENAI_API_KEY=your_openai_api_key_here` with comment
    - _Requirements: 16.8_
  
  - [x] 22.3 Update `research_agent/exceptions.py` with new exception types
    - Add `SourceUnavailableError(ResearchAgentError)` with `source_name` attribute
    - Add `PitchGenerationError(ResearchAgentError)` for GPT-4o-mini failures
    - _Requirements: 11.5, 12.5, 13.5, 14.4, 16.9_

- [x] 23. Implement Google Trends Client
  - [x] 23.1 Create `research_agent/google_trends_client.py` with `GoogleTrendsClient` class
    - Implement `__init__` with `geo` (default: empty/global) and `hl` (default: "en-US") parameters
    - Implement `fetch_trends(geo, hours)` using `pytrends.trending_searches()` and `pytrends.realtime_trending_searches()`
    - Implement `_normalize_topic_name(name)` to lowercase topic names for dedup
    - Return list of dicts with keys: `topic_name`, `approximate_search_volume`, `related_queries`, `source_url`
    - Log warning and return empty list if Google Trends is unreachable (catch exceptions, don't crash)
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6_
  
  - [ ]* 23.2 Write unit tests for Google Trends Client
    - Test successful trend fetch returns correct structure
    - Test geographic filtering passes country code to pytrends
    - Test topic names are normalized to lowercase
    - Test unreachable service returns empty list with warning logged
    - Mock pytrends library responses
    - _Requirements: 11.1, 11.2, 11.4, 11.5, 11.6_

- [x] 24. Implement Reddit Client
  - [x] 24.1 Create `research_agent/reddit_client.py` with `RedditClient` class
    - Implement `__init__` with `user_agent` (default: "FacelessMediaEngine/1.0 (research-agent)")
    - Define `DEFAULT_SUBREDDITS` list: worldnews, economics, technology, science, futurology, geopolitics, finance, dataisbeautiful, explainlikeimfive
    - Implement `fetch_hot_posts(subreddits, limit)` fetching from `https://www.reddit.com/r/{sub}/hot.json`
    - Implement `_fetch_subreddit(subreddit, limit)` for single subreddit fetch
    - Enforce 2-second minimum interval between HTTP requests
    - Set descriptive User-Agent header on all requests
    - Skip private/unavailable subreddits with warning, continue with remaining
    - Return list of dicts with keys: `title`, `score`, `comment_count`, `subreddit`, `permalink`, `created_utc`
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7_
  
  - [ ]* 24.2 Write unit tests for Reddit Client
    - Test successful fetch returns correct structure for each post
    - Test private subreddit is skipped with warning logged
    - Test rate limiting enforces 2-second interval between requests
    - Test descriptive User-Agent header is set
    - Test default subreddits list matches requirement
    - Mock Reddit JSON API responses
    - _Requirements: 12.1, 12.4, 12.5, 12.6, 12.7_

- [x] 25. Implement Yahoo Finance Client
  - [x] 25.1 Create `research_agent/yahoo_finance_client.py` with `YahooFinanceClient` class
    - Implement `__init__` with `MAJOR_INDICES` and `SECTORS` constants
    - Implement `fetch_market_movers()` returning dict with keys: `gainers`, `losers`, `most_active`, `story_triggers`
    - Flag stocks with `abs(change_percent) > 5.0` as story triggers
    - Implement `fetch_sector_performance()` returning sector ETF data
    - Implement `enrich_finance_context(tickers)` to fetch real-time price data for detected tickers
    - Each stock dict has keys: `symbol`, `name`, `price`, `change_percent`, `volume`, `sector`
    - Log warning and return empty dict if Yahoo Finance is unreachable
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6_
  
  - [ ]* 25.2 Write unit tests for Yahoo Finance Client
    - Test market movers returns correct structure
    - Test stock with >5% change appears in story_triggers
    - Test stock with <=5% change does NOT appear in story_triggers
    - Test sector performance returns correct structure
    - Test ticker enrichment returns price data for valid tickers
    - Test unreachable service returns empty dict with warning logged
    - Mock yfinance library responses
    - _Requirements: 13.1, 13.3, 13.4, 13.5, 13.6_

- [x] 26. Implement Wikipedia Events Client
  - [x] 26.1 Create `research_agent/wikipedia_events_client.py` with `WikipediaEventsClient` class
    - Implement `__init__` with `BASE_URL` and `EVENT_CATEGORIES` constants
    - Implement `fetch_current_events(date)` using `requests` + `BeautifulSoup` to parse Current Events portal
    - Implement `_parse_events_page(html)` to extract structured event records
    - Implement `_classify_event(text)` to classify into one of 7 EVENT_CATEGORIES
    - Implement `_extract_named_entities(text)` to extract people, places, organizations
    - Fall back to previous day's events if current day's page is unavailable (404)
    - Return list of dicts with keys: `headline`, `category`, `date`, `related_links`, `summary`, `named_entities`
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5_
  
  - [ ]* 26.2 Write unit tests for Wikipedia Events Client
    - Test successful parse returns correct structure
    - Test event classification into valid categories
    - Test named entity extraction returns list of strings
    - Test fallback to previous day when current day returns 404
    - Test unreachable Wikipedia returns empty list with warning
    - Mock Wikipedia HTML responses with sample Current Events portal HTML
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5_

- [x] 27. Checkpoint - Ensure all data source clients work independently
  - Ensure all tests pass, ask the user if questions arise.

- [x] 28. Update data models for multi-source support
  - [x] 28.1 Add `SourceTrend`, `StoryPitch`, and `StoryPitchBoard` dataclasses to `research_agent/models.py`
    - Implement `SourceTrend` with fields: `source_name`, `source_url`, `fetched_at`, `raw_data` and `to_dict()` method
    - Implement `StoryPitch` with fields: `title`, `hook`, `source_trends`, `context_type`, `category`, `data_note`, `estimated_interest` and `to_dict()` method
    - Implement `StoryPitchBoard` with fields: `pitches`, `generated_at`, `source_topic_count` and `to_dict()` method
    - _Requirements: 15.6, 16.3_
  
  - [x] 28.2 Extend `TrendingTopic` dataclass in `research_agent/models.py`
    - Add `source_count: int = 1` field
    - Add `sources: List[Dict[str, Any]]` field (default empty list)
    - Add `high_confidence: bool = False` field
    - Update `to_dict()` to include new fields
    - _Requirements: 9.1, 9.8, 15.3, 15.5_
  
  - [x] 28.3 Extend `ResearchAgentConfig` dataclass in `research_agent/models.py`
    - Add `google_trends_geo: str = ""` field
    - Add `reddit_subreddits` list field with 9 default subreddits
    - Add `reddit_posts_per_sub: int = 25` field
    - Add `reddit_rate_limit_seconds: float = 2.0` field
    - Add `yahoo_finance_story_trigger_pct: float = 5.0` field
    - Add `dedup_similarity_threshold: float = 0.75` field
    - Add `high_confidence_min_sources: int = 3` field
    - Add `openai_api_key: str = ""` field
    - Add `pitch_count: int = 12` field
    - _Requirements: 11.2, 12.2, 12.6, 13.4, 15.2, 15.5, 16.2_

- [x] 29. Extend Cross-Reference Engine for multi-source merging
  - [x] 29.1 Add `merge_all_sources()` method to `research_agent/cross_reference.py`
    - Accept 5 source lists: google_trends, reddit_posts, yahoo_finance, wikipedia_events, youtube_topics
    - Normalize all source data into a common topic format with `source_name` and `source_url`
    - Return unified list of topic dicts
    - _Requirements: 15.1_
  
  - [x] 29.2 Add `deduplicate_topics()` method to `research_agent/cross_reference.py`
    - Implement keyword matching and semantic similarity comparison
    - Use 0.75 similarity threshold for merging
    - When topics match, merge into single entry with combined `sources` list
    - Preserve original source metadata (`source_name`, `source_url`, `fetched_at`) for each merged entry
    - _Requirements: 15.2, 15.3, 15.6_
  
  - [x] 29.3 Add `calculate_cross_source_score()` method to `research_agent/cross_reference.py`
    - Weight topics appearing in more sources higher
    - Topics in 3+ sources get `high_confidence = True`
    - Normalize score to 0-100 range
    - _Requirements: 15.4, 15.5_
  
  - [x] 29.4 Add `mark_high_confidence()` method to `research_agent/cross_reference.py`
    - Set `high_confidence = True` for topics with `source_count >= 3`
    - Set `high_confidence = False` for topics with `source_count < 3`
    - _Requirements: 15.5_
  
  - [ ]* 29.5 Write unit tests for extended Cross-Reference Engine
    - Test merge_all_sources includes topics from all 5 sources
    - Test dedup merges two topics with similarity >= 0.75
    - Test dedup keeps separate topics with similarity < 0.75
    - Test merged topic has combined sources list with correct count
    - Test cross-source score is higher for multi-source topics
    - Test high_confidence flag set correctly at 3+ sources
    - Test unified list sorted by Trend_Score descending
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 15.7_

- [x] 30. Implement Pitch Generator
  - [x] 30.1 Create `research_agent/pitch_generator.py` with `PitchGenerator` class
    - Implement `__init__` loading `OPENAI_API_KEY` from environment, raise `AuthenticationError` if missing/empty
    - Set `MODEL = "gpt-4o-mini"`
    - Implement `generate_pitches(unified_topics, count)` calling OpenAI API
    - Implement `_build_prompt(topics, count)` instructing GPT-4o-mini to generate curiosity-driven questions, avoid clickbait/hyperbole/generic phrasing, classify as recent_event or historic_topic, include source trend references
    - Implement `_parse_response(response_text, topics)` to parse GPT response into `StoryPitch` objects
    - Implement `_rank_pitches(pitches)` sorting by `estimated_interest` (trend_score × source_count) descending
    - Return `StoryPitchBoard` with 10-15 pitches
    - Add `data_note` based on `context_type`: real-time data note for recent_event, historical context note for historic_topic
    - _Requirements: 16.1, 16.2, 16.3, 16.4, 16.5, 16.6, 16.7, 16.8, 16.9, 16.10_
  
  - [ ]* 30.2 Write unit tests for Pitch Generator
    - Test missing OPENAI_API_KEY raises AuthenticationError
    - Test empty OPENAI_API_KEY raises AuthenticationError
    - Test generate_pitches returns StoryPitchBoard with 10-15 pitches
    - Test each StoryPitch has all required fields populated
    - Test pitches ranked by estimated_interest descending
    - Test context_type is either "recent_event" or "historic_topic"
    - Test data_note matches context_type
    - Test prompt instructs against clickbait and generic phrasing
    - Mock OpenAI API responses
    - _Requirements: 16.2, 16.3, 16.4, 16.5, 16.6, 16.7, 16.9, 16.10_

- [x] 31. Implement Topic Selector (Human-in-the-Loop)
  - [x] 31.1 Create `research_agent/topic_selector.py` with `TopicSelector` class
    - Implement `__init__` with `PitchGenerator` reference for regeneration support
    - Implement `present_and_select(board, unified_topics)` handling user selection loop
    - Implement `_render_board(board)` rendering numbered list with title, hook, context_type, category
    - Implement `_show_details(pitch)` rendering full source trend data for a pitch
    - Support integer index selection (1-N) returning the selected `StoryPitch`
    - Support "regenerate" command triggering new pitch generation from same trends
    - Support "details N" command showing full source data for pitch N
    - Display error message and re-prompt on invalid index
    - _Requirements: 17.1, 17.2, 17.3, 17.4, 17.5, 17.6, 17.7_
  
  - [ ]* 31.2 Write unit tests for Topic Selector
    - Test board rendering contains numbered entries with title, hook, context_type, category
    - Test valid index selection returns correct StoryPitch
    - Test invalid index (0, N+1) displays error and re-prompts
    - Test "regenerate" command triggers new pitch generation
    - Test "details N" command shows source trend data
    - Test selected StoryPitch has all fields populated
    - Mock user input for selection loop
    - _Requirements: 17.1, 17.2, 17.3, 17.4, 17.5, 17.6_

- [x] 32. Checkpoint - Ensure pitch generation and selection work correctly
  - Ensure all tests pass, ask the user if questions arise.

- [x] 33. Update ResearchAgent to orchestrate multi-source pipeline
  - [x] 33.1 Update `research_agent/agent.py` to import and initialize new clients
    - Import `GoogleTrendsClient`, `RedditClient`, `YahooFinanceClient`, `WikipediaEventsClient`, `PitchGenerator`, `TopicSelector`
    - Initialize all clients in `__init__` (data source clients are keyless, PitchGenerator needs OPENAI_API_KEY)
    - Handle `SourceUnavailableError` gracefully during initialization
    - _Requirements: 11.1, 12.1, 13.1, 14.1, 16.8_
  
  - [x] 33.2 Add `get_trending_topics_multi_source()` method to `research_agent/agent.py`
    - Fetch from all 5 sources in sequence (Google Trends, Reddit, Yahoo Finance, Wikipedia, YouTube)
    - Wrap each source fetch in try/except, log warning on `SourceUnavailableError`, continue with remaining sources
    - Pass all source results to `CrossReferenceEngine.merge_all_sources()`
    - Deduplicate with 0.75 similarity threshold
    - Calculate cross-source scores and mark high-confidence topics
    - Sort unified list by Trend_Score descending
    - Enrich finance_context with Yahoo Finance real-time data for detected tickers
    - Return unified `TrendingTopic` list with source attribution
    - _Requirements: 11.5, 12.5, 13.5, 14.4, 15.1, 15.2, 15.4, 15.5, 15.7_
  
  - [x] 33.3 Add `generate_and_select_pitch()` method to `research_agent/agent.py`
    - Accept unified topic list from `get_trending_topics_multi_source()`
    - Pass topics to `PitchGenerator.generate_pitches()`
    - Pass `StoryPitchBoard` to `TopicSelector.present_and_select()`
    - Return selected `StoryPitch` as structured dataclass
    - _Requirements: 16.1, 16.2, 17.1, 17.2, 17.3, 17.7_
  
  - [ ]* 33.4 Write integration tests for multi-source pipeline
    - Test end-to-end: fetch all sources → merge → dedup → score → pitch → select
    - Test graceful degradation when 1-2 sources are unavailable
    - Test all 5 sources return empty results (pipeline still works, returns empty pitch board)
    - Test finance_context enriched with Yahoo Finance data
    - Test selected StoryPitch has correct structure for Script Generator input
    - Mock all external APIs
    - _Requirements: 11.5, 12.5, 13.5, 14.4, 15.1, 16.1, 17.7_

- [x] 34. Update configuration and exports
  - [x] 34.1 Update `research_agent/config.py` with multi-source settings
    - Load `OPENAI_API_KEY` from environment variables
    - Add multi-source config fields to config loading logic
    - Validate new configuration fields
    - _Requirements: 16.8_
  
  - [x] 34.2 Update `research_agent/__init__.py` with new exports
    - Export `GoogleTrendsClient`, `RedditClient`, `YahooFinanceClient`, `WikipediaEventsClient`
    - Export `PitchGenerator`, `TopicSelector`
    - Export `SourceTrend`, `StoryPitch`, `StoryPitchBoard`
    - Export `SourceUnavailableError`, `PitchGenerationError`
    - _Requirements: 9.1_
  
  - [x] 34.3 Update `examples/basic_usage.py` with multi-source example
    - Show how to call `get_trending_topics_multi_source()`
    - Show how to call `generate_and_select_pitch()`
    - Show how to access source attribution and finance_context
    - _Requirements: 11.1, 16.1, 17.1_

- [x] 35. Checkpoint - Ensure multi-source pipeline works end-to-end
  - Ensure all tests pass
  - Verify graceful degradation when individual sources are unavailable
  - Verify pitch generation and selection flow
  - Ask the user if questions arise

- [x] 36. Final checkpoint - Ensure all R11-R17 tasks complete
  - Ensure all new unit tests pass
  - Verify all 5 data source clients work independently
  - Verify cross-source merging and deduplication
  - Verify pitch generation with GPT-4o-mini
  - Verify human-in-the-loop selection flow
  - Verify updated exports and configuration
  - Ask the user if questions arise

## Notes (R11-R17)

- All data source clients (Google Trends, Reddit, Yahoo Finance, Wikipedia) are free and require no API keys
- Only the Pitch Generator requires an API key (OPENAI_API_KEY for GPT-4o-mini)
- Each source client follows graceful degradation: log warning and continue if unreachable
- Reddit enforces 2-second rate limit between requests per Reddit API guidelines
- Wikipedia falls back to previous day's events if today's page is unavailable
- Cross-source deduplication uses 0.75 similarity threshold
- Topics appearing in 3+ sources are marked as high_confidence
- Story Pitch Board targets 10-15 pitches ranked by estimated audience interest
- The selected StoryPitch serves as input to the Script Generator module
- Tasks marked with `*` are optional and can be skipped for faster MVP
