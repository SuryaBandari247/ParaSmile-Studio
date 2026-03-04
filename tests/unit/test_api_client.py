"""
Unit tests for YouTubeAPIClient.

Tests authentication, API key validation, and rate limiter integration.
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock

from research_agent.api_client import YouTubeAPIClient
from research_agent.exceptions import AuthenticationError
from research_agent.rate_limiter import APIRateLimiter


class TestYouTubeAPIClientInitialization:
    """Test YouTubeAPIClient initialization and authentication."""
    
    def test_missing_api_key_raises_authentication_error(self):
        """Test that missing API key raises AuthenticationError."""
        # Clear environment variable and prevent load_dotenv from re-populating it
        with patch('research_agent.api_client.load_dotenv'):
            with patch.dict(os.environ, {}, clear=True):
                with pytest.raises(AuthenticationError, match="YouTube API key is required"):
                    YouTubeAPIClient(api_key=None)
    
    def test_empty_string_api_key_raises_authentication_error(self):
        """Test that empty string API key raises AuthenticationError."""
        # Prevent load_dotenv from populating YOUTUBE_API_KEY from .env
        with patch('research_agent.api_client.load_dotenv'):
            with patch.dict(os.environ, {}, clear=True):
                with pytest.raises(AuthenticationError, match="YouTube API key is required"):
                    YouTubeAPIClient(api_key="")
    
    def test_whitespace_only_api_key_raises_authentication_error(self):
        """Test that whitespace-only API key raises AuthenticationError."""
        with pytest.raises(AuthenticationError, match="must be a non-empty string"):
            YouTubeAPIClient(api_key="   ")
    
    @patch('research_agent.api_client.build')
    def test_valid_api_key_initializes_successfully(self, mock_build):
        """Test that valid API key initializes client successfully."""
        mock_build.return_value = MagicMock()
        
        client = YouTubeAPIClient(api_key="valid_test_key_123")
        
        assert client.api_key == "valid_test_key_123"
        assert isinstance(client.rate_limiter, APIRateLimiter)
        mock_build.assert_called_once_with('youtube', 'v3', developerKey="valid_test_key_123")
    
    @patch('research_agent.api_client.build')
    def test_api_key_from_environment_variable(self, mock_build):
        """Test that API key is loaded from YOUTUBE_API_KEY environment variable."""
        mock_build.return_value = MagicMock()
        
        with patch.dict(os.environ, {'YOUTUBE_API_KEY': 'env_test_key_456'}):
            client = YouTubeAPIClient()
            
            assert client.api_key == "env_test_key_456"
            mock_build.assert_called_once_with('youtube', 'v3', developerKey="env_test_key_456")
    
    @patch('research_agent.api_client.build')
    def test_explicit_api_key_overrides_environment(self, mock_build):
        """Test that explicit API key parameter overrides environment variable."""
        mock_build.return_value = MagicMock()
        
        with patch.dict(os.environ, {'YOUTUBE_API_KEY': 'env_key'}):
            client = YouTubeAPIClient(api_key="explicit_key")
            
            assert client.api_key == "explicit_key"
            mock_build.assert_called_once_with('youtube', 'v3', developerKey="explicit_key")
    
    @patch('research_agent.api_client.build')
    def test_rate_limiter_integration(self, mock_build):
        """Test that rate limiter is properly integrated."""
        mock_build.return_value = MagicMock()
        custom_limiter = APIRateLimiter(daily_quota=5000)
        
        client = YouTubeAPIClient(api_key="test_key", rate_limiter=custom_limiter)
        
        assert client.rate_limiter is custom_limiter
        assert client.rate_limiter.daily_quota == 5000
    
    @patch('research_agent.api_client.build')
    def test_default_rate_limiter_created_when_none_provided(self, mock_build):
        """Test that default rate limiter is created when none provided."""
        mock_build.return_value = MagicMock()
        
        client = YouTubeAPIClient(api_key="test_key")
        
        assert isinstance(client.rate_limiter, APIRateLimiter)
        assert client.rate_limiter.daily_quota == 10000  # Default quota
    
    @patch('research_agent.api_client.build')
    def test_youtube_api_v3_service_built(self, mock_build):
        """Test that YouTube Data API v3 service is built."""
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        
        client = YouTubeAPIClient(api_key="test_key")
        
        assert client.youtube is mock_service
        mock_build.assert_called_once_with('youtube', 'v3', developerKey="test_key")
    
    @patch('research_agent.api_client.build')
    def test_build_failure_raises_authentication_error(self, mock_build):
        """Test that failure to build YouTube service raises AuthenticationError."""
        mock_build.side_effect = Exception("Invalid API key")
        
        with pytest.raises(AuthenticationError, match="Failed to authenticate with YouTube API"):
            YouTubeAPIClient(api_key="invalid_key")


class TestYouTubeAPIClientDotenvIntegration:
    """Test .env file loading with python-dotenv."""
    
    @patch('research_agent.api_client.load_dotenv')
    @patch('research_agent.api_client.build')
    def test_load_dotenv_called_on_initialization(self, mock_build, mock_load_dotenv):
        """Test that load_dotenv is called during initialization."""
        mock_build.return_value = MagicMock()
        
        with patch.dict(os.environ, {'YOUTUBE_API_KEY': 'test_key'}):
            YouTubeAPIClient()
        
        mock_load_dotenv.assert_called_once()



class TestYouTubeAPIClientSearchVideos:
    """Test YouTubeAPIClient.search_videos method."""

    @patch('research_agent.api_client.build')
    def test_search_videos_pre_flight_quota_check(self, mock_build):
        """Test that search performs pre-flight quota check."""
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        # Create rate limiter with insufficient quota
        rate_limiter = APIRateLimiter(daily_quota=10000)
        rate_limiter.consumed = 9950  # Only 50 units remaining, need 100

        client = YouTubeAPIClient(api_key="test_key", rate_limiter=rate_limiter)

        from research_agent.exceptions import QuotaExceededError
        with pytest.raises(QuotaExceededError):
            client.search_videos(
                query="python tutorial",
                published_after="2024-01-01T00:00:00Z",
                published_before="2024-01-08T00:00:00Z"
            )

    @patch('research_agent.api_client.build')
    def test_search_videos_builds_correct_request(self, mock_build):
        """Test that search builds YouTube API request with correct parameters."""
        mock_service = MagicMock()
        mock_search = MagicMock()
        mock_list = MagicMock()
        mock_request = MagicMock()

        mock_service.search.return_value = mock_search
        mock_search.list.return_value = mock_request
        mock_request.execute.return_value = {'items': []}
        mock_build.return_value = mock_service

        client = YouTubeAPIClient(api_key="test_key")

        client.search_videos(
            query="kubernetes tutorial",
            published_after="2024-01-01T00:00:00Z",
            published_before="2024-01-08T00:00:00Z",
            max_results=25
        )

        # Verify search().list() was called with correct parameters
        mock_search.list.assert_called_once_with(
            part='snippet',
            q='kubernetes tutorial',
            type='video',
            publishedAfter='2024-01-01T00:00:00Z',
            publishedBefore='2024-01-08T00:00:00Z',
            maxResults=25,
            order='relevance'
        )

    @patch('research_agent.api_client.build')
    def test_search_videos_parses_response_correctly(self, mock_build):
        """Test that search parses API response into video metadata dictionaries."""
        mock_service = MagicMock()
        mock_search = MagicMock()
        mock_list = MagicMock()
        mock_request = MagicMock()

        # Mock API response
        mock_response = {
            'items': [
                {
                    'id': {'videoId': 'abc123'},
                    'snippet': {
                        'title': 'Python Tutorial',
                        'description': 'Learn Python basics',
                        'channelId': 'channel_1',
                        'channelTitle': 'Tech Channel',
                        'publishedAt': '2024-01-05T10:00:00Z',
                        'thumbnails': {'default': {'url': 'http://example.com/thumb.jpg'}}
                    }
                },
                {
                    'id': {'videoId': 'def456'},
                    'snippet': {
                        'title': 'Advanced Python',
                        'description': 'Advanced concepts',
                        'channelId': 'channel_2',
                        'channelTitle': 'Code Academy',
                        'publishedAt': '2024-01-06T15:30:00Z',
                        'thumbnails': {}
                    }
                }
            ]
        }

        mock_service.search.return_value = mock_search
        mock_search.list.return_value = mock_request
        mock_request.execute.return_value = mock_response
        mock_build.return_value = mock_service

        client = YouTubeAPIClient(api_key="test_key")

        videos = client.search_videos(
            query="python",
            published_after="2024-01-01T00:00:00Z",
            published_before="2024-01-08T00:00:00Z"
        )

        assert len(videos) == 2

        # Check first video
        assert videos[0]['video_id'] == 'abc123'
        assert videos[0]['title'] == 'Python Tutorial'
        assert videos[0]['description'] == 'Learn Python basics'
        assert videos[0]['channel_id'] == 'channel_1'
        assert videos[0]['channel_title'] == 'Tech Channel'
        assert videos[0]['published_at'] == '2024-01-05T10:00:00Z'
        assert 'thumbnails' in videos[0]

        # Check second video
        assert videos[1]['video_id'] == 'def456'
        assert videos[1]['title'] == 'Advanced Python'

    @patch('research_agent.api_client.build')
    def test_search_videos_consumes_quota_after_success(self, mock_build):
        """Test that search consumes 100 quota units after successful request."""
        mock_service = MagicMock()
        mock_search = MagicMock()
        mock_list = MagicMock()
        mock_request = MagicMock()

        mock_service.search.return_value = mock_search
        mock_search.list.return_value = mock_request
        mock_request.execute.return_value = {'items': []}
        mock_build.return_value = mock_service

        rate_limiter = APIRateLimiter(daily_quota=10000)
        initial_consumed = rate_limiter.consumed

        client = YouTubeAPIClient(api_key="test_key", rate_limiter=rate_limiter)

        client.search_videos(
            query="test",
            published_after="2024-01-01T00:00:00Z",
            published_before="2024-01-08T00:00:00Z"
        )

        # Verify 100 units were consumed
        assert rate_limiter.consumed == initial_consumed + 100

    @patch('research_agent.api_client.build')
    def test_search_videos_handles_403_quota_error(self, mock_build):
        """Test that search raises QuotaExceededError on 403 quota error."""
        from googleapiclient.errors import HttpError
        from research_agent.exceptions import QuotaExceededError

        mock_service = MagicMock()
        mock_search = MagicMock()
        mock_list = MagicMock()
        mock_request = MagicMock()

        # Create mock 403 error response
        mock_resp = MagicMock()
        mock_resp.status = 403
        error_content = b'{"error": {"message": "quota exceeded"}}'
        http_error = HttpError(mock_resp, error_content)

        mock_service.search.return_value = mock_search
        mock_search.list.return_value = mock_request
        mock_request.execute.side_effect = http_error
        mock_build.return_value = mock_service

        client = YouTubeAPIClient(api_key="test_key")

        with pytest.raises(QuotaExceededError):
            client.search_videos(
                query="test",
                published_after="2024-01-01T00:00:00Z",
                published_before="2024-01-08T00:00:00Z"
            )

    @patch('research_agent.api_client.build')
    def test_search_videos_handles_network_timeout(self, mock_build):
        """Test that search raises NetworkError on socket timeout."""
        import socket
        from research_agent.exceptions import NetworkError

        mock_service = MagicMock()
        mock_search = MagicMock()
        mock_list = MagicMock()
        mock_request = MagicMock()

        mock_service.search.return_value = mock_search
        mock_search.list.return_value = mock_request
        mock_request.execute.side_effect = socket.timeout()
        mock_build.return_value = mock_service

        client = YouTubeAPIClient(api_key="test_key")

        with pytest.raises(NetworkError, match="Network timeout"):
            client.search_videos(
                query="test",
                published_after="2024-01-01T00:00:00Z",
                published_before="2024-01-08T00:00:00Z"
            )

    @patch('research_agent.api_client.build')
    def test_search_videos_handles_network_error(self, mock_build):
        """Test that search raises NetworkError on socket error."""
        import socket
        from research_agent.exceptions import NetworkError

        mock_service = MagicMock()
        mock_search = MagicMock()
        mock_list = MagicMock()
        mock_request = MagicMock()

        mock_service.search.return_value = mock_search
        mock_search.list.return_value = mock_request
        mock_request.execute.side_effect = socket.error("Connection refused")
        mock_build.return_value = mock_service

        client = YouTubeAPIClient(api_key="test_key")

        with pytest.raises(NetworkError, match="Network connectivity lost"):
            client.search_videos(
                query="test",
                published_after="2024-01-01T00:00:00Z",
                published_before="2024-01-08T00:00:00Z"
            )

    @patch('research_agent.api_client.build')
    def test_search_videos_handles_parse_error(self, mock_build):
        """Test that search raises ParseError when response parsing fails."""
        from research_agent.exceptions import ParseError

        mock_service = MagicMock()
        mock_search = MagicMock()
        mock_list = MagicMock()
        mock_request = MagicMock()

        # Return malformed response (missing required fields)
        mock_response = {
            'items': [
                {
                    'id': {},  # Missing videoId
                    'snippet': {}  # Missing required fields
                }
            ]
        }

        mock_service.search.return_value = mock_search
        mock_search.list.return_value = mock_request
        mock_request.execute.return_value = mock_response
        mock_build.return_value = mock_service

        client = YouTubeAPIClient(api_key="test_key")

        with pytest.raises(ParseError):
            client.search_videos(
                query="test",
                published_after="2024-01-01T00:00:00Z",
                published_before="2024-01-08T00:00:00Z"
            )

    @patch('research_agent.api_client.build')
    def test_search_videos_returns_empty_list_for_no_results(self, mock_build):
        """Test that search returns empty list when no videos found."""
        mock_service = MagicMock()
        mock_search = MagicMock()
        mock_list = MagicMock()
        mock_request = MagicMock()

        mock_service.search.return_value = mock_search
        mock_search.list.return_value = mock_request
        mock_request.execute.return_value = {'items': []}
        mock_build.return_value = mock_service

        client = YouTubeAPIClient(api_key="test_key")

        videos = client.search_videos(
            query="nonexistent_query_xyz",
            published_after="2024-01-01T00:00:00Z",
            published_before="2024-01-08T00:00:00Z"
        )

        assert videos == []

    @patch('research_agent.api_client.build')
    def test_search_videos_default_max_results(self, mock_build):
        """Test that search uses default max_results of 50."""
        mock_service = MagicMock()
        mock_search = MagicMock()
        mock_list = MagicMock()
        mock_request = MagicMock()

        mock_service.search.return_value = mock_search
        mock_search.list.return_value = mock_request
        mock_request.execute.return_value = {'items': []}
        mock_build.return_value = mock_service

        client = YouTubeAPIClient(api_key="test_key")

        client.search_videos(
            query="test",
            published_after="2024-01-01T00:00:00Z",
            published_before="2024-01-08T00:00:00Z"
        )

        # Verify maxResults=50 was used
        call_kwargs = mock_search.list.call_args[1]
        assert call_kwargs['maxResults'] == 50



class TestYouTubeAPIClientGetVideoDetails:
    """Test YouTubeAPIClient.get_video_details method."""

    @patch('research_agent.api_client.build')
    def test_get_video_details_empty_list(self, mock_build):
        """Test that get_video_details returns empty list for empty input."""
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        client = YouTubeAPIClient(api_key="test_key")
        
        result = client.get_video_details([])
        
        assert result == []

    @patch('research_agent.api_client.build')
    def test_get_video_details_pre_flight_quota_check(self, mock_build):
        """Test that get_video_details performs pre-flight quota check (1 unit per video)."""
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        # Create rate limiter with insufficient quota
        rate_limiter = APIRateLimiter(daily_quota=10000)
        rate_limiter.consumed = 9995  # Only 5 units remaining, need 10

        client = YouTubeAPIClient(api_key="test_key", rate_limiter=rate_limiter)

        from research_agent.exceptions import QuotaExceededError
        with pytest.raises(QuotaExceededError):
            client.get_video_details(['vid1', 'vid2', 'vid3', 'vid4', 'vid5', 
                                     'vid6', 'vid7', 'vid8', 'vid9', 'vid10'])

    @patch('research_agent.api_client.build')
    def test_get_video_details_single_video(self, mock_build):
        """Test fetching details for a single video."""
        mock_service = MagicMock()
        mock_videos = MagicMock()
        mock_list = MagicMock()
        mock_request = MagicMock()

        # Mock API response
        mock_response = {
            'items': [
                {
                    'id': 'abc123',
                    'snippet': {
                        'title': 'Python Tutorial',
                        'description': 'Learn Python basics',
                        'channelTitle': 'Tech Channel',
                        'publishedAt': '2024-01-05T10:00:00Z'
                    },
                    'statistics': {
                        'viewCount': '10000',
                        'likeCount': '500',
                        'commentCount': '50'
                    }
                }
            ]
        }

        mock_service.videos.return_value = mock_videos
        mock_videos.list.return_value = mock_request
        mock_request.execute.return_value = mock_response
        mock_build.return_value = mock_service

        client = YouTubeAPIClient(api_key="test_key")

        result = client.get_video_details(['abc123'])

        assert len(result) == 1
        assert result[0]['video_id'] == 'abc123'
        assert result[0]['title'] == 'Python Tutorial'
        assert result[0]['description'] == 'Learn Python basics'
        assert result[0]['channel_title'] == 'Tech Channel'
        assert result[0]['published_at'] == '2024-01-05T10:00:00Z'
        assert result[0]['view_count'] == 10000
        assert result[0]['like_count'] == 500
        assert result[0]['comment_count'] == 50

    @patch('research_agent.api_client.build')
    def test_get_video_details_multiple_videos(self, mock_build):
        """Test fetching details for multiple videos."""
        mock_service = MagicMock()
        mock_videos = MagicMock()
        mock_list = MagicMock()
        mock_request = MagicMock()

        # Mock API response with multiple videos
        mock_response = {
            'items': [
                {
                    'id': 'vid1',
                    'snippet': {
                        'title': 'Video 1',
                        'description': 'Description 1',
                        'channelTitle': 'Channel 1',
                        'publishedAt': '2024-01-01T10:00:00Z'
                    },
                    'statistics': {
                        'viewCount': '1000',
                        'likeCount': '100',
                        'commentCount': '10'
                    }
                },
                {
                    'id': 'vid2',
                    'snippet': {
                        'title': 'Video 2',
                        'description': 'Description 2',
                        'channelTitle': 'Channel 2',
                        'publishedAt': '2024-01-02T10:00:00Z'
                    },
                    'statistics': {
                        'viewCount': '2000',
                        'likeCount': '200',
                        'commentCount': '20'
                    }
                }
            ]
        }

        mock_service.videos.return_value = mock_videos
        mock_videos.list.return_value = mock_request
        mock_request.execute.return_value = mock_response
        mock_build.return_value = mock_service

        client = YouTubeAPIClient(api_key="test_key")

        result = client.get_video_details(['vid1', 'vid2'])

        assert len(result) == 2
        assert result[0]['video_id'] == 'vid1'
        assert result[0]['view_count'] == 1000
        assert result[1]['video_id'] == 'vid2'
        assert result[1]['view_count'] == 2000

    @patch('research_agent.api_client.build')
    def test_get_video_details_batching_50_videos(self, mock_build):
        """Test that video IDs are batched into groups of 50 (API limit)."""
        mock_service = MagicMock()
        mock_videos = MagicMock()
        mock_list = MagicMock()
        mock_request = MagicMock()

        # Mock API response
        mock_response = {'items': []}

        mock_service.videos.return_value = mock_videos
        mock_videos.list.return_value = mock_request
        mock_request.execute.return_value = mock_response
        mock_build.return_value = mock_service

        client = YouTubeAPIClient(api_key="test_key")

        # Create 75 video IDs (should result in 2 batches: 50 + 25)
        video_ids = [f'vid{i}' for i in range(75)]
        
        client.get_video_details(video_ids)

        # Verify videos().list() was called twice (2 batches)
        assert mock_videos.list.call_count == 2

        # Check first batch has 50 IDs
        first_call_ids = mock_videos.list.call_args_list[0][1]['id']
        assert len(first_call_ids.split(',')) == 50

        # Check second batch has 25 IDs
        second_call_ids = mock_videos.list.call_args_list[1][1]['id']
        assert len(second_call_ids.split(',')) == 25

    @patch('research_agent.api_client.build')
    def test_get_video_details_batching_exactly_50_videos(self, mock_build):
        """Test batching with exactly 50 videos (edge case)."""
        mock_service = MagicMock()
        mock_videos = MagicMock()
        mock_list = MagicMock()
        mock_request = MagicMock()

        mock_response = {'items': []}

        mock_service.videos.return_value = mock_videos
        mock_videos.list.return_value = mock_request
        mock_request.execute.return_value = mock_response
        mock_build.return_value = mock_service

        client = YouTubeAPIClient(api_key="test_key")

        # Create exactly 50 video IDs (should result in 1 batch)
        video_ids = [f'vid{i}' for i in range(50)]
        
        client.get_video_details(video_ids)

        # Verify videos().list() was called once
        assert mock_videos.list.call_count == 1

    @patch('research_agent.api_client.build')
    def test_get_video_details_batching_51_videos(self, mock_build):
        """Test batching with 51 videos (just over limit)."""
        mock_service = MagicMock()
        mock_videos = MagicMock()
        mock_list = MagicMock()
        mock_request = MagicMock()

        mock_response = {'items': []}

        mock_service.videos.return_value = mock_videos
        mock_videos.list.return_value = mock_request
        mock_request.execute.return_value = mock_response
        mock_build.return_value = mock_service

        client = YouTubeAPIClient(api_key="test_key")

        # Create 51 video IDs (should result in 2 batches: 50 + 1)
        video_ids = [f'vid{i}' for i in range(51)]
        
        client.get_video_details(video_ids)

        # Verify videos().list() was called twice
        assert mock_videos.list.call_count == 2

        # Check second batch has 1 ID
        second_call_ids = mock_videos.list.call_args_list[1][1]['id']
        assert len(second_call_ids.split(',')) == 1

    @patch('research_agent.api_client.build')
    def test_get_video_details_builds_correct_request(self, mock_build):
        """Test that get_video_details builds YouTube API request with correct parameters."""
        mock_service = MagicMock()
        mock_videos = MagicMock()
        mock_list = MagicMock()
        mock_request = MagicMock()

        mock_response = {'items': []}

        mock_service.videos.return_value = mock_videos
        mock_videos.list.return_value = mock_request
        mock_request.execute.return_value = mock_response
        mock_build.return_value = mock_service

        client = YouTubeAPIClient(api_key="test_key")

        client.get_video_details(['vid1', 'vid2', 'vid3'])

        # Verify videos().list() was called with correct parameters
        mock_videos.list.assert_called_once_with(
            part='snippet,statistics',
            id='vid1,vid2,vid3'
        )

    @patch('research_agent.api_client.build')
    def test_get_video_details_consumes_quota_after_success(self, mock_build):
        """Test that get_video_details consumes 1 quota unit per video after successful request."""
        mock_service = MagicMock()
        mock_videos = MagicMock()
        mock_list = MagicMock()
        mock_request = MagicMock()

        mock_response = {'items': []}

        mock_service.videos.return_value = mock_videos
        mock_videos.list.return_value = mock_request
        mock_request.execute.return_value = mock_response
        mock_build.return_value = mock_service

        rate_limiter = APIRateLimiter(daily_quota=10000)
        initial_consumed = rate_limiter.consumed

        client = YouTubeAPIClient(api_key="test_key", rate_limiter=rate_limiter)

        # Fetch details for 5 videos
        client.get_video_details(['vid1', 'vid2', 'vid3', 'vid4', 'vid5'])

        # Verify 5 units were consumed (1 per video)
        assert rate_limiter.consumed == initial_consumed + 5

    @patch('research_agent.api_client.build')
    def test_get_video_details_handles_missing_statistics(self, mock_build):
        """Test that get_video_details handles missing statistics gracefully (defaults to 0)."""
        mock_service = MagicMock()
        mock_videos = MagicMock()
        mock_list = MagicMock()
        mock_request = MagicMock()

        # Mock API response with missing statistics
        mock_response = {
            'items': [
                {
                    'id': 'vid1',
                    'snippet': {
                        'title': 'Video 1',
                        'description': 'Description 1',
                        'channelTitle': 'Channel 1',
                        'publishedAt': '2024-01-01T10:00:00Z'
                    },
                    'statistics': {
                        'viewCount': '1000'
                        # likeCount and commentCount missing
                    }
                }
            ]
        }

        mock_service.videos.return_value = mock_videos
        mock_videos.list.return_value = mock_request
        mock_request.execute.return_value = mock_response
        mock_build.return_value = mock_service

        client = YouTubeAPIClient(api_key="test_key")

        result = client.get_video_details(['vid1'])

        assert len(result) == 1
        assert result[0]['view_count'] == 1000
        assert result[0]['like_count'] == 0  # Default value
        assert result[0]['comment_count'] == 0  # Default value

    @patch('research_agent.api_client.build')
    def test_get_video_details_handles_403_quota_error(self, mock_build):
        """Test that get_video_details raises QuotaExceededError on 403 quota error."""
        from googleapiclient.errors import HttpError
        from research_agent.exceptions import QuotaExceededError

        mock_service = MagicMock()
        mock_videos = MagicMock()
        mock_list = MagicMock()
        mock_request = MagicMock()

        # Create mock 403 error response
        mock_resp = MagicMock()
        mock_resp.status = 403
        error_content = b'{"error": {"message": "quota exceeded"}}'
        http_error = HttpError(mock_resp, error_content)

        mock_service.videos.return_value = mock_videos
        mock_videos.list.return_value = mock_request
        mock_request.execute.side_effect = http_error
        mock_build.return_value = mock_service

        client = YouTubeAPIClient(api_key="test_key")

        with pytest.raises(QuotaExceededError):
            client.get_video_details(['vid1'])

    @patch('research_agent.api_client.build')
    def test_get_video_details_handles_network_timeout(self, mock_build):
        """Test that get_video_details raises NetworkError on socket timeout."""
        import socket
        from research_agent.exceptions import NetworkError

        mock_service = MagicMock()
        mock_videos = MagicMock()
        mock_list = MagicMock()
        mock_request = MagicMock()

        mock_service.videos.return_value = mock_videos
        mock_videos.list.return_value = mock_request
        mock_request.execute.side_effect = socket.timeout()
        mock_build.return_value = mock_service

        client = YouTubeAPIClient(api_key="test_key")

        with pytest.raises(NetworkError, match="Network timeout"):
            client.get_video_details(['vid1'])

    @patch('research_agent.api_client.build')
    def test_get_video_details_handles_network_error(self, mock_build):
        """Test that get_video_details raises NetworkError on socket error."""
        import socket
        from research_agent.exceptions import NetworkError

        mock_service = MagicMock()
        mock_videos = MagicMock()
        mock_list = MagicMock()
        mock_request = MagicMock()

        mock_service.videos.return_value = mock_videos
        mock_videos.list.return_value = mock_request
        mock_request.execute.side_effect = socket.error("Connection refused")
        mock_build.return_value = mock_service

        client = YouTubeAPIClient(api_key="test_key")

        with pytest.raises(NetworkError, match="Network connectivity lost"):
            client.get_video_details(['vid1'])

    @patch('research_agent.api_client.build')
    def test_get_video_details_handles_parse_error(self, mock_build):
        """Test that get_video_details raises ParseError when response parsing fails."""
        from research_agent.exceptions import ParseError

        mock_service = MagicMock()
        mock_videos = MagicMock()
        mock_list = MagicMock()
        mock_request = MagicMock()

        # Return malformed response (missing required fields)
        mock_response = {
            'items': [
                {
                    'id': 'vid1',
                    'snippet': {},  # Missing required fields
                    'statistics': {}
                }
            ]
        }

        mock_service.videos.return_value = mock_videos
        mock_videos.list.return_value = mock_request
        mock_request.execute.return_value = mock_response
        mock_build.return_value = mock_service

        client = YouTubeAPIClient(api_key="test_key")

        with pytest.raises(ParseError):
            client.get_video_details(['vid1'])



class TestYouTubeAPIClientRetryLogic:
    """Test retry logic with exponential backoff for 5xx server errors."""

    @patch('research_agent.api_client.build')
    @patch('research_agent.api_client.time.sleep')
    def test_search_videos_retries_on_500_error(self, mock_sleep, mock_build):
        """Test that search_videos retries up to 3 times on 5xx server errors."""
        from googleapiclient.errors import HttpError
        from research_agent.exceptions import NetworkError

        mock_service = MagicMock()
        mock_search = MagicMock()
        mock_list = MagicMock()
        mock_request = MagicMock()

        # Create mock 500 error response
        mock_resp = MagicMock()
        mock_resp.status = 500
        error_content = b'{"error": {"message": "Internal server error"}}'
        http_error = HttpError(mock_resp, error_content)

        mock_service.search.return_value = mock_search
        mock_search.list.return_value = mock_request
        # Fail all attempts with 500 error
        mock_request.execute.side_effect = http_error
        mock_build.return_value = mock_service

        client = YouTubeAPIClient(api_key="test_key")

        with pytest.raises(NetworkError, match="failed after 3 retries"):
            client.search_videos(
                query="test",
                published_after="2024-01-01T00:00:00Z",
                published_before="2024-01-08T00:00:00Z"
            )

        # Verify execute was called 4 times (1 initial + 3 retries)
        assert mock_request.execute.call_count == 4

        # Verify sleep was called 3 times with correct delays (1s, 2s, 4s)
        assert mock_sleep.call_count == 3
        assert mock_sleep.call_args_list[0][0][0] == 1
        assert mock_sleep.call_args_list[1][0][0] == 2
        assert mock_sleep.call_args_list[2][0][0] == 4

    @patch('research_agent.api_client.build')
    @patch('research_agent.api_client.time.sleep')
    def test_search_videos_succeeds_on_second_attempt(self, mock_sleep, mock_build):
        """Test that search_videos succeeds if retry succeeds."""
        from googleapiclient.errors import HttpError

        mock_service = MagicMock()
        mock_search = MagicMock()
        mock_list = MagicMock()
        mock_request = MagicMock()

        # Create mock 503 error response
        mock_resp = MagicMock()
        mock_resp.status = 503
        error_content = b'{"error": {"message": "Service unavailable"}}'
        http_error = HttpError(mock_resp, error_content)

        mock_service.search.return_value = mock_search
        mock_search.list.return_value = mock_request
        # Fail first attempt, succeed on second
        mock_request.execute.side_effect = [
            http_error,
            {'items': []}
        ]
        mock_build.return_value = mock_service

        client = YouTubeAPIClient(api_key="test_key")

        result = client.search_videos(
            query="test",
            published_after="2024-01-01T00:00:00Z",
            published_before="2024-01-08T00:00:00Z"
        )

        # Verify execute was called twice (1 initial + 1 retry)
        assert mock_request.execute.call_count == 2

        # Verify sleep was called once with 1 second delay
        assert mock_sleep.call_count == 1
        assert mock_sleep.call_args_list[0][0][0] == 1

        # Verify result is returned
        assert result == []

    @patch('research_agent.api_client.build')
    @patch('research_agent.api_client.time.sleep')
    def test_search_videos_no_retry_on_400_error(self, mock_sleep, mock_build):
        """Test that search_videos does NOT retry on 4xx client errors."""
        from googleapiclient.errors import HttpError
        from research_agent.exceptions import NetworkError

        mock_service = MagicMock()
        mock_search = MagicMock()
        mock_list = MagicMock()
        mock_request = MagicMock()

        # Create mock 400 error response
        mock_resp = MagicMock()
        mock_resp.status = 400
        error_content = b'{"error": {"message": "Bad request"}}'
        http_error = HttpError(mock_resp, error_content)

        mock_service.search.return_value = mock_search
        mock_search.list.return_value = mock_request
        mock_request.execute.side_effect = http_error
        mock_build.return_value = mock_service

        client = YouTubeAPIClient(api_key="test_key")

        with pytest.raises(NetworkError, match="YouTube API request failed"):
            client.search_videos(
                query="test",
                published_after="2024-01-01T00:00:00Z",
                published_before="2024-01-08T00:00:00Z"
            )

        # Verify execute was called only once (no retries)
        assert mock_request.execute.call_count == 1

        # Verify sleep was never called
        assert mock_sleep.call_count == 0

    @patch('research_agent.api_client.build')
    @patch('research_agent.api_client.time.sleep')
    def test_get_video_details_retries_on_502_error(self, mock_sleep, mock_build):
        """Test that get_video_details retries up to 3 times on 5xx server errors."""
        from googleapiclient.errors import HttpError
        from research_agent.exceptions import NetworkError

        mock_service = MagicMock()
        mock_videos = MagicMock()
        mock_list = MagicMock()
        mock_request = MagicMock()

        # Create mock 502 error response
        mock_resp = MagicMock()
        mock_resp.status = 502
        error_content = b'{"error": {"message": "Bad gateway"}}'
        http_error = HttpError(mock_resp, error_content)

        mock_service.videos.return_value = mock_videos
        mock_videos.list.return_value = mock_request
        # Fail all attempts with 502 error
        mock_request.execute.side_effect = http_error
        mock_build.return_value = mock_service

        client = YouTubeAPIClient(api_key="test_key")

        with pytest.raises(NetworkError, match="failed after 3 retries"):
            client.get_video_details(['vid1', 'vid2'])

        # Verify execute was called 4 times (1 initial + 3 retries)
        assert mock_request.execute.call_count == 4

        # Verify sleep was called 3 times with correct delays (1s, 2s, 4s)
        assert mock_sleep.call_count == 3
        assert mock_sleep.call_args_list[0][0][0] == 1
        assert mock_sleep.call_args_list[1][0][0] == 2
        assert mock_sleep.call_args_list[2][0][0] == 4

    @patch('research_agent.api_client.build')
    @patch('research_agent.api_client.time.sleep')
    def test_get_video_details_succeeds_on_third_attempt(self, mock_sleep, mock_build):
        """Test that get_video_details succeeds if third retry succeeds."""
        from googleapiclient.errors import HttpError

        mock_service = MagicMock()
        mock_videos = MagicMock()
        mock_list = MagicMock()
        mock_request = MagicMock()

        # Create mock 500 error response
        mock_resp = MagicMock()
        mock_resp.status = 500
        error_content = b'{"error": {"message": "Internal server error"}}'
        http_error = HttpError(mock_resp, error_content)

        mock_service.videos.return_value = mock_videos
        mock_videos.list.return_value = mock_request
        # Fail first two attempts, succeed on third
        mock_request.execute.side_effect = [
            http_error,
            http_error,
            {'items': [
                {
                    'id': 'vid1',
                    'snippet': {
                        'title': 'Test Video',
                        'description': 'Test Description',
                        'channelTitle': 'Test Channel',
                        'publishedAt': '2024-01-01T10:00:00Z'
                    },
                    'statistics': {
                        'viewCount': '1000',
                        'likeCount': '100',
                        'commentCount': '10'
                    }
                }
            ]}
        ]
        mock_build.return_value = mock_service

        client = YouTubeAPIClient(api_key="test_key")

        result = client.get_video_details(['vid1'])

        # Verify execute was called 3 times (1 initial + 2 retries)
        assert mock_request.execute.call_count == 3

        # Verify sleep was called twice with correct delays (1s, 2s)
        assert mock_sleep.call_count == 2
        assert mock_sleep.call_args_list[0][0][0] == 1
        assert mock_sleep.call_args_list[1][0][0] == 2

        # Verify result is returned
        assert len(result) == 1
        assert result[0]['video_id'] == 'vid1'

    @patch('research_agent.api_client.build')
    @patch('research_agent.api_client.time.sleep')
    def test_retry_logs_each_attempt(self, mock_sleep, mock_build):
        """Test that retry logic logs each retry attempt with context."""
        from googleapiclient.errors import HttpError
        from research_agent.exceptions import NetworkError

        mock_service = MagicMock()
        mock_search = MagicMock()
        mock_list = MagicMock()
        mock_request = MagicMock()

        # Create mock 500 error response
        mock_resp = MagicMock()
        mock_resp.status = 500
        error_content = b'{"error": {"message": "Internal server error"}}'
        http_error = HttpError(mock_resp, error_content)

        mock_service.search.return_value = mock_search
        mock_search.list.return_value = mock_request
        mock_request.execute.side_effect = http_error
        mock_build.return_value = mock_service

        client = YouTubeAPIClient(api_key="test_key")

        # Capture log messages
        with patch('research_agent.api_client.logger') as mock_logger:
            with pytest.raises(NetworkError):
                client.search_videos(
                    query="test",
                    published_after="2024-01-01T00:00:00Z",
                    published_before="2024-01-08T00:00:00Z"
                )

            # Verify warning logs for each retry attempt
            warning_calls = [call for call in mock_logger.warning.call_args_list]
            assert len(warning_calls) == 3

            # Check that each warning contains retry information
            for i, call in enumerate(warning_calls):
                log_message = call[0][0]
                assert "500 error" in log_message
                assert f"retrying in {[1, 2, 4][i]}s" in log_message
                assert f"attempt {i + 1}/3" in log_message

            # Verify error log after all retries exhausted
            error_calls = [call for call in mock_logger.error.call_args_list]
            assert len(error_calls) >= 1
            final_error = error_calls[-1][0][0]
            assert "failed after 3 retries" in final_error

    @patch('research_agent.api_client.build')
    @patch('research_agent.api_client.time.sleep')
    def test_retry_on_all_5xx_status_codes(self, mock_sleep, mock_build):
        """Test that retry logic works for all 5xx status codes (500-599)."""
        from googleapiclient.errors import HttpError
        from research_agent.exceptions import NetworkError

        for status_code in [500, 501, 502, 503, 504, 505, 599]:
            mock_service = MagicMock()
            mock_search = MagicMock()
            mock_list = MagicMock()
            mock_request = MagicMock()

            # Create mock error response with specific status code
            mock_resp = MagicMock()
            mock_resp.status = status_code
            error_content = f'{{"error": {{"message": "Server error {status_code}"}}}}'.encode()
            http_error = HttpError(mock_resp, error_content)

            mock_service.search.return_value = mock_search
            mock_search.list.return_value = mock_request
            mock_request.execute.side_effect = http_error
            mock_build.return_value = mock_service

            client = YouTubeAPIClient(api_key="test_key")

            with pytest.raises(NetworkError, match="failed after 3 retries"):
                client.search_videos(
                    query="test",
                    published_after="2024-01-01T00:00:00Z",
                    published_before="2024-01-08T00:00:00Z"
                )

            # Verify execute was called 4 times (1 initial + 3 retries)
            assert mock_request.execute.call_count == 4

            # Reset mocks for next iteration
            mock_sleep.reset_mock()
            mock_build.reset_mock()

    @patch('research_agent.api_client.build')
    @patch('socket.setdefaulttimeout')
    def test_30_second_timeout_set_for_search(self, mock_set_timeout, mock_build):
        """Test that 30-second timeout is set for search_videos requests."""
        mock_service = MagicMock()
        mock_search = MagicMock()
        mock_list = MagicMock()
        mock_request = MagicMock()

        mock_service.search.return_value = mock_search
        mock_search.list.return_value = mock_request
        mock_request.execute.return_value = {'items': []}
        mock_build.return_value = mock_service

        client = YouTubeAPIClient(api_key="test_key")

        client.search_videos(
            query="test",
            published_after="2024-01-01T00:00:00Z",
            published_before="2024-01-08T00:00:00Z"
        )

        # Verify timeout was set to 30 seconds
        timeout_calls = [call for call in mock_set_timeout.call_args_list if call[0][0] == 30]
        assert len(timeout_calls) >= 1

    @patch('research_agent.api_client.build')
    @patch('socket.setdefaulttimeout')
    def test_30_second_timeout_set_for_get_video_details(self, mock_set_timeout, mock_build):
        """Test that 30-second timeout is set for get_video_details requests."""
        mock_service = MagicMock()
        mock_videos = MagicMock()
        mock_list = MagicMock()
        mock_request = MagicMock()

        mock_service.videos.return_value = mock_videos
        mock_videos.list.return_value = mock_request
        mock_request.execute.return_value = {'items': []}
        mock_build.return_value = mock_service

        client = YouTubeAPIClient(api_key="test_key")

        client.get_video_details(['vid1'])

        # Verify timeout was set to 30 seconds
        timeout_calls = [call for call in mock_set_timeout.call_args_list if call[0][0] == 30]
        assert len(timeout_calls) >= 1
