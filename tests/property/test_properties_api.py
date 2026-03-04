"""
Property-based tests for API-related correctness properties.

This module tests properties related to YouTube API client, rate limiting,
and quota management using Hypothesis for property-based testing.
"""

import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime, timezone, timedelta
from pathlib import Path
import tempfile
import shutil

from research_agent.rate_limiter import APIRateLimiter
from research_agent.exceptions import QuotaExceededError


# Feature: research-agent, Property 12: Quota consumption tracking accuracy
@given(
    operations=st.lists(
        st.one_of(
            st.just(('search', 100)),  # search operation costs 100 units
            st.integers(min_value=1, max_value=50).map(lambda n: ('video_details', n))  # video details: 1 unit per video
        ),
        min_size=1,
        max_size=20
    )
)
@settings(max_examples=100)
def test_quota_consumption_tracking_accuracy(operations):
    """
    Property 12: Quota consumption tracking accuracy
    
    **Validates: Requirements 4.1**
    
    For any sequence of API operations, the total quota consumed (as tracked by
    the rate limiter) should equal the sum of individual operation costs
    (search: 100 units, video details: 1 unit per video).
    """
    # Create a temporary directory for quota state
    temp_dir = tempfile.mkdtemp()
    try:
        state_file = Path(temp_dir) / "quota_state.json"
        
        # Initialize rate limiter with high quota to avoid circuit breaker
        rate_limiter = APIRateLimiter(daily_quota=100000, state_file=str(state_file))
        
        # Track expected total cost
        expected_total_cost = 0
        
        # Execute each operation and consume quota
        for operation_type, cost in operations:
            # Check quota is available
            assert rate_limiter.check_quota(cost), \
                f"Quota check failed for {operation_type} with cost {cost}"
            
            # Consume the quota
            rate_limiter.consume_quota(cost)
            
            # Update expected total
            expected_total_cost += cost
        
        # Verify total consumed matches expected
        actual_consumed = rate_limiter.consumed
        
        assert actual_consumed == expected_total_cost, \
            f"Quota tracking mismatch: expected {expected_total_cost}, got {actual_consumed}. " \
            f"Operations: {operations}"
        
        # Also verify remaining quota is correct
        expected_remaining = rate_limiter.daily_quota - expected_total_cost
        actual_remaining = rate_limiter.get_remaining_quota()
        
        assert actual_remaining == expected_remaining, \
            f"Remaining quota mismatch: expected {expected_remaining}, got {actual_remaining}"
    
    finally:
        # Cleanup temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)


# Additional test: Verify quota tracking persists across rate limiter instances
@given(
    first_batch=st.lists(
        st.integers(min_value=1, max_value=100),
        min_size=1,
        max_size=10
    ),
    second_batch=st.lists(
        st.integers(min_value=1, max_value=100),
        min_size=1,
        max_size=10
    )
)
@settings(max_examples=100)
def test_quota_tracking_persists_across_instances(first_batch, second_batch):
    """
    Property 12 (extended): Quota tracking should persist across rate limiter instances.
    
    This verifies that quota state is correctly saved to disk and loaded,
    ensuring accurate tracking even if the application restarts.
    """
    # Create a temporary directory for quota state
    temp_dir = tempfile.mkdtemp()
    try:
        state_file = Path(temp_dir) / "quota_state.json"
        
        # First instance: consume first batch
        rate_limiter1 = APIRateLimiter(daily_quota=100000, state_file=str(state_file))
        first_total = sum(first_batch)
        
        for cost in first_batch:
            rate_limiter1.consume_quota(cost)
        
        assert rate_limiter1.consumed == first_total
        
        # Second instance: should load previous state and continue tracking
        rate_limiter2 = APIRateLimiter(daily_quota=100000, state_file=str(state_file))
        
        # Verify it loaded the previous consumption
        assert rate_limiter2.consumed == first_total, \
            f"Failed to load previous quota state: expected {first_total}, got {rate_limiter2.consumed}"
        
        # Consume second batch
        second_total = sum(second_batch)
        for cost in second_batch:
            rate_limiter2.consume_quota(cost)
        
        # Verify total is cumulative
        expected_total = first_total + second_total
        assert rate_limiter2.consumed == expected_total, \
            f"Cumulative quota tracking failed: expected {expected_total}, got {rate_limiter2.consumed}"
    
    finally:
        # Cleanup temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)


