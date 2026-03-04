"""
Topic Analyzer for the Research Agent.

This module analyzes video data to identify and score trending topics.
Implements trend scoring algorithm and topic classification.
"""

from datetime import datetime, timezone
from typing import Dict, Any, TYPE_CHECKING, Optional
from research_agent.models import VideoMetadata

if TYPE_CHECKING:
    from research_agent.models import TrendingTopic


class TopicAnalyzer:
    """
    Analyzes video data to identify and score trending topics.
    Implements trend scoring algorithm and topic classification.
    """
    
    # Negative keywords to filter out non-technical content
    NEGATIVE_KEYWORDS = [
        'snake', 'reptile', 'zoo', 'egg', 'animal', 'pet', 'wildlife',
        'cooking', 'recipe', 'food', 'restaurant', 'chef',
        'music', 'song', 'album', 'concert', 'band', 'singer',
        'movie', 'film', 'actor', 'actress', 'cinema',
        'sports', 'football', 'basketball', 'soccer', 'game',
        'fashion', 'makeup', 'beauty', 'style', 'outfit',
        'travel', 'vacation', 'tourist', 'destination',
        'vlog', 'daily vlog', 'my day', 'lifestyle',
        'motorcycle', 'bike', 'motorbike', 'biker', 'ride', 'test ride',
        'saas bhi', 'bahu thi', 'episode', 'promo', 'serial', 'drama',
        'divorce', 'wedding', 'marriage', 'love story', 'romance',
        'stock', 'trading', 'invest', 'forex', 'crypto trading'
    ]
    
    # High-RPM keywords that get a 20% bonus
    HIGH_RPM_KEYWORDS = ['docker', 'saas', 'ai', 'artificial intelligence', 'machine learning']
    
    def __init__(self):
        """Initialize the Topic Analyzer."""
        pass
    
    def detect_language(self, text: str) -> str:
        """
        Detect the language of the text.
        
        Uses simple heuristics based on character patterns and common words.
        
        Args:
            text: Text to analyze
            
        Returns:
            Language code: 'EN' (English), 'ES' (Spanish), 'AR' (Arabic), 'OTHER'
        """
        text_lower = text.lower()
        
        # Arabic detection (Arabic script characters)
        arabic_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
        if arabic_chars > len(text) * 0.3:  # 30% Arabic characters
            return 'AR'
        
        # Spanish detection (common Spanish words and patterns)
        spanish_indicators = [
            'el ', 'la ', 'los ', 'las ', 'un ', 'una ', 'de ', 'del ',
            'que ', 'con ', 'por ', 'para ', 'en ', 'es ', 'está ',
            'cómo', 'qué', 'cuál', 'dónde', 'cuándo', 'español'
        ]
        spanish_count = sum(1 for indicator in spanish_indicators if indicator in text_lower)
        if spanish_count >= 3:
            return 'ES'
        
        # English detection (common English words)
        english_indicators = [
            'the ', 'is ', 'are ', 'was ', 'were ', 'have ', 'has ',
            'will ', 'would ', 'can ', 'could ', 'should ', 'this ',
            'that ', 'with ', 'from ', 'how ', 'what ', 'when ', 'where'
        ]
        english_count = sum(1 for indicator in english_indicators if indicator in text_lower)
        if english_count >= 3:
            return 'EN'
        
        # Default to OTHER if no clear match
        return 'OTHER'
    
    def is_technical_content(self, video: Dict[str, Any]) -> bool:
        """
        Check if video contains technical content (not filtered by negative keywords).
        
        Args:
            video: Video metadata with title, description, tags
            
        Returns:
            True if technical content, False if should be filtered out
        """
        # Extract video data
        if isinstance(video, VideoMetadata):
            title = video.title.lower()
            description = video.description.lower()
            tags = [tag.lower() for tag in video.tags]
        else:
            title = video.get('title', '').lower()
            description = video.get('description', '').lower()
            tags = [tag.lower() for tag in video.get('tags', [])]
        
        # Combine all text for analysis
        combined_text = f"{title} {description} {' '.join(tags)}"
        
        # Check for negative keywords
        for negative_kw in self.NEGATIVE_KEYWORDS:
            if negative_kw in combined_text:
                return False
        
        return True
    
    def calculate_trend_score(self, video: Dict[str, Any]) -> float:
        """
        Calculate trend score for a single video.
        
        Formula:
        - View count weight: 40%
        - Engagement rate (likes + comments / views): 30%
        - Recency weight: 30% (2x multiplier for < 24 hours)
        - High-RPM bonus: 20% for Docker, SaaS, AI keywords
        - Normalized to 0-100 scale
        
        Args:
            video: Video metadata with statistics (dict or VideoMetadata)
            
        Returns:
            Trend score (0-100)
        """
        # Extract video data (support both dict and VideoMetadata)
        if isinstance(video, VideoMetadata):
            view_count = video.view_count
            like_count = video.like_count
            comment_count = video.comment_count
            published_at = video.published_at
            title = video.title.lower()
            description = video.description.lower()
            tags = [tag.lower() for tag in video.tags]
        else:
            view_count = video.get('view_count', 0)
            like_count = video.get('like_count', 0)
            comment_count = video.get('comment_count', 0)
            published_at = video.get('published_at')
            title = video.get('title', '').lower()
            description = video.get('description', '').lower()
            tags = [tag.lower() for tag in video.get('tags', [])]
        
        # Handle edge case: zero views
        if view_count == 0:
            return 0.0
        
        # Calculate engagement rate (likes + comments / views)
        engagement_rate = (like_count + comment_count) / view_count
        
        # Calculate recency weight
        now = datetime.now(timezone.utc)
        
        # Handle published_at as string or datetime
        if isinstance(published_at, str):
            published_at = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
        elif published_at.tzinfo is None:
            # Make published_at timezone-aware if it isn't
            published_at = published_at.replace(tzinfo=timezone.utc)
        
        hours_since_published = (now - published_at).total_seconds() / 3600
        
        # Apply 2x multiplier for videos published within 24 hours
        if hours_since_published < 24:
            recency_multiplier = 2.0
        else:
            recency_multiplier = 1.0
        
        # Normalize view count (log scale to handle wide range)
        # Using log10 with a cap at 10M views
        import math
        normalized_views = min(math.log10(view_count + 1) / math.log10(10_000_000 + 1), 1.0)
        
        # Normalize engagement rate (cap at 0.1 = 10% engagement)
        normalized_engagement = min(engagement_rate / 0.1, 1.0)
        
        # Normalize recency (exponential decay over 7 days)
        # Fresh videos (0 hours) = 1.0, 7 days old = ~0.0
        hours_in_week = 7 * 24
        normalized_recency = math.exp(-hours_since_published / hours_in_week)
        
        # Apply weighted formula: 40% views, 30% engagement, 30% recency
        base_score = (
            0.4 * normalized_views +
            0.3 * normalized_engagement +
            0.3 * normalized_recency
        )
        
        # Apply recency multiplier
        final_score = base_score * recency_multiplier
        
        # Check for high-RPM keywords and apply 20% bonus
        combined_text = f"{title} {description} {' '.join(tags)}"
        has_high_rpm_keyword = any(kw in combined_text for kw in self.HIGH_RPM_KEYWORDS)
        if has_high_rpm_keyword:
            final_score *= 1.20  # 20% bonus
        
        # Normalize to 0-100 scale
        # Since recency_multiplier can be 2x and high-RPM bonus is 1.2x, we need to cap at 100
        normalized_score = min(final_score * 100, 100.0)
        
        return normalized_score
    
    def classify_topic(self, video: Dict[str, Any]) -> tuple[str, float]:
        """
        Classify video into technical category.
        
        Categories:
        - Programming Languages
        - DevOps
        - Cloud Infrastructure
        - Software Architecture
        - Security
        - Data Engineering
        - Uncategorized (confidence < 0.6)
        
        Args:
            video: Video metadata with title, description, tags
            
        Returns:
            Tuple of (category, confidence_score)
        """
        # Extract video data (support both dict and VideoMetadata)
        if isinstance(video, VideoMetadata):
            title = video.title.lower()
            description = video.description.lower()
            tags = [tag.lower() for tag in video.tags]
        else:
            title = video.get('title', '').lower()
            description = video.get('description', '').lower()
            tags = [tag.lower() for tag in video.get('tags', [])]
        
        # Combine all text for analysis
        combined_text = f"{title} {description} {' '.join(tags)}"
        
        # Define keyword patterns for each category
        category_keywords = {
            'Programming Languages': [
                'python', 'javascript', 'java', 'c++', 'c#', 'ruby', 'go', 'golang',
                'rust', 'typescript', 'php', 'swift', 'kotlin', 'scala', 'r programming',
                'programming language', 'coding tutorial', 'syntax', 'compiler', 'interpreter'
            ],
            'DevOps': [
                'devops', 'ci/cd', 'continuous integration', 'continuous deployment',
                'jenkins', 'gitlab ci', 'github actions', 'circleci', 'travis ci',
                'automation', 'pipeline', 'deployment', 'infrastructure as code',
                'ansible', 'terraform', 'puppet', 'chef', 'monitoring', 'observability'
            ],
            'Cloud Infrastructure': [
                'aws', 'amazon web services', 'azure', 'microsoft azure', 'gcp',
                'google cloud', 'cloud computing', 'ec2', 's3', 'lambda',
                'kubernetes', 'k8s', 'docker', 'container', 'serverless',
                'cloud native', 'cloud architecture', 'cloud migration'
            ],
            'Software Architecture': [
                'architecture', 'design patterns', 'microservices', 'monolith',
                'scalability', 'system design', 'distributed systems', 'api design',
                'rest api', 'graphql', 'event driven', 'message queue', 'kafka',
                'rabbitmq', 'service mesh', 'clean architecture', 'solid principles'
            ],
            'Security': [
                'security', 'cybersecurity', 'penetration testing', 'ethical hacking',
                'vulnerability', 'encryption', 'authentication', 'authorization',
                'oauth', 'jwt', 'ssl', 'tls', 'firewall', 'intrusion detection',
                'security audit', 'owasp', 'xss', 'sql injection', 'csrf'
            ],
            'Data Engineering': [
                'data engineering', 'data pipeline', 'etl', 'data warehouse',
                'big data', 'hadoop', 'spark', 'airflow', 'data lake',
                'data processing', 'batch processing', 'stream processing',
                'data modeling', 'sql', 'nosql', 'database', 'postgres', 'mongodb'
            ]
        }
        
        # Calculate confidence score for each category
        category_scores = {}
        for category, keywords in category_keywords.items():
            # Weight title matches more heavily (3x)
            title_matches = sum(1 for kw in keywords if kw in title)
            description_matches = sum(1 for kw in keywords if kw in description)
            tag_matches = sum(1 for kw in keywords if any(kw in tag for tag in tags))
            
            # Weighted score: title (3x), description (1x), tags (2x)
            weighted_matches = (title_matches * 3) + description_matches + (tag_matches * 2)
            
            # Normalize by a reasonable threshold (5 matches = 1.0 confidence)
            # This makes it achievable to reach high confidence with a few strong matches
            confidence = min(weighted_matches / 5.0, 1.0)
            category_scores[category] = confidence
        
        # Find category with highest confidence
        if not category_scores:
            return ('Uncategorized', 0.0)
        
        best_category = max(category_scores, key=category_scores.get)
        best_confidence = category_scores[best_category]
        
        # Mark as "Uncategorized" if confidence < 0.6
        if best_confidence < 0.6:
            return ('Uncategorized', best_confidence)
        
        return (best_category, best_confidence)


    def analyze_trends(
        self,
        videos: list[Dict[str, Any]],
        min_score: int = 30
    ) -> list['TrendingTopic']:
        """
        Analyze videos to identify trending topics.

        Args:
            videos: List of video metadata with statistics
            min_score: Minimum trend score threshold (0-100)

        Returns:
            List of TrendingTopic objects, ranked by trend strength
        """
        from collections import defaultdict
        from research_agent.models import TrendingTopic

        # Step 1: Filter out non-technical content using negative keywords
        technical_videos = [v for v in videos if self.is_technical_content(v)]
        
        # Step 2: Calculate trend score for each video
        videos_with_scores = []
        for video in technical_videos:
            score = self.calculate_trend_score(video)
            videos_with_scores.append((video, score))

        # Step 3: Classify each video into technical category and detect language
        videos_with_classification = []
        for video, score in videos_with_scores:
            category, confidence = self.classify_topic(video)
            
            # Detect language
            if isinstance(video, VideoMetadata):
                text_for_lang = f"{video.title} {video.description}"
            else:
                text_for_lang = f"{video.get('title', '')} {video.get('description', '')}"
            language = self.detect_language(text_for_lang)
            
            videos_with_classification.append((video, score, category, confidence, language))

        # Step 4: Filter videos with score < min_score
        filtered_videos = [
            (video, score, category, confidence, language)
            for video, score, category, confidence, language in videos_with_classification
            if score >= min_score
        ]

        # Step 5: Group videos by topic name (using title as topic name)
        topics_dict = defaultdict(list)
        for video, score, category, confidence, language in filtered_videos:
            # Extract topic name from video (use title as topic identifier)
            if isinstance(video, VideoMetadata):
                topic_name = video.title
            else:
                topic_name = video.get('title', 'Unknown')

            topics_dict[topic_name].append({
                'video': video,
                'score': score,
                'category': category,
                'confidence': confidence,
                'language': language
            })

        # Step 6: Create TrendingTopic objects
        trending_topics = []
        for topic_name, topic_videos in topics_dict.items():
            # Calculate aggregate trend score (average of all videos in topic)
            avg_score = sum(v['score'] for v in topic_videos) / len(topic_videos)

            # Use the category with highest confidence
            best_category = max(topic_videos, key=lambda v: v['confidence'])
            
            # Determine primary language (most common)
            languages = [v['language'] for v in topic_videos]
            primary_language = max(set(languages), key=languages.count)

            # Calculate total view count for tie-breaking
            total_views = sum(
                v['video'].view_count if isinstance(v['video'], VideoMetadata)
                else v['video'].get('view_count', 0)
                for v in topic_videos
            )

            # Convert video dicts to VideoMetadata if needed
            video_objects = []
            for v in topic_videos:
                if isinstance(v['video'], VideoMetadata):
                    video_objects.append(v['video'])
                else:
                    # Convert dict to VideoMetadata
                    video_dict = v['video']
                    video_objects.append(VideoMetadata(
                        video_id=video_dict.get('video_id', ''),
                        title=video_dict.get('title', ''),
                        description=video_dict.get('description', ''),
                        channel_id=video_dict.get('channel_id', ''),
                        channel_title=video_dict.get('channel_title', ''),
                        published_at=video_dict.get('published_at', datetime.now(timezone.utc)),
                        tags=video_dict.get('tags', []),
                        view_count=video_dict.get('view_count', 0),
                        like_count=video_dict.get('like_count', 0),
                        comment_count=video_dict.get('comment_count', 0),
                        duration=video_dict.get('duration', 'PT0S')
                    ))

            trending_topic = TrendingTopic(
                topic_name=topic_name,
                category=best_category['category'],
                category_confidence=best_category['confidence'],
                trend_score=avg_score,
                video_count=len(topic_videos),
                top_videos=video_objects,
                fetched_at=datetime.now(timezone.utc)
            )

            # Store metadata for sorting and language tagging
            trending_topic._total_views = total_views
            trending_topic._language = primary_language
            trending_topics.append(trending_topic)

        # Step 7: Rank topics by trend score (descending), tie-break by view count
        trending_topics.sort(
            key=lambda t: (t.trend_score, t._total_views),
            reverse=True
        )

        # Clean up temporary attributes (keep language for output)
        for topic in trending_topics:
            delattr(topic, '_total_views')

        return trending_topics

