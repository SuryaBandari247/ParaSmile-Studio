"""
Google Trends client for the Research Agent.

Fetches daily trending searches from Google Trends via the public RSS feed.
No API key required. Falls back gracefully if Google is unreachable.
"""

import xml.etree.ElementTree as ET
from typing import Any, Dict, List
from urllib.parse import quote_plus

import requests

from research_agent.logger import get_logger, log_error_with_context

logger = get_logger("google_trends_client")

# Google Trends daily trending searches RSS feed
_RSS_URL = "https://trends.google.com/trending/rss?geo={geo}"


class GoogleTrendsClient:
    """
    Fetches trending topics from Google Trends via RSS feed.
    No API key required.
    """

    def __init__(self, geo: str = "", hl: str = "en-US"):
        self.geo = geo or "US"
        self.hl = hl
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "Mozilla/5.0"})

    def fetch_trends(
        self,
        geo: str = "",
        hours: int = 24,
    ) -> List[Dict[str, Any]]:
        """
        Fetch daily trending searches from Google Trends RSS feed.

        Returns:
            List of dicts with keys:
            - topic_name: str (lowercase normalised)
            - approximate_search_volume: int
            - related_queries: List[str]
            - source_url: str
        """
        effective_geo = geo or self.geo
        results: List[Dict[str, Any]] = []
        seen: set = set()

        # Try RSS feed
        try:
            results, seen = self._fetch_rss(effective_geo, results, seen)
        except Exception as exc:
            logger.warning("Google Trends RSS unavailable: %s", exc)
            log_error_with_context(
                logger, exc, "fetch_rss", {"geo": effective_geo}
            )

        # Fallback: try pytrends if RSS returned nothing
        if not results:
            try:
                results, seen = self._fetch_pytrends(effective_geo, results, seen)
            except Exception as exc:
                logger.warning("Google Trends pytrends fallback unavailable: %s", exc)

        logger.info(
            "Fetched %d trends from Google Trends (geo=%s)",
            len(results), effective_geo,
        )
        return results

    def _fetch_rss(
        self, geo: str, results: List[Dict[str, Any]], seen: set
    ) -> tuple:
        """Fetch from Google Trends RSS feed."""
        url = _RSS_URL.format(geo=geo.upper())
        resp = self._session.get(url, timeout=15)
        resp.raise_for_status()

        root = ET.fromstring(resp.text)

        # RSS namespace
        ns = {"ht": "https://trends.google.com/trending/rss"}

        for item in root.iter("item"):
            title_el = item.find("title")
            if title_el is None or not title_el.text:
                continue

            raw_name = title_el.text.strip()
            normalised = raw_name.strip().lower()
            if normalised in seen:
                continue
            seen.add(normalised)

            # Extract traffic volume
            traffic_el = item.find("ht:approx_traffic", ns)
            volume = 0
            if traffic_el is not None and traffic_el.text:
                vol_str = traffic_el.text.replace("+", "").replace(",", "")
                try:
                    volume = int(vol_str)
                except ValueError:
                    pass

            # Extract related news titles as related queries
            related: List[str] = []
            for news in item.findall("ht:news_item", ns):
                news_title = news.find("ht:news_item_title", ns)
                if news_title is not None and news_title.text:
                    related.append(news_title.text.strip())

            results.append({
                "topic_name": normalised,
                "approximate_search_volume": volume,
                "related_queries": related[:5],
                "source_url": self._build_source_url(raw_name, geo),
            })

        return results, seen

    def _fetch_pytrends(
        self, geo: str, results: List[Dict[str, Any]], seen: set
    ) -> tuple:
        """Fallback: try pytrends library."""
        try:
            from pytrends.request import TrendReq
        except ImportError:
            return results, seen

        _GEO_TO_PN = {
            "US": "united_states", "GB": "united_kingdom", "IN": "india",
            "CA": "canada", "AU": "australia", "DE": "germany",
            "FR": "france", "BR": "brazil", "JP": "japan",
        }

        pytrends = TrendReq(hl=self.hl, geo=geo)
        pn = _GEO_TO_PN.get(geo.upper(), "united_states")
        df = pytrends.trending_searches(pn=pn)

        for _, row in df.iterrows():
            raw_name = str(row.iloc[0]).strip()
            if not raw_name:
                continue
            normalised = raw_name.strip().lower()
            if normalised in seen:
                continue
            seen.add(normalised)
            results.append({
                "topic_name": normalised,
                "approximate_search_volume": 0,
                "related_queries": [],
                "source_url": self._build_source_url(raw_name, geo),
            })
        return results, seen

    @staticmethod
    def _build_source_url(topic: str, geo: str) -> str:
        encoded = quote_plus(topic)
        base = f"https://trends.google.com/trends/explore?q={encoded}"
        if geo:
            base += f"&geo={geo.upper()}"
        return base