# Test: Verify quota tracking with mixed operation types
@given(
    num_searches=st.integers(min_value=0, max_value=10),
    num_video_batches=st.lists(
        st.integers(min_value=1, max_value=50),
        min_size=0,
        max_size=10
    )
)
@settings(max_examples=100)
def test_quota_tracking_mixed_operations(num_searches, num_video_batches):
    """
    Property 12 (extended): Quota tracking for realistic mixed operation sequences.
    
    Tests quota tracking with a realistic mix of search operations (100 units each)
    and video detail fetches (1 unit per video).
    """
    # Create a temporary directory for quota state
    temp_dir = tempfile.mkdtemp()
    try:
        state_file = Path(temp_dir) / "quota_state.json"
        
        # Initialize rate limiter
        rate_limiter = APIRateLimiter(daily_quota=100000, state_file=str(state_file))
        
        # Calculate expected cost
        search_cost = num_searches * 100
        video_cost = sum(num_video_batches)  # 1 unit per video
        expected_total = search_cost + video_cost
        
        # Execute searches
        for _ in range(num_searches):
            rate_limiter.consume_quota(100)
        
        # Execute video detail fetches
        for batch_size in num_video_batches:
            rate_limiter.consume_quota(batch_size)
        
        # Verify total
        assert rate_limiter.consumed == expected_total, \
            f"Mixed operation tracking failed: expected {expected_total}, got {rate_limiter.consumed}. " \
            f"Searches: {num_searches}, Video batches: {num_video_batches}"
    
    finally:
        # Cleanup temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)


from research_agent.cross_reference import CrossReferenceEngine


# Feature: research-agent, Property 38: Cross-reference bonus application
@given(
    base_scores=st.lists(
        st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        min_size=1,
        max_size=20
    ),
    match_flags=st.lists(
        st.booleans(),
        min_size=1,
        max_size=20
    )
)
@settings(max_examples=100)
def test_cross_reference_bonus_application(base_scores, match_flags):
    """
    Property 38: Cross-reference bonus application

    **Validates: Requirements 3.9**

    For any topic that appears in both technical searches AND authority channel
    content, the trend_score should be exactly 2x the base score (before
    normalization to 100).
    """
    # Ensure lists are same length
    length = min(len(base_scores), len(match_flags))
    base_scores = base_scores[:length]
    match_flags = match_flags[:length]

    # Build topics and match_status
    topics = []
    match_status = {}
    for i, (score, matched) in enumerate(zip(base_scores, match_flags)):
        name = f"topic_{i}"
        topics.append({"topic_name": name, "trend_score": score})
        match_status[name] = matched

    # Create engine with a mock api_client (not used by apply_macro_bonus)
    engine = CrossReferenceEngine.__new__(CrossReferenceEngine)

    # Apply macro bonus
    result = engine.apply_macro_bonus(topics, match_status)

    # Verify properties
    for i, (score, matched) in enumerate(zip(base_scores, match_flags)):
        name = f"topic_{i}"
        result_score = result[i]["trend_score"]

        if matched:
            expected = min(score * 2.0, 100.0)
            assert abs(result_score - expected) < 1e-9, (
                f"Matched topic '{name}' with base score {score}: "
                f"expected {expected}, got {result_score}"
            )
            # Score must never exceed 100
            assert result_score <= 100.0, (
                f"Score exceeded 100 for topic '{name}': {result_score}"
            )
        else:
            # Unmatched topics should keep their original score
            assert abs(result_score - score) < 1e-9, (
                f"Unmatched topic '{name}' score changed: "
                f"expected {score}, got {result_score}"
            )


# Feature: research-agent, Property 39: Stock ticker extraction format
@given(
    tickers=st.lists(
        st.from_regex(r'[A-Z]{1,5}', fullmatch=True),
        min_size=0,
        max_size=10
    ),
    noise=st.text(
        alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'Z')),
        min_size=0,
        max_size=100
    )
)
@settings(max_examples=100)
def test_stock_ticker_extraction_format(tickers, noise):
    """
    Property 39: Stock ticker extraction format

    **Validates: Requirements 3.10**

    For any extracted stock ticker, the format should match the pattern
    $[A-Z]{1,5} (dollar sign followed by 1-5 uppercase letters).
    """
    import re

    engine = CrossReferenceEngine.__new__(CrossReferenceEngine)

    # Build text with known tickers embedded in noise
    text_parts = [noise]
    for ticker in tickers:
        text_parts.append(f"${ticker}")
    text = " ".join(text_parts)

    extracted = engine.extract_stock_tickers(text)

    # Property 1: Every extracted ticker matches the required format
    ticker_pattern = re.compile(r'^[A-Z]{1,5}$')
    for t in extracted:
        assert ticker_pattern.match(t), (
            f"Extracted ticker '{t}' does not match format [A-Z]{{1,5}}"
        )

    # Property 2: All intentionally inserted tickers should be found
    for ticker in tickers:
        if 1 <= len(ticker) <= 5 and ticker.isalpha() and ticker.isupper():
            assert ticker in extracted, (
                f"Expected ticker '{ticker}' not found in extracted: {extracted}. "
                f"Text was: {text}"
            )

    # Property 3: Extracted tickers are unique (no duplicates)
    assert len(extracted) == len(set(extracted)), (
        f"Duplicate tickers found: {extracted}"
    )


