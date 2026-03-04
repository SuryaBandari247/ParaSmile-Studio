"""Pexels API client for searching and downloading stock video clips."""

from __future__ import annotations

import hashlib
import logging
import os

import requests

from asset_orchestrator.exceptions import ConfigurationError, StockFootageError

logger = logging.getLogger(__name__)

PEXELS_VIDEO_SEARCH_URL = "https://api.pexels.com/videos/search"


class PexelsClient:
    """Search and download stock video clips from Pexels API."""

    def __init__(
        self,
        api_key: str | None = None,
        cache_dir: str = "output/stock_cache",
    ) -> None:
        self._api_key = api_key or os.getenv("PEXELS_API_KEY", "")
        if not self._api_key:
            raise ConfigurationError(
                "PEXELS_API_KEY",
                "Get a free key at https://www.pexels.com/api/",
            )
        self._cache_dir = os.path.abspath(cache_dir)
        os.makedirs(self._cache_dir, exist_ok=True)
        self._session = requests.Session()
        self._session.headers["Authorization"] = self._api_key

    def search_videos(
        self,
        query: str,
        per_page: int = 5,
        min_duration: int = 5,
    ) -> list[dict]:
        """Search Pexels for stock videos matching *query*.

        Returns:
            List of video result dicts. Empty list if no results.
        """
        params = {"query": query, "per_page": per_page, "orientation": "landscape"}
        try:
            resp = self._session.get(PEXELS_VIDEO_SEARCH_URL, params=params, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("Pexels search failed for '%s': %s", query, exc)
            return []

        data = resp.json()
        videos = data.get("videos", [])

        # Filter by min duration
        results = []
        for v in videos:
            if v.get("duration", 0) >= min_duration:
                results.append({
                    "id": v["id"],
                    "url": v.get("url", ""),
                    "duration": v.get("duration", 0),
                    "width": v.get("width", 0),
                    "height": v.get("height", 0),
                    "video_files": v.get("video_files", []),
                })
        return results

    def download_video(
        self,
        video_result: dict,
        filename: str | None = None,
    ) -> str:
        """Download the best-quality video file (preferring 1080p+).

        Returns:
            Absolute path to the downloaded MP4 file.
        """
        video_files = video_result.get("video_files", [])
        if not video_files:
            raise StockFootageError("No video files in result", query="")

        best = self._select_best_file(video_files)
        download_url = best.get("link", "")
        if not download_url:
            raise StockFootageError("No download URL in video file", query="")

        vid_id = video_result.get("id", "unknown")
        if filename is None:
            filename = f"pexels_{vid_id}.mp4"

        filepath = os.path.join(self._cache_dir, filename)

        # Cache hit — skip download
        if os.path.isfile(filepath):
            logger.info("Cache hit: %s", filepath)
            return os.path.abspath(filepath)

        logger.info("Downloading Pexels video %s → %s", vid_id, filepath)
        try:
            resp = self._session.get(download_url, stream=True, timeout=60)
            resp.raise_for_status()
            with open(filepath, "wb") as f:
                for chunk in resp.iter_content(chunk_size=1024 * 256):
                    f.write(chunk)
        except requests.RequestException as exc:
            raise StockFootageError(f"Download failed: {exc}", query=str(vid_id)) from exc

        return os.path.abspath(filepath)

    def search_and_download(
        self,
        query: str,
        min_duration: int = 5,
    ) -> str | None:
        """Search for *query* and download the best result.

        Returns:
            Absolute path to downloaded clip, or None if no results.
        """
        results = self.search_videos(query, per_page=3, min_duration=min_duration)
        if not results:
            logger.info("No Pexels results for '%s'", query)
            return None
        return self.download_video(results[0])

    def search_and_download_multiple(
        self,
        query: str,
        count: int = 2,
        min_duration: int = 3,
    ) -> list[str]:
        """Search and download multiple clips for jump-cut b-roll.

        Returns:
            List of absolute paths to downloaded clips (may be fewer than count).
        """
        results = self.search_videos(query, per_page=max(count + 2, 5), min_duration=min_duration)
        paths = []
        for r in results[:count]:
            try:
                p = self.download_video(r)
                paths.append(p)
            except Exception as exc:
                logger.warning("Failed to download clip %s: %s", r.get("id"), exc)
        return paths



    @staticmethod
    def _select_best_file(video_files: list[dict]) -> dict:
        """Pick the video file closest to 1080p, preferring HD+."""
        target_h = 1080
        # Sort: prefer files >= 1080p height, then closest to 1080
        hd_files = [f for f in video_files if f.get("height", 0) >= target_h]
        if hd_files:
            return min(hd_files, key=lambda f: f.get("height", 9999))
        # No HD files — pick the largest available
        return max(video_files, key=lambda f: f.get("height", 0))
