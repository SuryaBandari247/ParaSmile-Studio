"""
Wikipedia Current Events client for the Research Agent.

Fetches curated daily global news summaries from the Wikipedia Current Events
portal using requests + BeautifulSoup. No API key required. Parses event
entries into structured records with category classification and named entity
extraction.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from research_agent.logger import get_logger, log_error_with_context

logger = get_logger("wikipedia_events_client")


class WikipediaEventsClient:
    """
    Fetches curated daily events from Wikipedia Current Events portal.
    No API key required. Uses requests + BeautifulSoup.
    """

    BASE_URL = "https://en.wikipedia.org/wiki/Portal:Current_events"

    EVENT_CATEGORIES: List[str] = [
        "Armed conflicts and attacks",
        "Disasters and accidents",
        "International relations",
        "Law and crime",
        "Politics and elections",
        "Science and technology",
        "Sports",
    ]

    # Keyword patterns for classifying events into categories
    _CATEGORY_KEYWORDS: Dict[str, List[str]] = {
        "Armed conflicts and attacks": [
            "war", "attack", "military", "bomb", "soldier", "troops",
            "missile", "airstrike", "insurgent", "militant", "combat",
            "conflict", "armed", "killed", "shooting", "terrorism",
            "ceasefire", "invasion", "siege", "rebel",
        ],
        "Disasters and accidents": [
            "earthquake", "flood", "hurricane", "tornado", "wildfire",
            "crash", "explosion", "disaster", "accident", "storm",
            "tsunami", "drought", "landslide", "collapse", "derail",
            "fire", "poisoning", "deaths", "rescue",
        ],
        "International relations": [
            "diplomat", "treaty", "summit", "ambassador", "sanctions",
            "relations", "bilateral", "alliance", "united nations",
            "nato", "eu", "trade deal", "foreign minister", "embassy",
        ],
        "Law and crime": [
            "court", "judge", "trial", "arrest", "prison", "sentence",
            "convicted", "crime", "murder", "fraud", "lawsuit", "verdict",
            "indictment", "police", "investigation", "warrant", "impeach",
        ],
        "Politics and elections": [
            "election", "vote", "president", "parliament", "minister",
            "governor", "legislation", "bill", "referendum", "campaign",
            "political", "party", "coalition", "inaugurat", "resign",
        ],
        "Science and technology": [
            "research", "scientist", "discovery", "space", "nasa",
            "climate", "vaccine", "medical", "ai", "artificial intelligence",
            "robot", "quantum", "genome", "species", "satellite", "launch",
            "fda", "drug", "treatment", "study",
        ],
        "Sports": [
            "championship", "tournament", "olympic", "world cup",
            "league", "football", "soccer", "basketball", "tennis",
            "cricket", "medal", "athlete", "coach", "stadium", "fifa",
        ],
    }

    def __init__(self) -> None:
        """Initialize Wikipedia Events client."""
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "CalmCapitalist/1.0 (research-agent)"
        })
        logger.info("WikipediaEventsClient initialized")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch_current_events(
        self, date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch events from Wikipedia Current Events portal.

        Falls back to previous day if current day's page is unavailable (404).

        Args:
            date: Target date (default: today in UTC).

        Returns:
            List of dicts with keys: headline, category, date,
            related_links, summary, named_entities.
        """
        target_date = date or datetime.utcnow()

        # Try the target date first, then fall back to previous day
        for attempt_date in [target_date, target_date - timedelta(days=1)]:
            url = self._build_url(attempt_date)
            try:
                response = self._session.get(url, timeout=30)

                if response.status_code == 404:
                    logger.warning(
                        "Wikipedia Current Events page not found for %s, "
                        "trying previous day",
                        attempt_date.strftime("%Y-%m-%d"),
                    )
                    continue

                response.raise_for_status()

                events = self._parse_events_page(
                    response.text, attempt_date
                )
                logger.info(
                    "Fetched %d events from Wikipedia for %s",
                    len(events),
                    attempt_date.strftime("%Y-%m-%d"),
                )
                return events

            except requests.RequestException as exc:
                logger.warning(
                    "Wikipedia unreachable for %s: %s",
                    attempt_date.strftime("%Y-%m-%d"),
                    exc,
                )
                log_error_with_context(
                    logger,
                    exc,
                    "fetch_current_events",
                    {"date": attempt_date.strftime("%Y-%m-%d"), "url": url},
                )
                # If this was the first attempt, try the fallback date
                if attempt_date == target_date and date is not None:
                    continue
                # Otherwise give up gracefully
                return []

        # Both dates failed (404 on both)
        logger.warning(
            "Wikipedia Current Events unavailable for %s and previous day",
            target_date.strftime("%Y-%m-%d"),
        )
        return []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_url(self, date: datetime) -> str:
        """Build Wikipedia Current Events portal URL for a given date.

        Format: Portal:Current_events/2024_January_15
        """
        date_str = date.strftime("%Y_%B_%-d")
        return f"{self.BASE_URL}/{date_str}"

    def _parse_events_page(
        self, html: str, date: datetime
    ) -> List[Dict[str, Any]]:
        """
        Parse HTML from Current Events portal into structured records.

        The portal uses bold text or <b> tags for category headers,
        followed by <ul>/<li> elements for individual events. Each event
        may contain links to Wikipedia articles.

        Args:
            html: Raw HTML of the Current Events page.
            date: The date of the events page.

        Returns:
            List of event dicts.
        """
        soup = BeautifulSoup(html, "html.parser")
        events: List[Dict[str, Any]] = []
        date_str = date.strftime("%Y-%m-%d")

        # Find the main content area
        content = soup.find("div", {"class": "mw-parser-output"})
        if content is None:
            content = soup.find("div", {"id": "mw-content-text"})
        if content is None:
            logger.warning("Could not find content area in Wikipedia page")
            return events

        current_category = "Uncategorized"

        # Walk through the content looking for category headers and event items
        for element in content.descendants:
            # Detect category headers — they appear as bold text (<b> or <p><b>)
            if element.name == "b" or element.name == "strong":
                text = element.get_text(strip=True)
                matched_cat = self._match_category_header(text)
                if matched_cat:
                    current_category = matched_cat

            # Detect event items — they are <li> elements containing text
            if element.name == "li":
                # Skip nested list items that are sub-items (indented context)
                # We want the deepest <li> that contains actual event text
                child_lis = element.find_all("li", recursive=True)
                if child_lis:
                    # This <li> has sub-items; skip it and process children
                    continue

                event_text = element.get_text(separator=" ", strip=True)
                if not event_text or len(event_text) < 20:
                    continue

                # Extract links from this list item
                links = self._extract_links(element)
                entities = self._extract_named_entities(element)

                # Build headline from the first sentence or the full text
                headline = self._extract_headline(event_text)

                events.append({
                    "headline": headline,
                    "category": current_category,
                    "date": date_str,
                    "related_links": links,
                    "summary": event_text,
                    "named_entities": entities,
                })

        return events

    def _match_category_header(self, text: str) -> Optional[str]:
        """Match bold text against known EVENT_CATEGORIES.

        Uses case-insensitive prefix matching.

        Args:
            text: Bold text from the page.

        Returns:
            Matched category name or None.
        """
        text_lower = text.lower().strip()
        for category in self.EVENT_CATEGORIES:
            if text_lower.startswith(category.lower()):
                return category
        return None

    def _classify_event(self, text: str) -> str:
        """
        Classify event text into one of EVENT_CATEGORIES using keyword matching.

        Args:
            text: Event text to classify.

        Returns:
            Best matching category name, or 'Uncategorized' if no match.
        """
        text_lower = text.lower()
        best_category = "Uncategorized"
        best_score = 0

        for category, keywords in self._CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > best_score:
                best_score = score
                best_category = category

        return best_category

    def _extract_named_entities(self, element: Any) -> List[str]:
        """
        Extract named entities (people, places, organizations) from an element.

        Uses Wikipedia links as a proxy for named entities — linked text in
        Wikipedia Current Events typically refers to notable people, places,
        and organizations.

        Args:
            element: BeautifulSoup element containing the event text.

        Returns:
            List of entity name strings.
        """
        entities: List[str] = []
        seen: set = set()

        for link in element.find_all("a", href=True):
            href = link.get("href", "")
            text = link.get_text(strip=True)

            # Only consider internal Wikipedia links (not external sources)
            if not href.startswith("/wiki/"):
                continue

            # Skip portal/category/special pages
            if any(
                prefix in href
                for prefix in ["/wiki/Portal:", "/wiki/Category:",
                               "/wiki/Special:", "/wiki/File:",
                               "/wiki/Help:", "/wiki/Wikipedia:"]
            ):
                continue

            # Skip very short text (likely abbreviations or formatting)
            if len(text) < 2:
                continue

            text_key = text.lower()
            if text_key not in seen:
                seen.add(text_key)
                entities.append(text)

        return entities

    def _extract_links(self, element: Any) -> List[str]:
        """
        Extract Wikipedia article URLs from an element.

        Args:
            element: BeautifulSoup element.

        Returns:
            List of full Wikipedia URLs.
        """
        links: List[str] = []
        seen: set = set()

        for link in element.find_all("a", href=True):
            href = link.get("href", "")

            if href.startswith("/wiki/") and href not in seen:
                # Skip non-article pages
                if any(
                    prefix in href
                    for prefix in ["/wiki/Portal:", "/wiki/Category:",
                                   "/wiki/Special:", "/wiki/File:"]
                ):
                    continue
                full_url = f"https://en.wikipedia.org{href}"
                seen.add(href)
                links.append(full_url)

        return links

    @staticmethod
    def _extract_headline(text: str) -> str:
        """
        Extract a concise headline from event text.

        Takes the first sentence (up to the first period followed by a space)
        or the full text if no sentence boundary is found, capped at 200 chars.

        Args:
            text: Full event text.

        Returns:
            Headline string.
        """
        # Find first sentence boundary
        for i, char in enumerate(text):
            if char == "." and i < len(text) - 1 and text[i + 1] == " ":
                headline = text[: i + 1]
                if len(headline) >= 20:
                    return headline

        # No clear sentence boundary; truncate
        if len(text) > 200:
            return text[:197] + "..."
        return text
