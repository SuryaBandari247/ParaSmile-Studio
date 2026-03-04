"""Extract visual search keywords from scene narration text."""

from __future__ import annotations

import logging
import os
import re

logger = logging.getLogger(__name__)


class KeywordExtractor:
    """Extract visual search keywords from scene narration for stock footage search."""

    def __init__(self, use_llm: bool = True) -> None:
        self._use_llm = use_llm
        self._cache: dict[str, list[str]] = {}
        self._openai_client = None
        if use_llm:
            try:
                import openai
                api_key = os.getenv("OPENAI_API_KEY", "")
                if api_key:
                    self._openai_client = openai.OpenAI(api_key=api_key)
            except ImportError:
                logger.warning("openai package not installed, falling back to simple extraction")

    def extract(self, narration_text: str, title: str = "") -> list[str]:
        """Extract 2-4 visual search keywords from narration.

        Returns:
            List of 2-4 keyword strings suitable for Pexels search.
        """
        cache_key = f"{title}::{narration_text}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        keywords: list[str] = []
        if self._use_llm and self._openai_client:
            try:
                keywords = self._extract_with_llm(narration_text, title)
            except Exception as exc:
                logger.warning("LLM keyword extraction failed: %s. Falling back.", exc)

        if not keywords:
            keywords = self._extract_simple(narration_text, title)

        self._cache[cache_key] = keywords
        return keywords

    def _extract_with_llm(self, narration_text: str, title: str) -> list[str]:
        """Use GPT-4o-mini to extract visual keywords."""
        prompt = (
            "You are a stock footage search assistant. Given a video scene's narration text, "
            "extract 2-4 visual search keywords that would find relevant B-roll footage on a "
            "stock video site. Focus on concrete visual concepts (people, places, actions, objects). "
            "Return ONLY a comma-separated list of keywords, nothing else.\n\n"
            f"Scene title: {title}\n"
            f"Narration: {narration_text}\n\n"
            "Keywords:"
        )
        resp = self._openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50,
            temperature=0.3,
        )
        raw = resp.choices[0].message.content.strip()
        keywords = [k.strip() for k in raw.split(",") if k.strip()]
        return keywords[:4] if keywords else []

    def _extract_simple(self, narration_text: str, title: str) -> list[str]:
        """Fallback: extract key phrases using simple heuristics."""
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "shall", "can", "need", "dare", "ought",
            "used", "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "as", "into", "through", "during", "before", "after", "above", "below",
            "between", "out", "off", "over", "under", "again", "further", "then",
            "once", "here", "there", "when", "where", "why", "how", "all", "both",
            "each", "few", "more", "most", "other", "some", "such", "no", "nor",
            "not", "only", "own", "same", "so", "than", "too", "very", "just",
            "don", "now", "it", "its", "you", "your", "we", "our", "they", "their",
            "this", "that", "these", "those", "i", "me", "my", "he", "him", "his",
            "she", "her", "what", "which", "who", "whom", "but", "and", "or", "if",
            "about", "up", "down", "s", "t", "re", "ve", "ll", "d", "m",
        }
        combined = f"{title} {narration_text}"
        words = re.findall(r"[a-zA-Z]{3,}", combined.lower())
        # Count frequency, skip stop words
        freq: dict[str, int] = {}
        for w in words:
            if w not in stop_words:
                freq[w] = freq.get(w, 0) + 1
        # Sort by frequency, take top 3
        sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        keywords = [w for w, _ in sorted_words[:3]]
        return keywords if keywords else ["abstract", "technology"]