# Feature: research-agent, Property 40: Finance context structure completeness
@given(
    topic_name=st.text(min_size=1, max_size=50),
    category=st.text(min_size=0, max_size=30),
    authority_match=st.booleans(),
    num_authority_videos=st.integers(min_value=0, max_value=5),
    include_tickers=st.booleans(),
    include_companies=st.booleans(),
)
@settings(max_examples=100)
def test_finance_context_structure_completeness(
    topic_name, category, authority_match, num_authority_videos,
    include_tickers, include_companies
):
    """
    Property 40: Finance context structure completeness

    **Validates: Requirements 3.11, 9.6**

    For any topic in macro mode results, the finance_context dict produced by
    build_finance_context always contains all 4 required keys: stock_tickers,
    mentioned_companies, macro_relevance_score, and authority_channel_match.
    """
    engine = CrossReferenceEngine.__new__(CrossReferenceEngine)

    # Build a topic dict with optional ticker/company text
    text_parts = [topic_name, category]
    if include_tickers:
        text_parts.append("$NVDA $AMZN")
    if include_companies:
        text_parts.append("NVIDIA Amazon")

    topic = {
        "topic_name": " ".join(text_parts),
        "category": category,
    }

    # Build authority videos list
    authority_videos = [
        {"title": f"Authority video {i}", "description": "market analysis"}
        for i in range(num_authority_videos)
    ]

    result = engine.build_finance_context(topic, authority_match, authority_videos)

    # Property: all 4 required keys must be present
    required_keys = {"stock_tickers", "mentioned_companies", "macro_relevance_score", "authority_channel_match"}
    assert set(result.keys()) >= required_keys, (
        f"Missing keys in finance_context: {required_keys - set(result.keys())}. "
        f"Got keys: {set(result.keys())}"
    )

    # Verify value types
    assert isinstance(result["stock_tickers"], list), (
        f"stock_tickers should be a list, got {type(result['stock_tickers'])}"
    )
    assert isinstance(result["mentioned_companies"], list), (
        f"mentioned_companies should be a list, got {type(result['mentioned_companies'])}"
    )
    assert isinstance(result["macro_relevance_score"], (int, float)), (
        f"macro_relevance_score should be numeric, got {type(result['macro_relevance_score'])}"
    )
    assert isinstance(result["authority_channel_match"], bool), (
        f"authority_channel_match should be bool, got {type(result['authority_channel_match'])}"
    )


# Feature: research-agent, Property 42: Macro relevance score bounds
@given(
    authority_match=st.booleans(),
    include_tickers=st.booleans(),
    include_companies=st.booleans(),
    extra_text=st.text(min_size=0, max_size=100),
)
@settings(max_examples=100)
def test_macro_relevance_score_bounds(
    authority_match, include_tickers, include_companies, extra_text
):
    """
    Property 42: Macro relevance score bounds

    **Validates: Requirements 3.11**

    For any topic, the macro_relevance_score produced by build_finance_context
    is always between 0.0 and 1.0 (inclusive).
    """
    engine = CrossReferenceEngine.__new__(CrossReferenceEngine)

    # Build topic text with varying financial content
    text_parts = [extra_text]
    if include_tickers:
        text_parts.append("$TSLA $MSFT $GOOG")
    if include_companies:
        text_parts.append("Tesla Microsoft Google Apple")

    topic = {
        "topic_name": " ".join(text_parts),
        "category": "Finance",
    }

    authority_videos = [
        {"title": "Market update", "description": "stocks and bonds"}
    ] if authority_match else []

    result = engine.build_finance_context(topic, authority_match, authority_videos)

    score = result["macro_relevance_score"]

    assert 0.0 <= score <= 1.0, (
        f"macro_relevance_score {score} is out of bounds [0.0, 1.0]. "
        f"authority_match={authority_match}, tickers={include_tickers}, "
        f"companies={include_companies}"
    )


