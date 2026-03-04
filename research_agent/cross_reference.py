"""
Cross-Reference Engine for the Research Agent.

This module cross-references technical topics with authority channel content
to identify macro trends and extract financial context.
"""

import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from research_agent.api_client import YouTubeAPIClient
from research_agent.logger import get_logger

logger = get_logger(__name__)


class CrossReferenceEngine:
    """
    Cross-references technical topics with authority channel content.
    Identifies macro trends and extracts financial context.
    """
    
    # Authority channel IDs (YouTube channel IDs)
    AUTHORITY_CHANNELS = {
        'The Economist': 'UC0p5jTq6Xx_DosDFxVXnWaQ',
        'Bloomberg Technology': 'UCrM7B7SL_g1edFOnmj-SDKg',
        'CNBC Television': 'UCvJJ_dzjViJCoLf5uKUTwoA',
        'Financial Times': 'UCRb3vTRz8RYCqGGq-Xt8Rkw',
        'Wall Street Journal': 'UCK7tptUDHh-RYDsdxO1-5QQ',
        'TechCrunch': 'UCCjyq_K1Xwfg8Lndy7lKMpA',
        'The Verge': 'UCddiUEpeqJcYeBxX1IVBKvQ'
    }
    
    # Common tech company names for extraction
    TECH_COMPANIES = [
        'NVIDIA', 'Amazon', 'Microsoft', 'Google', 'Apple', 'Meta', 'Tesla',
        'AMD', 'Intel', 'IBM', 'Oracle', 'Salesforce', 'Adobe', 'Netflix',
        'Uber', 'Airbnb', 'Spotify', 'Twitter', 'LinkedIn', 'PayPal',
        'Cisco', 'VMware', 'ServiceNow', 'Snowflake', 'Databricks'
    ]
    
    def __init__(self, api_client: YouTubeAPIClient):
        """
        Initialize cross-reference engine.
        
        Args:
            api_client: YouTube API client for fetching authority content
        """
        self.api_client = api_client
        logger.info("CrossReferenceEngine initialized with %d authority channels", 
                   len(self.AUTHORITY_CHANNELS))
    
    def fetch_authority_content(
        self,
        max_videos_per_channel: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Fetch latest videos from authority channels.
        
        Args:
            max_videos_per_channel: Number of recent videos to fetch per channel
            
        Returns:
            List of video metadata from authority channels
            
        Raises:
            QuotaExceededError: If API quota exhausted
        """
        logger.info("Fetching authority content from %d channels", 
                   len(self.AUTHORITY_CHANNELS))
        
        all_videos = []
        
        for channel_name, channel_id in self.AUTHORITY_CHANNELS.items():
            try:
                # Search for videos from this channel
                # Use channel ID in query to get channel-specific results
                videos = self.api_client.search_videos(
                    query=f"",  # Empty query to get all videos
                    channel_id=channel_id,
                    max_results=max_videos_per_channel,
                    order='date'  # Get most recent videos
                )
                
                logger.debug("Fetched %d videos from %s", len(videos), channel_name)
                
                # Tag videos with authority channel name
                for video in videos:
                    video['authority_channel'] = channel_name
                
                all_videos.extend(videos)
                
            except Exception as e:
                logger.warning("Failed to fetch from %s: %s", channel_name, str(e))
                continue
        
        logger.info("Fetched total of %d videos from authority channels", len(all_videos))
        return all_videos
    
    def match_topics(
        self,
        technical_topics: List[Dict[str, Any]],
        authority_videos: List[Dict[str, Any]],
        similarity_threshold: float = 0.3
    ) -> Dict[str, bool]:
        """
        Identify topic overlap between technical and authority content.
        
        Uses keyword matching and semantic similarity to find cross-references.
        
        Args:
            technical_topics: Topics from technical searches
            authority_videos: Videos from authority channels
            similarity_threshold: Minimum similarity score for match (0-1)
            
        Returns:
            Dictionary mapping topic names to match status (True if matched)
        """
        logger.info("Matching %d technical topics against %d authority videos",
                   len(technical_topics), len(authority_videos))
        
        match_status = {}
        
        for topic in technical_topics:
            topic_name = topic.get('topic_name', '')
            max_similarity = 0.0
            matched_video = None
            
            # Compare topic against all authority videos
            for video in authority_videos:
                similarity = self.calculate_similarity(topic, video)
                
                if similarity > max_similarity:
                    max_similarity = similarity
                    matched_video = video
            
            # Mark as matched if similarity exceeds threshold
            is_matched = max_similarity >= similarity_threshold
            match_status[topic_name] = is_matched
            
            if is_matched:
                logger.info("Topic '%s' matched with authority video (similarity: %.2f)",
                           topic_name[:50], max_similarity)
        
        matched_count = sum(1 for matched in match_status.values() if matched)
        logger.info("Matched %d/%d topics with authority content",
                   matched_count, len(technical_topics))
        
        return match_status
    
    def calculate_similarity(
        self,
        topic: Dict[str, Any],
        video: Dict[str, Any]
    ) -> float:
        """
        Calculate semantic similarity between topic and video.
        
        Uses keyword overlap, entity matching, and contextual analysis.
        
        Args:
            topic: Technical topic with metadata
            video: Authority channel video with metadata
            
        Returns:
            Similarity score (0-1)
        """
        # Extract text from topic
        topic_text = f"{topic.get('topic_name', '')} {topic.get('category', '')}"
        topic_keywords = set(self._extract_keywords(topic_text.lower()))
        
        # Extract text from video
        video_title = video.get('title', '')
        video_desc = video.get('description', '')
        video_text = f"{video_title} {video_desc}"
        video_keywords = set(self._extract_keywords(video_text.lower()))
        
        # Calculate keyword overlap (Jaccard similarity)
        if not topic_keywords or not video_keywords:
            return 0.0
        
        intersection = topic_keywords & video_keywords
        union = topic_keywords | video_keywords
        
        keyword_similarity = len(intersection) / len(union) if union else 0.0
        
        # Boost similarity if specific tech terms match
        tech_terms = {'aws', 'azure', 'cloud', 'kubernetes', 'docker', 'ai', 
                     'machine learning', 'devops', 'security', 'data'}
        
        topic_tech = topic_keywords & tech_terms
        video_tech = video_keywords & tech_terms
        tech_overlap = topic_tech & video_tech
        
        tech_boost = 0.2 if tech_overlap else 0.0
        
        # Final similarity score
        similarity = min(keyword_similarity + tech_boost, 1.0)
        
        return similarity
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extract meaningful keywords from text.
        
        Args:
            text: Text to extract keywords from
            
        Returns:
            List of keywords
        """
        # Remove common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at',
                     'to', 'for', 'of', 'with', 'by', 'from', 'as', 'is', 'was',
                     'are', 'were', 'been', 'be', 'have', 'has', 'had', 'do',
                     'does', 'did', 'will', 'would', 'could', 'should', 'may',
                     'might', 'must', 'can', 'this', 'that', 'these', 'those'}
        
        # Split into words and filter
        words = re.findall(r'\b\w+\b', text.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        return keywords
    
    def extract_stock_tickers(
        self,
        text: str
    ) -> List[str]:
        """
        Extract stock tickers from text (format: $SYMBOL).
        
        Args:
            text: Text to analyze (title, description, tags)
            
        Returns:
            List of stock ticker symbols (e.g., ['NVDA', 'AMZN', 'MSFT'])
        """
        # Regex pattern for stock tickers: $SYMBOL (1-5 uppercase letters)
        pattern = r'\$([A-Z]{1,5})\b'
        matches = re.findall(pattern, text)
        
        # Return unique tickers
        return list(set(matches))
    
    def extract_companies(
        self,
        text: str
    ) -> List[str]:
        """
        Extract company names from text.
        
        Uses pattern matching and entity recognition.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of company names (e.g., ['NVIDIA', 'Amazon', 'Microsoft'])
        """
        found_companies = []
        text_lower = text.lower()
        
        for company in self.TECH_COMPANIES:
            if company.lower() in text_lower:
                found_companies.append(company)
        
        return list(set(found_companies))
    
    def build_finance_context(
        self,
        topic: Dict[str, Any],
        authority_match: bool,
        authority_videos: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Build finance_context dictionary for a topic.
        
        Args:
            topic: Technical topic with metadata
            authority_match: Whether topic matched authority content
            authority_videos: Matched authority videos (if any)
            
        Returns:
            Dictionary with structure:
            {
                "stock_tickers": List[str],
                "mentioned_companies": List[str],
                "macro_relevance_score": float (0-1),
                "authority_channel_match": bool
            }
        """
        # Extract text from topic
        topic_text = f"{topic.get('topic_name', '')} {topic.get('category', '')}"
        
        # Extract from top videos if available
        if 'top_videos' in topic:
            for video in topic['top_videos'][:3]:  # Check top 3 videos
                video_text = f"{video.get('title', '')} {video.get('description', '')}"
                topic_text += f" {video_text}"
        
        # Extract stock tickers and companies
        stock_tickers = self.extract_stock_tickers(topic_text)
        mentioned_companies = self.extract_companies(topic_text)
        
        # Calculate macro relevance score
        # Base score on authority match and financial entity presence
        macro_relevance_score = 0.0
        
        if authority_match:
            macro_relevance_score += 0.5
        
        if stock_tickers:
            macro_relevance_score += 0.25
        
        if mentioned_companies:
            macro_relevance_score += 0.25
        
        # Cap at 1.0
        macro_relevance_score = min(macro_relevance_score, 1.0)
        
        return {
            'stock_tickers': stock_tickers,
            'mentioned_companies': mentioned_companies,
            'macro_relevance_score': macro_relevance_score,
            'authority_channel_match': authority_match
        }
    
    def apply_macro_bonus(
        self,
        topics: List[Dict[str, Any]],
        match_status: Dict[str, bool]
    ) -> List[Dict[str, Any]]:
        """
        Apply 2x trend score bonus to cross-referenced topics.
        
        Args:
            topics: List of topics with trend scores
            match_status: Dictionary mapping topic names to match status
            
        Returns:
            Topics with enhanced trend scores (capped at 100)
        """
        logger.info("Applying macro bonus to matched topics")
        
        bonus_count = 0
        
        for topic in topics:
            topic_name = topic.get('topic_name', '')
            
            if match_status.get(topic_name, False):
                original_score = topic.get('trend_score', 0)
                enhanced_score = min(original_score * 2.0, 100.0)
                topic['trend_score'] = enhanced_score
                
                logger.debug("Applied macro bonus to '%s': %.2f -> %.2f",
                           topic_name[:50], original_score, enhanced_score)
                bonus_count += 1
        
        logger.info("Applied macro bonus to %d topics", bonus_count)
        
        return topics

    def merge_all_sources(
        self,
        google_trends: List[Dict[str, Any]],
        reddit_posts: List[Dict[str, Any]],
        yahoo_finance: Dict[str, Any],
        wikipedia_events: List[Dict[str, Any]],
        youtube_topics: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Merge topics from all 5 sources into a unified list.

        Each source's data is normalized into a common topic format with
        topic_name, source_name, source_url, and raw_data.

        Args:
            google_trends: Topics from GoogleTrendsClient
            reddit_posts: Posts from RedditClient
            yahoo_finance: Market data from YahooFinanceClient
            wikipedia_events: Events from WikipediaEventsClient
            youtube_topics: Topics from existing YouTube pipeline

        Returns:
            Unified list of topic dicts with normalized format
        """
        now = datetime.now(timezone.utc).isoformat()
        unified: List[Dict[str, Any]] = []

        # --- Google Trends ---
        for item in (google_trends or []):
            unified.append({
                'topic_name': item.get('topic_name', ''),
                'source_name': 'google_trends',
                'source_url': item.get('source_url', 'https://trends.google.com'),
                'fetched_at': item.get('fetched_at', now),
                'raw_data': item,
                'sources': [{
                    'source_name': 'google_trends',
                    'source_url': item.get('source_url', 'https://trends.google.com'),
                    'fetched_at': item.get('fetched_at', now),
                }],
                'source_count': 1,
                'trend_score': 0.0,
                'high_confidence': False,
            })

        # --- Reddit ---
        for item in (reddit_posts or []):
            permalink = item.get('permalink', '')
            source_url = f"https://www.reddit.com{permalink}" if permalink else 'https://www.reddit.com'
            unified.append({
                'topic_name': item.get('title', ''),
                'source_name': 'reddit',
                'source_url': source_url,
                'fetched_at': item.get('fetched_at', now),
                'raw_data': item,
                'sources': [{
                    'source_name': 'reddit',
                    'source_url': source_url,
                    'fetched_at': item.get('fetched_at', now),
                }],
                'source_count': 1,
                'trend_score': 0.0,
                'high_confidence': False,
            })

        # --- Yahoo Finance ---
        yahoo = yahoo_finance or {}
        for category_key in ('gainers', 'losers', 'most_active', 'story_triggers'):
            for item in yahoo.get(category_key, []):
                symbol = item.get('symbol', '')
                name = item.get('name', symbol)
                topic_name = f"{name} ({symbol})" if name and symbol else (name or symbol)
                unified.append({
                    'topic_name': topic_name,
                    'source_name': 'yahoo_finance',
                    'source_url': f"https://finance.yahoo.com/quote/{symbol}" if symbol else 'https://finance.yahoo.com',
                    'fetched_at': item.get('fetched_at', now),
                    'raw_data': item,
                    'sources': [{
                        'source_name': 'yahoo_finance',
                        'source_url': f"https://finance.yahoo.com/quote/{symbol}" if symbol else 'https://finance.yahoo.com',
                        'fetched_at': item.get('fetched_at', now),
                    }],
                    'source_count': 1,
                    'trend_score': 0.0,
                    'high_confidence': False,
                })

        # --- Wikipedia Events ---
        for item in (wikipedia_events or []):
            related_links = item.get('related_links', [])
            source_url = related_links[0] if related_links else 'https://en.wikipedia.org/wiki/Portal:Current_events'
            unified.append({
                'topic_name': item.get('headline', ''),
                'source_name': 'wikipedia',
                'source_url': source_url,
                'fetched_at': item.get('fetched_at', now),
                'raw_data': item,
                'sources': [{
                    'source_name': 'wikipedia',
                    'source_url': source_url,
                    'fetched_at': item.get('fetched_at', now),
                }],
                'source_count': 1,
                'trend_score': 0.0,
                'high_confidence': False,
            })

        # --- YouTube ---
        for item in (youtube_topics or []):
            topic_name = item.get('topic_name', '')
            unified.append({
                'topic_name': topic_name,
                'source_name': 'youtube',
                'source_url': item.get('source_url', 'https://www.youtube.com'),
                'fetched_at': item.get('fetched_at', now),
                'raw_data': item,
                'sources': [{
                    'source_name': 'youtube',
                    'source_url': item.get('source_url', 'https://www.youtube.com'),
                    'fetched_at': item.get('fetched_at', now),
                }],
                'source_count': 1,
                'trend_score': 0.0,
                'high_confidence': False,
            })

        logger.info(
            "Merged %d topics from 5 sources (GT=%d, RD=%d, YF=%d, WK=%d, YT=%d)",
            len(unified),
            len(google_trends or []),
            len(reddit_posts or []),
            sum(len(yahoo.get(k, [])) for k in ('gainers', 'losers', 'most_active', 'story_triggers')),
            len(wikipedia_events or []),
            len(youtube_topics or []),
        )
        return unified

    def deduplicate_topics(
        self,
        topics: List[Dict[str, Any]],
        similarity_threshold: float = 0.75
    ) -> List[Dict[str, Any]]:
        """
        Deduplicate topics using keyword matching and semantic similarity.

        When the same topic appears in multiple sources, merges into a single
        entry with a combined source list.

        Args:
            topics: Raw topic list from all sources
            similarity_threshold: Minimum similarity for dedup (default: 0.75)

        Returns:
            Deduplicated topic list with merged source metadata
        """
        if not topics:
            return []

        merged: List[Dict[str, Any]] = []

        for topic in topics:
            best_match_idx = -1
            best_similarity = 0.0

            topic_name = topic.get('topic_name', '')
            topic_keywords = set(self._extract_keywords(topic_name.lower()))

            for idx, existing in enumerate(merged):
                existing_name = existing.get('topic_name', '')
                existing_keywords = set(self._extract_keywords(existing_name.lower()))

                # Calculate Jaccard similarity on keywords
                if not topic_keywords or not existing_keywords:
                    continue

                intersection = topic_keywords & existing_keywords
                union = topic_keywords | existing_keywords
                similarity = len(intersection) / len(union) if union else 0.0

                if similarity >= similarity_threshold and similarity > best_similarity:
                    best_similarity = similarity
                    best_match_idx = idx

            if best_match_idx >= 0:
                # Merge into existing entry
                existing = merged[best_match_idx]
                existing['sources'].extend(topic.get('sources', []))
                existing['source_count'] = len(existing['sources'])
                logger.debug(
                    "Dedup merged '%s' into '%s' (similarity=%.2f)",
                    topic_name[:40], existing['topic_name'][:40], best_similarity,
                )
            else:
                # New unique topic
                merged.append(dict(topic))

        logger.info(
            "Deduplicated %d topics down to %d (threshold=%.2f)",
            len(topics), len(merged), similarity_threshold,
        )
        return merged

    def calculate_cross_source_score(
        self,
        topic: Dict[str, Any]
    ) -> float:
        """
        Calculate Trend_Score weighted by number of sources.

        Topics appearing in more sources score higher.
        Score is normalized to 0-100 range.

        Args:
            topic: Merged topic with source list

        Returns:
            Cross-source Trend_Score (0-100)
        """
        source_count = topic.get('source_count', 1)
        base_score = topic.get('trend_score', 0.0)

        # Weight by source count: each additional source adds 20 points on a base of 20
        # 1 source = 20, 2 sources = 40, 3 sources = 60, 4 sources = 80, 5 sources = 100
        source_score = min(source_count * 20.0, 100.0)

        # Blend base score (if any) with source-derived score
        if base_score > 0:
            score = (base_score * 0.5) + (source_score * 0.5)
        else:
            score = source_score

        # Normalize to 0-100
        score = max(0.0, min(score, 100.0))

        # Mark high confidence inline
        if source_count >= 3:
            topic['high_confidence'] = True

        topic['trend_score'] = score
        return score

    def mark_high_confidence(
        self,
        topics: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Mark topics appearing in 3+ sources as high_confidence.

        Args:
            topics: Deduplicated topic list

        Returns:
            Topics with high_confidence flag set
        """
        for topic in topics:
            source_count = topic.get('source_count', 1)
            topic['high_confidence'] = source_count >= 3

        high_count = sum(1 for t in topics if t.get('high_confidence'))
        logger.info(
            "Marked %d/%d topics as high_confidence (3+ sources)",
            high_count, len(topics),
        )
        return topics

