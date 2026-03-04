"""Wikimedia Commons client for searching and downloading freely-licensed images.

No API key required. Images are typically CC BY-SA or public domain.
Useful for actual company photos, products, buildings, and historical images
that stock footage sites like Pexels don't carry.
"""

from __future__ import annotations

import logging
import os
import re

import requests

logger = logging.getLogger(__name__)

COMMONS_API_URL = "https://commons.wikimedia.org/w/api.php"

# Licenses considered safe for YouTube editorial use
FREE_LICENSES = {
    "cc-by-sa-4.0", "cc-by-sa-3.0", "cc-by-sa-2.0",
    "cc-by-4.0", "cc-by-3.0", "cc-by-2.0",
    "cc-zero", "pd", "public domain",
}


class WikimediaResult:
    """A single image result from Wikimedia Commons."""

    __slots__ = ("title", "url", "thumb_url", "width", "height", "license", "attribution", "description")

    def __init__(self, title: str, url: str, thumb_url: str,
                 width: int, height: int, license_: str,
                 attribution: str, description: str) -> None:
        self.title = title
        self.url = url
        self.thumb_url = thumb_url
        self.width = width
        self.height = height
        self.license = license_
        self.attribution = attribution
        self.description = description

    def to_dict(self) -> dict:
        return {
            "title": self.title, "url": self.url, "thumb_url": self.thumb_url,
            "width": self.width, "height": self.height,
            "license": self.license, "attribution": self.attribution,
        }


class WikimediaCommonsClient:
    """Search and download images from Wikimedia Commons."""

    def __init__(self, cache_dir: str = "output/wikimedia_cache") -> None:
        self._cache_dir = os.path.abspath(cache_dir)
        os.makedirs(self._cache_dir, exist_ok=True)
        self._session = requests.Session()
        self._session.headers["User-Agent"] = (
            "ParaSmileStudio/1.0 (https://github.com/parasmile-studio; "
            "parasmile-studio@users.noreply.github.com) python-requests/2.31"
        )

    def search_images(
        self,
        query: str,
        limit: int = 10,
        min_width: int = 800,
    ) -> list[WikimediaResult]:
        """Search Commons for images matching *query*.

        Uses the MediaWiki API generator=search with file namespace.
        Filters for images above min_width and with free licenses.
        """
        # Fetch a generous batch — many get filtered out by license/size
        fetch_limit = min(max(limit * 4, 40), 50)
        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrnamespace": "6",  # File namespace
            "gsrsearch": query,
            "gsrlimit": str(fetch_limit),
            "prop": "imageinfo",
            "iiprop": "url|size|extmetadata|mime",
            "iiurlwidth": "1920",  # request a scaled thumb
        }

        try:
            resp = self._session.get(COMMONS_API_URL, params=params, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("Wikimedia search failed for '%s': %s", query, exc)
            return []

        data = resp.json()
        pages = data.get("query", {}).get("pages", {})

        results: list[WikimediaResult] = []
        for page in pages.values():
            ii = (page.get("imageinfo") or [{}])[0]
            width = ii.get("width", 0)
            height = ii.get("height", 0)
            mime = ii.get("mime", "")

            # Skip non-image or too small
            if not mime.startswith("image/") or width < min_width:
                continue

            url = ii.get("url", "")
            thumb_url = ii.get("thumburl", url)
            ext_meta = ii.get("extmetadata", {})

            # Extract license
            license_short = ext_meta.get("LicenseShortName", {}).get("value", "")
            license_lower = license_short.lower().strip()

            # Accept images with known free licenses or no license info
            # (many Commons images are free but have inconsistent metadata)
            if license_lower:
                license_normalized = re.sub(r"[\s\-]+", "-", license_lower)
                is_free = any(fl in license_normalized for fl in FREE_LICENSES)
                # Also accept common variants the strict set misses
                is_free = is_free or any(tag in license_lower for tag in (
                    "cc", "public", "pd", "gfdl", "free", "fal",
                ))
                if not is_free:
                    continue

            attribution = ext_meta.get("Artist", {}).get("value", "")
            # Strip HTML tags from attribution
            attribution = re.sub(r"<[^>]+>", "", attribution).strip()
            description = ext_meta.get("ImageDescription", {}).get("value", "")
            description = re.sub(r"<[^>]+>", "", description).strip()

            results.append(WikimediaResult(
                title=page.get("title", ""),
                url=url,
                thumb_url=thumb_url,
                width=width,
                height=height,
                license_=license_short or "Wikimedia Commons",
                attribution=attribution,
                description=description,
            ))

        # Sort by resolution (prefer larger)
        results.sort(key=lambda r: r.width * r.height, reverse=True)
        return results[:limit]

    def download_image(self, result: WikimediaResult, filename: str | None = None) -> str:
        """Download an image to the cache directory.

        Returns:
            Absolute path to the downloaded image file.
        """
        if filename is None:
            # Derive filename from title
            safe_name = re.sub(r"[^\w\-.]", "_", result.title.replace("File:", ""))
            filename = safe_name[:80]

        filepath = os.path.join(self._cache_dir, filename)

        if os.path.isfile(filepath):
            logger.info("Cache hit: %s", filepath)
            return os.path.abspath(filepath)

        # Use the thumb URL (pre-scaled to 1920px) for faster download
        download_url = result.thumb_url or result.url
        logger.info("Downloading Wikimedia image: %s → %s", result.title, filepath)

        try:
            resp = self._session.get(download_url, stream=True, timeout=30,
                                     headers={"User-Agent": self._session.headers["User-Agent"]})
            resp.raise_for_status()
            with open(filepath, "wb") as f:
                for chunk in resp.iter_content(chunk_size=1024 * 64):
                    f.write(chunk)
        except requests.RequestException as exc:
            logger.warning("Wikimedia download failed: %s", exc)
            return ""

        return os.path.abspath(filepath)

    def search_and_download(
        self,
        query: str,
        min_width: int = 800,
    ) -> str | None:
        """Search and download the best matching image.

        Returns:
            Absolute path to downloaded image, or None if no results.
        """
        results = self.search_images(query, limit=3, min_width=min_width)
        if not results:
            logger.info("No Wikimedia results for '%s'", query)
            return None
        path = self.download_image(results[0])
        return path or None

    def search_and_download_multiple(
        self,
        query: str,
        count: int = 3,
        min_width: int = 800,
    ) -> list[str]:
        """Search and download multiple images.

        Returns:
            List of absolute paths to downloaded images.
        """
        results = self.search_images(query, limit=count + 2, min_width=min_width)
        paths = []
        for r in results[:count]:
            p = self.download_image(r)
            if p:
                paths.append(p)
        return paths

    def get_attribution(self, result: WikimediaResult) -> str:
        """Generate a proper attribution string for the image."""
        parts = []
        if result.attribution:
            parts.append(f"By {result.attribution}")
        if result.license:
            parts.append(f"License: {result.license}")
        parts.append("Via Wikimedia Commons")
        return " | ".join(parts)