# Feature: research-agent, Property 37: Macro mode authority channel fetching
@given(
    max_videos_per_channel=st.integers(min_value=1, max_value=10),
    num_channels_responding=st.integers(min_value=0, max_value=7),
)
@settings(max_examples=100)
def test_macro_mode_authority_channel_fetching(
    max_videos_per_channel, num_channels_responding
):
    """
    Property 37: Macro mode authority channel fetching

    **Validates: Requirements 3.6, 3.7**

    For any request with macro_mode enabled, the Research Agent should fetch
    videos from all configured authority channels (minimum 5 videos per channel).
    The CrossReferenceEngine must attempt to fetch from every authority channel
    and the total videos returned should not exceed
    num_channels * max_videos_per_channel.
    """
    from unittest.mock import Mock, patch

    # Build a mock api_client whose search_videos returns controlled results
    mock_api = Mock()

    # Track which channel IDs were queried
    queried_channel_ids = []

    channel_list = list(CrossReferenceEngine.AUTHORITY_CHANNELS.items())

    def fake_search(query="", channel_id=None, max_results=5, order='date', **kwargs):
        queried_channel_ids.append(channel_id)
        idx = next(
            (i for i, (_, cid) in enumerate(channel_list) if cid == channel_id),
            None,
        )
        # Simulate some channels failing (returning nothing)
        if idx is not None and idx >= num_channels_responding:
            raise Exception(f"Simulated failure for channel {channel_id}")
        return [
            {
                "video_id": f"vid_{channel_id}_{j}",
                "title": f"Video {j}",
                "description": "desc",
                "channel_id": channel_id or "unknown",
                "channel_title": "Authority",
                "published_at": "2024-01-10T00:00:00Z",
            }
            for j in range(max_results)
        ]

    mock_api.search_videos = Mock(side_effect=fake_search)

    engine = CrossReferenceEngine(mock_api)
    result = engine.fetch_authority_content(max_videos_per_channel=max_videos_per_channel)

    # Property 1: Engine must attempt to fetch from ALL authority channels
    assert len(queried_channel_ids) == len(CrossReferenceEngine.AUTHORITY_CHANNELS), (
        f"Expected {len(CrossReferenceEngine.AUTHORITY_CHANNELS)} channel queries, "
        f"got {len(queried_channel_ids)}"
    )

    # Property 2: Every configured channel ID must have been queried
    configured_ids = set(CrossReferenceEngine.AUTHORITY_CHANNELS.values())
    assert set(queried_channel_ids) == configured_ids, (
        f"Not all authority channels were queried. "
        f"Missing: {configured_ids - set(queried_channel_ids)}"
    )

    # Property 3: Total videos returned <= channels_responding * max_videos_per_channel
    expected_max = num_channels_responding * max_videos_per_channel
    assert len(result) <= expected_max, (
        f"Too many videos returned: {len(result)} > {expected_max}"
    )

    # Property 4: Each returned video should have the authority_channel tag
    for video in result:
        assert "authority_channel" in video, (
            f"Video missing 'authority_channel' tag: {video}"
        )

    # Property 5: The authority channels list has at least 7 entries (per Req 3.7)
    assert len(CrossReferenceEngine.AUTHORITY_CHANNELS) >= 7, (
        f"Expected at least 7 authority channels, "
        f"got {len(CrossReferenceEngine.AUTHORITY_CHANNELS)}"
    )


