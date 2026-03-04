"""Pixabay API client for searching and downloading stock video clips and images.

CC0 license — no attribution required. Free API key from https://pixabay.com/api/docs/
"""

from __future__ import annotations

import logging
import os
import re

import requests

logger = logging.getLogger(__name__)

PIXABAY_VIDEO_URL = "https://pixabay.com/api/videos/"
PIXABAY_IMAGE_URL = "https://pixabay.com/api/"


class PixabayClient:
    """Search and download stock videos and images from Pixabay."""

    def __init__(
        self,
        api_key: str | None = None,
        cache_dir: str = "output/pixabay_cache",
    ) -> None:
        self._api_key = api_key or os.getenv("PIXABAY_API_KEY", "")
        if not self._api_key:
            raise ValueError(
                "PIXABAY_API_KEY not set. Get a free key at https://pixabay.com/api/docs/"
            )
        self._cache_dir = os.path.abspath(cache_dir)
        os.makedirs(self._cache_dir, exist_ok=True)
        self._session = requests.Session()

    # ── Video search ──────────────────────────────────────────────────

    def search_videos(
        self,
        query: str,
        per_page: int = 5,
        min_duration: int = 5,
    ) -> list[dict]:
        """Search Pixabay for stock videos."""
        params = {
            "key": self._api_key,
            "q": query,
            "per_page": min(per_page * 2, 50),
            "safesearch": "true",
            "video_type": "film",
        }
        try:
            resp = self._session.get(PIXABAY_VIDEO_URL, params=params, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("Pixabay video search failed for '%s': %s", query, exc)
            return []

        hits = resp.json().get("hits", [])
        results = []
        for h in hits:
            if h.get("duration", 0) < min_duration:
                continue
            videos = h.get("videos", {})
            # Prefer large (1080p), fall back to medium
            best = videos.get("large", {}) or videos.get("medium", {})
            if not best.get("url"):
                best = videos.get("medium", {})
            results.append({
                "id": h["id"],
                "url": h.get("pageURL", ""),
                "duration": h.get("duration", 0),
                "width": best.get("width", 0),
                "height": best.get("height", 0),
                "download_url": best.get("url", ""),
                "tags": h.get("tags", ""),
                "video_files": videos,
            })
        return results[:per_page]

    def download_video(self, video_result: dict, filename: str | None = None) -> str:
        """Download the best-quality video file.

        Returns absolute path to the downloaded MP4.
        """
        download_url = video_result.get("download_url", "")
        if not download_url:
            # Try medium fallback
            videos = video_result.get("video_files", {})
            medium = videos.get("medium", {})
            download_url = medium.get("url", "")
        if not download_url:
            logger.warning("No download URL for Pixabay video %s", video_result.get("id"))
            return ""

        vid_id = video_result.get("id", "unknown")
        if filename is None:
            filename = f"pixabay_{vid_id}.mp4"

        filepath = os.path.join(self._cache_dir, filename)
        if os.path.isfile(filepath):
            logger.info("Cache hit: %s", filepath)
            return os.path.abspath(filepath)

        logger.info("Downloading Pixabay video %s → %s", vid_id, filepath)
        try:
            resp = self._session.get(download_url, stream=True, timeout=60)
            resp.raise_for_status()
            with open(filepath, "wb") as f:
                for chunk in resp.iter_content(chunk_size=1024 * 256):
                    f.write(chunk)
        except requests.RequestException as exc:
            logger.warning("Pixabay download failed: %s", exc)
            return ""

        return os.path.abspath(filepath)

    def search_and_download(self, query: str, min_duration: int = 5) -> str | None:
        """Search and download the best matching video.

        Returns absolute path or None.
        """
        results = self.search_videos(query, per_page=3, min_duration=min_duration)
        if not results:
            logger.info("No Pixabay video results for '%s'", query)
            return None
        path = self.download_video(results[0])
        return path or None

    def search_and_download_multiple(
        self, query: str, count: int = 2, min_duration: int = 3,
    ) -> list[str]:
        """Download multiple clips for jump-cut b-roll."""
        results = self.search_videos(query, per_page=max(count + 2, 5), min_duration=min_duration)
        paths = []
        for r in results[:count]:
            p = self.download_video(r)
            if p:
                paths.append(p)
        return paths

    # ── Image search ──────────────────────────────────────────────────

    def search_images(self, query: str, per_page: int = 8) -> list[dict]:
        """Search Pixabay for images. Returns list of image result dicts."""
        params = {
            "key": self._api_key,
            "q": query,
            "per_page": per_page,
            "safesearch": "true",
            "image_type": "photo",
            "orientation": "horizontal",
            "min_width": 1280,
        }
        try:
            resp = self._session.get(PIXABAY_IMAGE_URL, params=params, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("Pixabay image search failed for '%s': %s", query, exc)
            return []

        hits = resp.json().get("hits", [])
        return [
            {
                "id": h["id"],
                "url": h.get("largeImageURL", h.get("webformatURL", "")),
                "preview_url": h.get("previewURL", ""),
                "width": h.get("imageWidth", h.get("webformatWidth", 0)),
                "height": h.get("imageHeight", h.get("webformatHeight", 0)),
                "tags": h.get("tags", ""),
                "user": h.get("user", ""),
                "page_url": h.get("pageURL", ""),
            }
            for h in hits
        ]
