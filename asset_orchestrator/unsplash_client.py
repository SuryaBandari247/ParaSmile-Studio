"""Unsplash API client for searching and downloading high-quality stock photos.

Free API: 50 requests/hour (demo), 5000/hour (production key).
No attribution required for most uses, but appreciated.
Get a key at https://unsplash.com/developers
"""

from __future__ import annotations

import hashlib
import logging
import os

import requests

logger = logging.getLogger(__name__)

UNSPLASH_API_URL = "https://api.unsplash.com"


class UnsplashClient:
    """Search and download stock photos from Unsplash."""

    def __init__(
        self,
        api_key: str | None = None,
        cache_dir: str = "output/unsplash_cache",
    ) -> None:
        self._api_key = api_key or os.getenv("UNSPLASH_ACCESS_KEY", "")
        if not self._api_key:
            raise ValueError(
                "UNSPLASH_ACCESS_KEY not set. Get a free key at "
                "https://unsplash.com/developers"
            )
        self._cache_dir = os.path.abspath(cache_dir)
        os.makedirs(self._cache_dir, exist_ok=True)
        self._session = requests.Session()
        self._session.headers["Authorization"] = f"Client-ID {self._api_key}"
        self._session.headers["Accept-Version"] = "v1"

    def search_photos(
        self,
        query: str,
        per_page: int = 15,
        orientation: str = "landscape",
    ) -> list[dict]:
        """Search Unsplash for photos matching *query*.

        Returns list of photo result dicts with id, urls, dimensions, description.
        """
        params = {
            "query": query,
            "per_page": min(per_page, 30),
            "orientation": orientation,
        }
        try:
            resp = self._session.get(
                f"{UNSPLASH_API_URL}/search/photos",
                params=params,
                timeout=15,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("Unsplash search failed for '%s': %s", query, exc)
            return []

        data = resp.json()
        results = []
        for photo in data.get("results", []):
            urls = photo.get("urls", {})
            results.append({
                "id": photo["id"],
                "description": photo.get("description") or photo.get("alt_description") or "",
                "width": photo.get("width", 0),
                "height": photo.get("height", 0),
                "url": urls.get("regular", ""),       # 1080px wide
                "full_url": urls.get("full", ""),      # original size
                "thumb_url": urls.get("thumb", ""),    # 200px wide
                "small_url": urls.get("small", ""),    # 400px wide
                "page_url": photo.get("links", {}).get("html", ""),
                "photographer": photo.get("user", {}).get("name", ""),
                "color": photo.get("color", "#000000"),
            })
        return results

    def download_photo(
        self,
        photo_result: dict,
        filename: str | None = None,
    ) -> str:
        """Download a photo (regular quality, 1080px wide).

        Returns absolute path to the downloaded image file.
        """
        url = photo_result.get("url") or photo_result.get("full_url", "")
        if not url:
            logger.warning("No download URL for Unsplash photo %s", photo_result.get("id"))
            return ""

        photo_id = photo_result.get("id", "unknown")
        if filename is None:
            filename = f"unsplash_{photo_id}.jpg"

        filepath = os.path.join(self._cache_dir, filename)
        if os.path.isfile(filepath):
            logger.info("Cache hit: %s", filepath)
            return os.path.abspath(filepath)

        logger.info("Downloading Unsplash photo %s → %s", photo_id, filepath)
        try:
            resp = self._session.get(url, stream=True, timeout=30)
            resp.raise_for_status()
            with open(filepath, "wb") as f:
                for chunk in resp.iter_content(chunk_size=64 * 1024):
                    f.write(chunk)
        except requests.RequestException as exc:
            logger.warning("Unsplash download failed: %s", exc)
            return ""

        return os.path.abspath(filepath)

    def search_and_download(
        self,
        query: str,
    ) -> str | None:
        """Search and download the best matching photo.

        Returns absolute path or None.
        """
        results = self.search_photos(query, per_page=3)
        if not results:
            logger.info("No Unsplash results for '%s'", query)
            return None
        path = self.download_photo(results[0])
        return path or None