# Feature: research-agent, Property 41: Empty finance context in standard mode
@given(
    num_topics=st.integers(min_value=0, max_value=10),
    topic_names=st.lists(
        st.text(
            alphabet=st.characters(whitelist_categories=('L', 'N')),
            min_size=1,
            max_size=30,
        ),
        min_size=0,
        max_size=10,
    ),
)
@settings(max_examples=100)
def test_empty_finance_context_in_standard_mode(num_topics, topic_names):
    """
    Property 41: Empty finance context in standard mode

    **Validates: Requirements 3.12, 9.7**

    For any request with macro_mode disabled, all topics should have
    finance_context with empty lists and macro_relevance_score of 0.0.
    """
    from unittest.mock import Mock, patch
    from research_agent.agent import ResearchAgent
    from research_agent.models import TrendingTopic, VideoMetadata

    # Trim topic_names to num_topics
    actual_count = min(num_topics, len(topic_names))
    names = topic_names[:actual_count]

    # Build mock trending topics
    mock_trending = []
    for name in names:
        mt = Mock(spec=TrendingTopic)
        mt.topic_name = name
        mt.to_dict.return_value = {
            "topic_name": name,
            "category": "Programming Languages",
            "trend_score": 50.0,
            "video_count": 1,
            "top_videos": [
                {
                    "video_id": "v1",
                    "title": "Test",
                    "channel": "Ch",
                    "view_count": 5000,
                    "published_at": "2024-01-10T00:00:00Z",
                }
            ],
            "fetched_at": "2024-01-15T00:00:00Z",
        }
        mock_trending.append(mt)

    config = {
        "youtube_api_key": "test_key_prop41",
        "daily_quota_limit": 100000,
    }

    with patch("research_agent.agent.load_dotenv"):
        with patch("research_agent.api_client.load_dotenv"):
            agent = ResearchAgent(config=config)

    agent.cache = Mock()
    agent.cache.get.return_value = None
    agent.api_client = Mock()
    agent.api_client.search_videos.return_value = [
        {
            "video_id": "v1",
            "title": "Test",
            "description": "desc",
            "channel_id": "ch1",
            "channel_title": "Ch",
            "published_at": "2024-01-10T00:00:00Z",
        }
    ] if names else []
    agent.api_client.get_video_details.return_value = [
        {
            "video_id": "v1",
            "title": "Test",
            "description": "desc",
            "channel_title": "Ch",
            "published_at": datetime(2024, 1, 10, tzinfo=timezone.utc),
            "view_count": 5000,
            "like_count": 100,
            "comment_count": 10,
        }
    ] if names else []
    agent.analyzer = Mock()
    agent.analyzer.analyze_trends.return_value = mock_trending

    # Call with macro_mode=False (standard mode)
    result = agent.get_trending_topics(
        keywords=["test"], days_back=7, min_views=100, macro_mode=False
    )

    # Property: every topic must have empty finance_context
    for topic in result["topics"]:
        fc = topic.get("finance_context", {})

        assert fc.get("stock_tickers") == [], (
            f"stock_tickers should be empty in standard mode, got {fc.get('stock_tickers')}"
        )
        assert fc.get("mentioned_companies") == [], (
            f"mentioned_companies should be empty in standard mode, got {fc.get('mentioned_companies')}"
        )
        assert fc.get("macro_relevance_score") == 0.0, (
            f"macro_relevance_score should be 0.0 in standard mode, got {fc.get('macro_relevance_score')}"
        )
        assert fc.get("authority_channel_match") is False, (
            f"authority_channel_match should be False in standard mode, got {fc.get('authority_channel_match')}"
        )

    # Property: metadata should indicate macro_mode is disabled
    assert result["metadata"]["macro_mode_enabled"] is False, (
        f"macro_mode_enabled should be False, got {result['metadata']['macro_mode_enabled']}"
    )
    assert result["metadata"]["authority_channels_checked"] == 0, (
        f"authority_channels_checked should be 0, got {result['metadata']['authority_channels_checked']}"
    )


# Feature: research-agent, Property 43: Authority channel match consistency
@given(
    authority_match=st.booleans(),
    has_tickers=st.booleans(),
    has_companies=st.booleans(),
)
@settings(max_examples=100)
def test_authority_channel_match_consistency(
    authority_match, has_tickers, has_companies
):
    """
    Property 43: Authority channel match consistency

    **Validates: Requirements 3.9, 3.11**

    For any topic with authority_channel_match=True, the macro_relevance_score
    should be greater than 0.
    """
    engine = CrossReferenceEngine.__new__(CrossReferenceEngine)

    # Build topic text with optional financial entities
    text_parts = ["AI chip shortage"]
    if has_tickers:
        text_parts.append("$NVDA $AMD")
    if has_companies:
        text_parts.append("NVIDIA AMD Intel")

    topic = {
        "topic_name": " ".join(text_parts),
        "category": "Technology",
    }

    authority_videos = (
        [{"title": "Tech market update", "description": "semiconductor stocks"}]
        if authority_match
        else []
    )

    result = engine.build_finance_context(topic, authority_match, authority_videos)

    # Core property: if authority_channel_match is True, score must be > 0
    if result["authority_channel_match"]:
        assert result["macro_relevance_score"] > 0.0, (
            f"authority_channel_match is True but macro_relevance_score is "
            f"{result['macro_relevance_score']}. Expected > 0. "
            f"authority_match={authority_match}, tickers={has_tickers}, "
            f"companies={has_companies}"
        )

    # Consistency: authority_channel_match should reflect the input
    assert result["authority_channel_match"] == authority_match, (
        f"authority_channel_match mismatch: expected {authority_match}, "
        f"got {result['authority_channel_match']}"
    )

    # Bound check: score always in [0, 1]
    assert 0.0 <= result["macro_relevance_score"] <= 1.0, (
        f"macro_relevance_score {result['macro_relevance_score']} out of bounds"
    )
