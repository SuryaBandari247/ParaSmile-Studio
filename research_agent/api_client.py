"""
YouTube API Client for Research Agent.

This module provides the YouTubeAPIClient class that interfaces with
YouTube Data API v3 for video search and data retrieval. It handles
authentication, request building, and integrates with the rate limiter
for quota management.
"""

import logging
import os
import time
from functools import wraps
from typing import Optional, Callable, Any

from dotenv import load_dotenv
from googleapiclient.discovery import build

from research_agent.exceptions import AuthenticationError, NetworkError
from research_agent.rate_limiter import APIRateLimiter


logger = logging.getLogger(__name__)


def retry_on_server_error(max_retries: int = 3, delays: tuple = (1, 2, 4)):
    """
    Decorator to retry API calls on 5xx server errors with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        delays: Tuple of delay times in seconds for each retry (default: (1, 2, 4))
    
    Raises:
        NetworkError: After all retries are exhausted
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            from googleapiclient.errors import HttpError
            
            last_exception = None
            
            for attempt in range(max_retries + 1):  # +1 for initial attempt
                try:
                    # Set 30-second timeout for the request
                    # Note: googleapiclient uses httplib2 which doesn't support per-request timeout
                    # The timeout is handled at the socket level in the calling methods
                    return func(*args, **kwargs)
                    
                except HttpError as e:
                    # Check if it's a 5xx server error
                    if e.resp.status >= 500 and e.resp.status < 600:
                        last_exception = e
                        
                        # If we've exhausted all retries, raise NetworkError
                        if attempt >= max_retries:
                            logger.error(
                                f"API request failed after {max_retries} retries: {func.__name__}, "
                                f"status={e.resp.status}, error={str(e)}"
                            )
                            raise NetworkError(
                                f"YouTube API request failed after {max_retries} retries: {str(e)}"
                            ) from e
                        
                        # Log retry attempt and wait before retrying
                        delay = delays[attempt] if attempt < len(delays) else delays[-1]
                        logger.warning(
                            f"API request failed with {e.resp.status} error, "
                            f"retrying in {delay}s (attempt {attempt + 1}/{max_retries}): "
                            f"{func.__name__}"
                        )
                        time.sleep(delay)
                    else:
                        # Not a 5xx error, re-raise immediately
                        raise
                        
            # This should never be reached, but just in case
            if last_exception:
                raise NetworkError(
                    f"YouTube API request failed after {max_retries} retries"
                ) from last_exception
                
        return wrapper
    return decorator


class YouTubeAPIClient:
    """
    Client for interacting with YouTube Data API v3.
    Handles authentication, request execution, and error handling.
    """
    
    def __init__(self, api_key: Optional[str] = None, rate_limiter: Optional[APIRateLimiter] = None):
        """
        Initialize YouTube API client.
        
        Args:
            api_key: YouTube Data API key. If None, loads from YOUTUBE_API_KEY environment variable.
            rate_limiter: Rate limiter instance for quota management. If None, creates a new instance.
            
        Raises:
            AuthenticationError: If API key is invalid or missing
        """
        # Load environment variables from .env file
        load_dotenv()
        
        # Get API key from parameter or environment
        self.api_key = api_key or os.getenv('YOUTUBE_API_KEY')
        
        # Validate API key
        if not self.api_key:
            logger.error("YouTube API key is missing")
            raise AuthenticationError("YouTube API key is required. Set YOUTUBE_API_KEY environment variable.")
        
        if not isinstance(self.api_key, str) or not self.api_key.strip():
            logger.error("YouTube API key is invalid (empty or non-string)")
            raise AuthenticationError("YouTube API key must be a non-empty string")
        
        # Store rate limiter reference
        self.rate_limiter = rate_limiter if rate_limiter is not None else APIRateLimiter()
        
        # Build YouTube API service
        try:
            self.youtube = build('youtube', 'v3', developerKey=self.api_key)
            logger.info("YouTube API client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize YouTube API client: {e}")
            raise AuthenticationError(f"Failed to authenticate with YouTube API: {str(e)}")
    
    @retry_on_server_error(max_retries=3, delays=(1, 2, 4))
    def search_videos(
        self,
        query: str,
        published_after: str = None,
        published_before: str = None,
        max_results: int = 50,
        channel_id: str = None,
        order: str = 'relevance'
    ) -> list:
        """
        Search for videos matching query within date range.

        Args:
            query: Search keywords
            published_after: Start date for video publication (RFC 3339 format: YYYY-MM-DDTHH:MM:SSZ)
            published_before: End date for video publication (RFC 3339 format: YYYY-MM-DDTHH:MM:SSZ)
            max_results: Maximum number of results to return (default: 50)
            channel_id: Optional channel ID to search within specific channel
            order: Sort order ('relevance', 'date', 'rating', 'viewCount')

        Returns:
            List of video metadata dictionaries

        Raises:
            QuotaExceededError: If API quota exhausted
            NetworkError: If network connectivity lost or 5xx errors after retries
            ParseError: If response parsing fails
        """
        from research_agent.exceptions import QuotaExceededError, NetworkError, ParseError
        from googleapiclient.errors import HttpError
        import socket

        # Pre-flight quota check (search costs 100 units)
        search_cost = 100
        if not self.rate_limiter.check_quota(search_cost):
            logger.error(f"Insufficient quota for search operation (requires {search_cost} units)")
            raise QuotaExceededError(self.rate_limiter.reset_at)

        logger.info(
            f"Executing search: query='{query}', published_after={published_after}, "
            f"published_before={published_before}, max_results={max_results}, "
            f"channel_id={channel_id}, order={order}"
        )

        try:
            # Set socket timeout to 30 seconds
            original_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(30)
            
            try:
                # Build YouTube API search request with date filters
                search_params = {
                    'part': 'snippet',
                    'type': 'video',
                    'maxResults': max_results,
                    'order': order
                }
                
                # Add optional parameters
                if query:
                    search_params['q'] = query
                if published_after:
                    search_params['publishedAfter'] = published_after
                if published_before:
                    search_params['publishedBefore'] = published_before
                if channel_id:
                    search_params['channelId'] = channel_id
                
                request = self.youtube.search().list(**search_params)

                # Execute the request
                response = request.execute()
            finally:
                # Restore original timeout
                socket.setdefaulttimeout(original_timeout)

            # Consume quota after successful request
            self.rate_limiter.consume_quota(search_cost)

            # Parse response into list of video metadata dictionaries
            videos = []
            for item in response.get('items', []):
                video_metadata = {
                    'video_id': item['id']['videoId'],
                    'title': item['snippet']['title'],
                    'description': item['snippet']['description'],
                    'channel_id': item['snippet']['channelId'],
                    'channel_title': item['snippet']['channelTitle'],
                    'published_at': item['snippet']['publishedAt'],
                    'thumbnails': item['snippet'].get('thumbnails', {})
                }
                videos.append(video_metadata)

            logger.info(f"Search completed successfully: {len(videos)} videos found")
            return videos

        except HttpError as e:
            # Handle 403 quota errors
            if e.resp.status == 403:
                error_content = e.content.decode('utf-8') if isinstance(e.content, bytes) else str(e.content)
                if 'quota' in error_content.lower():
                    logger.error(f"YouTube API quota exceeded: {error_content}")
                    raise QuotaExceededError(self.rate_limiter.reset_at)

            # 5xx errors are handled by the retry decorator
            # Other HTTP errors are raised as NetworkError
            if e.resp.status < 500 or e.resp.status >= 600:
                logger.error(f"YouTube API HTTP error: {e}")
                raise NetworkError(f"YouTube API request failed: {str(e)}")
            else:
                # Re-raise 5xx errors for retry decorator to handle
                raise

        except socket.timeout:
            logger.error("Network timeout during YouTube API request (30 seconds)")
            raise NetworkError("Network timeout: request took longer than 30 seconds")

        except socket.error as e:
            logger.error(f"Network error during YouTube API request: {e}")
            raise NetworkError(f"Network connectivity lost: {str(e)}")

        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Failed to parse YouTube API response: {e}")
            raise ParseError(str(response) if 'response' in locals() else "Unknown response")

    @retry_on_server_error(max_retries=3, delays=(1, 2, 4))
    def get_video_details(self, video_ids: list) -> list:
        """
        Fetch detailed statistics for videos.

        Batches video IDs into groups of 50 (API limit) and performs
        pre-flight quota checks (1 unit per video).

        Args:
            video_ids: List of YouTube video IDs

        Returns:
            List of video detail dictionaries with statistics including:
            - video_id: YouTube video ID
            - view_count: Number of views
            - like_count: Number of likes
            - comment_count: Number of comments
            - title: Video title
            - description: Video description
            - channel_title: Channel name
            - published_at: Publication timestamp

        Raises:
            QuotaExceededError: If API quota exhausted
            NetworkError: If network connectivity lost or 5xx errors after retries
            ParseError: If response parsing fails
        """
        from research_agent.exceptions import QuotaExceededError, NetworkError, ParseError
        from googleapiclient.errors import HttpError
        import socket

        if not video_ids:
            logger.info("No video IDs provided, returning empty list")
            return []

        # Pre-flight quota check (1 unit per video)
        total_cost = len(video_ids)
        if not self.rate_limiter.check_quota(total_cost):
            logger.error(f"Insufficient quota for video details operation (requires {total_cost} units)")
            raise QuotaExceededError(self.rate_limiter.reset_at)

        logger.info(f"Fetching details for {len(video_ids)} videos (quota cost: {total_cost} units)")

        all_video_details = []

        # Batch video IDs into groups of 50 (API limit)
        batch_size = 50
        for i in range(0, len(video_ids), batch_size):
            batch = video_ids[i:i + batch_size]
            batch_ids_str = ','.join(batch)

            logger.debug(f"Processing batch {i // batch_size + 1}: {len(batch)} videos")

            try:
                # Set socket timeout to 30 seconds
                original_timeout = socket.getdefaulttimeout()
                socket.setdefaulttimeout(30)
                
                try:
                    # Build YouTube API videos.list request
                    request = self.youtube.videos().list(
                        part='snippet,statistics',
                        id=batch_ids_str
                    )

                    # Execute the request
                    response = request.execute()
                finally:
                    # Restore original timeout
                    socket.setdefaulttimeout(original_timeout)

                # Parse response into list of video detail dictionaries
                for item in response.get('items', []):
                    video_details = {
                        'video_id': item['id'],
                        'title': item['snippet']['title'],
                        'description': item['snippet']['description'],
                        'channel_title': item['snippet']['channelTitle'],
                        'published_at': item['snippet']['publishedAt'],
                        'view_count': int(item['statistics'].get('viewCount', 0)),
                        'like_count': int(item['statistics'].get('likeCount', 0)),
                        'comment_count': int(item['statistics'].get('commentCount', 0))
                    }
                    all_video_details.append(video_details)

            except HttpError as e:
                # Handle 403 quota errors
                if e.resp.status == 403:
                    error_content = e.content.decode('utf-8') if isinstance(e.content, bytes) else str(e.content)
                    if 'quota' in error_content.lower():
                        logger.error(f"YouTube API quota exceeded: {error_content}")
                        raise QuotaExceededError(self.rate_limiter.reset_at)

                # 5xx errors are handled by the retry decorator
                # Other HTTP errors are raised as NetworkError
                if e.resp.status < 500 or e.resp.status >= 600:
                    logger.error(f"YouTube API HTTP error: {e}")
                    raise NetworkError(f"YouTube API request failed: {str(e)}")
                else:
                    # Re-raise 5xx errors for retry decorator to handle
                    raise

            except socket.timeout:
                logger.error("Network timeout during YouTube API request (30 seconds)")
                raise NetworkError("Network timeout: request took longer than 30 seconds")

            except socket.error as e:
                logger.error(f"Network error during YouTube API request: {e}")
                raise NetworkError(f"Network connectivity lost: {str(e)}")

            except (KeyError, ValueError, TypeError) as e:
                logger.error(f"Failed to parse YouTube API response: {e}")
                raise ParseError(str(response) if 'response' in locals() else "Unknown response")

        # Consume quota after all successful requests
        self.rate_limiter.consume_quota(total_cost)

        logger.info(f"Video details fetch completed successfully: {len(all_video_details)} videos processed")
        return all_video_details



