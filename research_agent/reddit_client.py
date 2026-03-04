"""
Reddit client for the Research Agent.

Fetches trending posts from public Reddit subreddits via the JSON API.
No API key required. Uses a descriptive User-Agent header and enforces
a 2-second minimum interval between HTTP requests per Reddit guidelines.
"""

import time
from typing import Any, Dict, List, Optional

import requests

from research_agent.logger import get_logger, log_error_with_context

logger = get_logger("reddit_client")


class RedditClient:
    """
    Fetches trending posts from public Reddit subreddits via JSON API.
    No API key required. Uses descriptive User-Agent header.
    """

    DEFAULT_SUBREDDITS: List[str] = [
        "worldnews",
        "economics",
        "technology",
        "science",
        "futurology",
        "geopolitics",
        "finance",
        "dataisbeautiful",
        "explainlikeimfive",
    ]

    _MIN_REQUEST_INTERVAL: float = 2.0  # seconds between HTTP requests

    def __init__(self, user_agent: str = "CalmCapitalist/1.0 (research-agent)"):
        """
        Initialize Reddit client with descriptive User-Agent.

        Args:
            user_agent: User-Agent header string for Reddit API compliance.
        """
        self.user_agent = user_agent
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": self.user_agent})
        self._last_request_time: float = 0.0

    def fetch_hot_posts(
        self,
        subreddits: Optional[List[str]] = None,
        limit: int = 25,
    ) -> List[Dict[str, Any]]:
        """
        Fetch hot posts from configured subreddits.

        Enforces 2-second minimum interval between requests.
        Skips private/unavailable subreddits with a warning.

        Args:
            subreddits: List of subreddit names (default: DEFAULT_SUBREDDITS).
            limit: Posts per subreddit (default: 25).

        Returns:
            List of dicts with keys: title, score, comment_count,
            subreddit, permalink, created_utc.
        """
        subs = subreddits if subreddits is not None else self.DEFAULT_SUBREDDITS
        all_posts: List[Dict[str, Any]] = []

        for sub in subs:
            try:
                posts = self._fetch_subreddit(sub, limit)
                all_posts.extend(posts)
            except Exception as exc:
                logger.warning(
                    "Skipping subreddit r/%s: %s", sub, exc,
                )
                log_error_with_context(
                    logger, exc, "_fetch_subreddit", {"subreddit": sub}
                )

        logger.info(
            "Fetched %d posts from %d subreddits",
            len(all_posts),
            len(subs),
        )
        return all_posts

    def _fetch_subreddit(self, subreddit: str, limit: int) -> List[Dict[str, Any]]:
        """
        Fetch hot posts from a single subreddit.

        Enforces rate limiting and raises on private/unavailable subreddits.

        Args:
            subreddit: Subreddit name (without r/ prefix).
            limit: Maximum number of posts to retrieve.

        Returns:
            List of post dicts.

        Raises:
            SourceUnavailableError: If the subreddit is private or unavailable.
            requests.RequestException: On network errors.
        """
        self._enforce_rate_limit()

        url = f"https://www.reddit.com/r/{subreddit}/hot.json"
        params = {"limit": limit, "raw_json": 1}

        response = self._session.get(url, params=params, timeout=30)
        self._last_request_time = time.monotonic()

        if response.status_code == 403:
            raise Exception(f"Subreddit r/{subreddit} is private or restricted")
        if response.status_code == 404:
            raise Exception(f"Subreddit r/{subreddit} not found")
        response.raise_for_status()

        data = response.json()
        children = data.get("data", {}).get("children", [])

        posts: List[Dict[str, Any]] = []
        for child in children:
            post_data = child.get("data", {})
            posts.append({
                "title": post_data.get("title", ""),
                "score": post_data.get("score", 0),
                "comment_count": post_data.get("num_comments", 0),
                "subreddit": post_data.get("subreddit", subreddit),
                "permalink": post_data.get("permalink", ""),
                "created_utc": post_data.get("created_utc", 0.0),
            })

        return posts

    def _enforce_rate_limit(self) -> None:
        """Sleep if needed to maintain 2-second minimum between requests."""
        if self._last_request_time > 0:
            elapsed = time.monotonic() - self._last_request_time
            if elapsed < self._MIN_REQUEST_INTERVAL:
                sleep_time = self._MIN_REQUEST_INTERVAL - elapsed
                logger.debug("Rate limiting: sleeping %.2fs", sleep_time)
                time.sleep(sleep_time)
