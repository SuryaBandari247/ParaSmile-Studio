"""
Unit tests for TopicAnalyzer.
"""

import pytest
from datetime import datetime, timezone, timedelta
from research_agent.analyzer import TopicAnalyzer
from research_agent.models import VideoMetadata


class TestTopicClassification:
    """Tests for classify_topic method."""
    
    def test_classify_python_video(self):
        """Test classification of a Python programming video."""
        analyzer = TopicAnalyzer()
        
        video = {
            'title': 'Python Tutorial for Beginners',
            'description': 'Learn Python programming from scratch',
            'tags': ['python', 'programming', 'tutorial']
        }
        
        category, confidence = analyzer.classify_topic(video)
        
        assert category == 'Programming Languages'
        assert confidence >= 0.6
    
    def test_classify_devops_video(self):
        """Test classification of a DevOps video."""
        analyzer = TopicAnalyzer()
        
        video = {
            'title': 'CI/CD Pipeline with Jenkins',
            'description': 'Build automated deployment pipelines using Jenkins and GitLab CI',
            'tags': ['devops', 'jenkins', 'ci/cd', 'automation']
        }
        
        category, confidence = analyzer.classify_topic(video)
        
        assert category == 'DevOps'
        assert confidence >= 0.6
    
    def test_classify_cloud_video(self):
        """Test classification of a cloud infrastructure video."""
        analyzer = TopicAnalyzer()
        
        video = {
            'title': 'AWS Lambda Serverless Tutorial',
            'description': 'Deploy serverless functions on AWS using Lambda and API Gateway',
            'tags': ['aws', 'lambda', 'serverless', 'cloud']
        }
        
        category, confidence = analyzer.classify_topic(video)
        
        assert category == 'Cloud Infrastructure'
        assert confidence >= 0.6
    
    def test_classify_security_video(self):
        """Test classification of a security video."""
        analyzer = TopicAnalyzer()
        
        video = {
            'title': 'OAuth 2.0 Authentication Explained',
            'description': 'Learn about OAuth authentication and authorization flows',
            'tags': ['security', 'oauth', 'authentication']
        }
        
        category, confidence = analyzer.classify_topic(video)
        
        assert category == 'Security'
        assert confidence >= 0.6
    
    def test_classify_data_engineering_video(self):
        """Test classification of a data engineering video."""
        analyzer = TopicAnalyzer()
        
        video = {
            'title': 'Building ETL Pipelines with Apache Airflow',
            'description': 'Create data pipelines for big data processing using Airflow and Spark',
            'tags': ['data engineering', 'etl', 'airflow', 'spark']
        }
        
        category, confidence = analyzer.classify_topic(video)
        
        assert category == 'Data Engineering'
        assert confidence >= 0.6
    
    def test_classify_architecture_video(self):
        """Test classification of a software architecture video."""
        analyzer = TopicAnalyzer()
        
        video = {
            'title': 'Microservices Design Patterns',
            'description': 'Learn about microservices architecture and distributed systems design',
            'tags': ['architecture', 'microservices', 'design patterns']
        }
        
        category, confidence = analyzer.classify_topic(video)
        
        assert category == 'Software Architecture'
        assert confidence >= 0.6
    
    def test_classify_low_confidence_as_uncategorized(self):
        """Test that videos with low confidence are marked as Uncategorized."""
        analyzer = TopicAnalyzer()
        
        video = {
            'title': 'How to Make Money Online',
            'description': 'Tips and tricks for making money on the internet',
            'tags': ['money', 'online', 'business']
        }
        
        category, confidence = analyzer.classify_topic(video)
        
        assert category == 'Uncategorized'
        assert confidence < 0.6
    
    def test_classify_empty_video_metadata(self):
        """Test classification with empty metadata."""
        analyzer = TopicAnalyzer()
        
        video = {
            'title': '',
            'description': '',
            'tags': []
        }
        
        category, confidence = analyzer.classify_topic(video)
        
        assert category == 'Uncategorized'
        assert confidence == 0.0
    
    def test_classify_with_video_metadata_object(self):
        """Test classification using VideoMetadata object."""
        analyzer = TopicAnalyzer()
        
        video = VideoMetadata(
            video_id='test123',
            title='Kubernetes Tutorial',
            description='Learn Kubernetes container orchestration',
            channel_id='channel123',
            channel_title='Tech Channel',
            published_at=datetime.now(timezone.utc),
            tags=['kubernetes', 'k8s', 'docker', 'container'],
            view_count=10000,
            like_count=500,
            comment_count=100,
            duration='PT10M'
        )
        
        category, confidence = analyzer.classify_topic(video)
        
        assert category == 'Cloud Infrastructure'
        assert confidence >= 0.6
    
    def test_confidence_score_bounds(self):
        """Test that confidence scores are always between 0 and 1."""
        analyzer = TopicAnalyzer()
        
        # Test with highly relevant video
        video = {
            'title': 'Python JavaScript Java C++ Ruby Go Rust TypeScript',
            'description': 'Programming languages tutorial',
            'tags': ['python', 'javascript', 'java']
        }
        
        category, confidence = analyzer.classify_topic(video)
        
        assert 0.0 <= confidence <= 1.0
    
    def test_title_weighted_more_than_description(self):
        """Test that title matches are weighted more heavily than description."""
        analyzer = TopicAnalyzer()
        
        # Video with keyword in title
        video_title = {
            'title': 'Python Tutorial',
            'description': '',
            'tags': []
        }
        
        # Video with keyword in description only
        video_description = {
            'title': '',
            'description': 'Python Tutorial',
            'tags': []
        }
        
        _, confidence_title = analyzer.classify_topic(video_title)
        _, confidence_description = analyzer.classify_topic(video_description)
        
        # Title should have higher confidence due to 3x weighting
        assert confidence_title > confidence_description
    
    def test_all_categories_are_valid(self):
        """Test that all returned categories are from the valid set."""
        analyzer = TopicAnalyzer()
        
        valid_categories = {
            'Programming Languages',
            'DevOps',
            'Cloud Infrastructure',
            'Software Architecture',
            'Security',
            'Data Engineering',
            'Uncategorized'
        }
        
        test_videos = [
            {'title': 'Python', 'description': '', 'tags': []},
            {'title': 'DevOps', 'description': '', 'tags': []},
            {'title': 'AWS', 'description': '', 'tags': []},
            {'title': 'Random Video', 'description': '', 'tags': []},
        ]
        
        for video in test_videos:
            category, _ = analyzer.classify_topic(video)
            assert category in valid_categories



class TestTrendAnalysis:
    """Tests for analyze_trends method."""
    
    def test_analyze_trends_basic(self):
        """Test basic trend analysis with multiple videos."""
        analyzer = TopicAnalyzer()
        
        # Create test videos
        now = datetime.now(timezone.utc)
        videos = [
            VideoMetadata(
                video_id='vid1',
                title='Python Tutorial',
                description='Learn Python',
                channel_id='ch1',
                channel_title='Tech Channel',
                published_at=now - timedelta(hours=12),
                tags=['python', 'programming'],
                view_count=10000,
                like_count=500,
                comment_count=100,
                duration='PT10M'
            ),
            VideoMetadata(
                video_id='vid2',
                title='DevOps Guide',
                description='Learn DevOps',
                channel_id='ch2',
                channel_title='DevOps Channel',
                published_at=now - timedelta(hours=48),
                tags=['devops', 'ci/cd'],
                view_count=5000,
                like_count=200,
                comment_count=50,
                duration='PT15M'
            ),
            VideoMetadata(
                video_id='vid3',
                title='Low Score Video',
                description='Not trending',
                channel_id='ch3',
                channel_title='Random Channel',
                published_at=now - timedelta(days=6),
                tags=[],
                view_count=100,
                like_count=1,
                comment_count=0,
                duration='PT5M'
            )
        ]
        
        topics = analyzer.analyze_trends(videos, min_score=30)
        
        # Should filter out low-scoring video
        assert len(topics) <= 2
        
        # All topics should have score >= 30
        for topic in topics:
            assert topic.trend_score >= 30
        
        # Topics should be sorted by trend score (descending)
        for i in range(len(topics) - 1):
            assert topics[i].trend_score >= topics[i + 1].trend_score
    
    def test_analyze_trends_filters_low_scores(self):
        """Test that videos below min_score are filtered out."""
        analyzer = TopicAnalyzer()
        
        now = datetime.now(timezone.utc)
        videos = [
            VideoMetadata(
                video_id='vid1',
                title='High Score Video',
                description='Trending content',
                channel_id='ch1',
                channel_title='Tech Channel',
                published_at=now - timedelta(hours=12),
                tags=['python', 'programming'],
                view_count=100000,
                like_count=5000,
                comment_count=1000,
                duration='PT10M'
            ),
            VideoMetadata(
                video_id='vid2',
                title='Low Score Video',
                description='Not trending',
                channel_id='ch2',
                channel_title='Random Channel',
                published_at=now - timedelta(days=6),
                tags=[],
                view_count=50,
                like_count=1,
                comment_count=0,
                duration='PT5M'
            )
        ]
        
        topics = analyzer.analyze_trends(videos, min_score=30)
        
        # Only high-scoring video should be included
        assert len(topics) == 1
        assert topics[0].topic_name == 'High Score Video'
    
    def test_analyze_trends_classifies_videos(self):
        """Test that videos are classified into technical categories."""
        analyzer = TopicAnalyzer()
        
        now = datetime.now(timezone.utc)
        videos = [
            VideoMetadata(
                video_id='vid1',
                title='Python Programming Tutorial',
                description='Learn Python programming',
                channel_id='ch1',
                channel_title='Tech Channel',
                published_at=now - timedelta(hours=12),
                tags=['python', 'programming', 'tutorial'],
                view_count=10000,
                like_count=500,
                comment_count=100,
                duration='PT10M'
            )
        ]
        
        topics = analyzer.analyze_trends(videos, min_score=0)
        
        assert len(topics) == 1
        assert topics[0].category == 'Programming Languages'
        assert topics[0].category_confidence >= 0.6
    
    def test_analyze_trends_sorts_by_score_then_views(self):
        """Test that topics are sorted by trend score, with view count as tie-breaker."""
        analyzer = TopicAnalyzer()
        
        now = datetime.now(timezone.utc)
        
        # Create videos with similar scores but different view counts
        videos = [
            VideoMetadata(
                video_id='vid1',
                title='Topic A',
                description='Python tutorial',
                channel_id='ch1',
                channel_title='Channel 1',
                published_at=now - timedelta(hours=48),
                tags=['python'],
                view_count=5000,  # Lower views
                like_count=250,
                comment_count=50,
                duration='PT10M'
            ),
            VideoMetadata(
                video_id='vid2',
                title='Topic B',
                description='Python guide',
                channel_id='ch2',
                channel_title='Channel 2',
                published_at=now - timedelta(hours=48),
                tags=['python'],
                view_count=10000,  # Higher views
                like_count=500,
                comment_count=100,
                duration='PT10M'
            )
        ]
        
        topics = analyzer.analyze_trends(videos, min_score=0)
        
        # Both should be included
        assert len(topics) == 2
        
        # If scores are similar, higher view count should rank first
        # (Topic B has more views)
        if abs(topics[0].trend_score - topics[1].trend_score) < 1.0:
            # Scores are similar, check view count ordering
            topic_names = [t.topic_name for t in topics]
            assert topic_names.index('Topic B') < topic_names.index('Topic A')
    
    def test_analyze_trends_groups_by_topic_name(self):
        """Test that videos are grouped by topic name (title)."""
        analyzer = TopicAnalyzer()
        
        now = datetime.now(timezone.utc)
        
        # Create multiple videos with same title
        videos = [
            VideoMetadata(
                video_id='vid1',
                title='Python Tutorial',
                description='Part 1',
                channel_id='ch1',
                channel_title='Channel 1',
                published_at=now - timedelta(hours=12),
                tags=['python'],
                view_count=10000,
                like_count=500,
                comment_count=100,
                duration='PT10M'
            ),
            VideoMetadata(
                video_id='vid2',
                title='Python Tutorial',
                description='Part 2',
                channel_id='ch1',
                channel_title='Channel 1',
                published_at=now - timedelta(hours=24),
                tags=['python'],
                view_count=8000,
                like_count=400,
                comment_count=80,
                duration='PT10M'
            )
        ]
        
        topics = analyzer.analyze_trends(videos, min_score=0)
        
        # Should be grouped into one topic
        assert len(topics) == 1
        assert topics[0].topic_name == 'Python Tutorial'
        assert topics[0].video_count == 2
    
    def test_analyze_trends_returns_trending_topic_objects(self):
        """Test that analyze_trends returns TrendingTopic objects."""
        from research_agent.models import TrendingTopic
        
        analyzer = TopicAnalyzer()
        
        now = datetime.now(timezone.utc)
        videos = [
            VideoMetadata(
                video_id='vid1',
                title='Python Tutorial',
                description='Learn Python',
                channel_id='ch1',
                channel_title='Tech Channel',
                published_at=now - timedelta(hours=12),
                tags=['python', 'programming'],
                view_count=10000,
                like_count=500,
                comment_count=100,
                duration='PT10M'
            )
        ]
        
        topics = analyzer.analyze_trends(videos, min_score=0)
        
        assert len(topics) == 1
        assert isinstance(topics[0], TrendingTopic)
        assert topics[0].topic_name == 'Python Tutorial'
        assert topics[0].category == 'Programming Languages'
        assert 0 <= topics[0].trend_score <= 100
        assert topics[0].video_count == 1
        assert len(topics[0].top_videos) == 1
        assert topics[0].fetched_at is not None
    
    def test_analyze_trends_with_dict_videos(self):
        """Test analyze_trends with dict-based video data."""
        analyzer = TopicAnalyzer()
        
        now = datetime.now(timezone.utc)
        videos = [
            {
                'video_id': 'vid1',
                'title': 'Python Tutorial',
                'description': 'Learn Python',
                'channel_id': 'ch1',
                'channel_title': 'Tech Channel',
                'published_at': now - timedelta(hours=12),
                'tags': ['python', 'programming'],
                'view_count': 10000,
                'like_count': 500,
                'comment_count': 100,
                'duration': 'PT10M'
            }
        ]
        
        topics = analyzer.analyze_trends(videos, min_score=0)
        
        assert len(topics) == 1
        assert topics[0].topic_name == 'Python Tutorial'
    
    def test_analyze_trends_empty_list(self):
        """Test analyze_trends with empty video list."""
        analyzer = TopicAnalyzer()
        
        topics = analyzer.analyze_trends([], min_score=30)
        
        assert topics == []
    
    def test_analyze_trends_default_min_score(self):
        """Test that default min_score is 30."""
        analyzer = TopicAnalyzer()
        
        now = datetime.now(timezone.utc)
        videos = [
            VideoMetadata(
                video_id='vid1',
                title='Low Score Video',
                description='Not trending',
                channel_id='ch1',
                channel_title='Channel',
                published_at=now - timedelta(days=6),
                tags=[],
                view_count=100,
                like_count=1,
                comment_count=0,
                duration='PT5M'
            )
        ]
        
        # Call without min_score parameter (should default to 30)
        topics = analyzer.analyze_trends(videos)
        
        # Low-scoring video should be filtered out
        assert len(topics) == 0
