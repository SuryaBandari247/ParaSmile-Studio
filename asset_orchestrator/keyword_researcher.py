"""Context-aware keyword researcher with anti-pattern enforcement.

Generates ranked, visually specific keyword suggestions for stock footage
scenes by analyzing narration context from surrounding scenes.
"""

from __future__ import annotations

import json
import logging
import os
import re

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class KeywordSuggestion(BaseModel):
    """A single suggested search term with optional visual synonym mapping."""

    keyword: str
    rank: int
    original_term: str | None = None
    visual_synonym: str | None = None
    category: str | None = None  # e.g. "subject", "environment", "action", "abstract"
    source_hints: dict[str, str] | None = None  # per-source refined queries, e.g. {"pexels": "...", "pixabay": "..."}


class NarrativeBeat(BaseModel):
    """A narrative beat extracted from the scene — a visual moment implied by the script."""

    beat: str  # e.g. "reveal of chip under microscope"
    timestamp_hint: str | None = None  # e.g. "early", "mid", "late" in the scene
    suggested_keywords: list[str] = []  # keywords that match this beat


class SuggestionResponse(BaseModel):
    """Response containing ranked keyword suggestions, categorized map, narrative beats, and aesthetic hints."""

    suggestions: list[KeywordSuggestion]
    aesthetic_hints: list[str]
    keyword_categories: dict[str, list[str]] = {}  # e.g. {"subject": [...], "environment": [...], "action": [...]}
    narrative_beats: list[NarrativeBeat] = []


BLOCKLIST: list[str] = [
    "man in office",
    "woman at desk",
    "business meeting",
    "people shaking hands",
    "generic office",
    "happy team",
    "thumbs up",
    "woman at computer",
]


class KeywordResearcher:
    """Context-aware keyword researcher with anti-pattern enforcement."""

    def __init__(self, use_llm: bool = True) -> None:
        self._use_llm = use_llm
        self._openai_client = None
        if use_llm:
            try:
                import openai

                api_key = os.getenv("OPENAI_API_KEY", "")
                if api_key:
                    self._openai_client = openai.OpenAI(api_key=api_key)
            except ImportError:
                logger.warning(
                    "openai package not installed, falling back to simple extraction"
                )

    def research(
        self,
        narration: str,
        prev_narration: str | None = None,
        next_narration: str | None = None,
        script_tone: str | None = None,
    ) -> SuggestionResponse:
        """Generate ranked keyword suggestions from narration context.

        Returns 5-8 suggestions with visual synonyms and 2-3 aesthetic hints.
        Falls back to simple noun extraction if LLM fails.
        """
        if self._use_llm and self._openai_client:
            try:
                return self._research_with_llm(
                    narration, prev_narration, next_narration, script_tone
                )
            except Exception as exc:
                logger.warning(
                    "LLM keyword research failed: %s. Falling back to simple extraction.",
                    exc,
                )

        return self._research_fallback(narration)

    def _research_with_llm(
        self,
        narration: str,
        prev_narration: str | None,
        next_narration: str | None,
        script_tone: str | None,
    ) -> SuggestionResponse:
        """Use GPT-4o-mini to generate context-aware keyword suggestions."""
        blocklist_str = ", ".join(f'"{b}"' for b in BLOCKLIST)

        system_message = (
            "You are a stock footage keyword researcher for technical video production.\n"
            "You generate visually specific, concrete keywords for stock footage searches.\n\n"
            "Rules:\n"
            "- Return 5-8 keywords ranked by relevance\n"
            "- Prefer technical, specific, visually concrete terms\n"
            f"- NEVER suggest generic clichés: {blocklist_str}\n"
            "- For niche/proprietary terms, provide a visual_synonym mapping\n"
            "- Derive 2-3 aesthetic hints from the overall tone\n"
            "- Categorize each keyword into one of: subject, environment, action, abstract\n"
            "- Provide source_hints per keyword: optimized search queries for Pexels, Pixabay, Wikimedia, and Unsplash\n"
            "- Identify 2-4 narrative beats — visual moments implied by the narration (e.g. 'reveal of chip under microscope')\n"
            "- For each beat, indicate timing (early/mid/late) and matching keywords\n"
            "- Also return a keyword_categories map grouping all keywords by their category"
        )

        user_message = (
            f"Target scene narration: {narration}\n"
            f"Previous scene narration: {prev_narration or 'N/A'}\n"
            f"Next scene narration: {next_narration or 'N/A'}\n"
            f"Script tone: {script_tone or 'technical, analytical'}\n\n"
            "Return JSON:\n"
            "{\n"
            '  "suggestions": [\n'
            '    {\n'
            '      "keyword": "semiconductor cleanroom",\n'
            '      "rank": 1,\n'
            '      "original_term": "ASML EUV",\n'
            '      "visual_synonym": "semiconductor cleanroom laser",\n'
            '      "category": "environment",\n'
            '      "source_hints": {\n'
            '        "pexels": "cleanroom laboratory",\n'
            '        "pixabay": "semiconductor factory",\n'
            '        "wikimedia": "semiconductor fabrication plant",\n'
            '        "unsplash": "tech laboratory clean"\n'
            "      }\n"
            "    }\n"
            "  ],\n"
            '  "aesthetic_hints": ["dark lighting", "macro close-up"],\n'
            '  "keyword_categories": {\n'
            '    "subject": ["semiconductor cleanroom"],\n'
            '    "environment": ["laboratory interior"],\n'
            '    "action": ["laser etching"],\n'
            '    "abstract": ["digital network"]\n'
            "  },\n"
            '  "narrative_beats": [\n'
            '    {"beat": "reveal of chip under microscope", "timestamp_hint": "early", "suggested_keywords": ["microchip macro", "microscope lens"]}\n'
            "  ]\n"
            "}"
        )

        resp = self._openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ],
            temperature=0.4,
            max_tokens=1000,
        )

        raw_content = resp.choices[0].message.content.strip()
        # Strip markdown code fences if present
        if raw_content.startswith("```"):
            raw_content = re.sub(r"^```(?:json)?\s*", "", raw_content)
            raw_content = re.sub(r"\s*```$", "", raw_content)
        data = json.loads(raw_content)

        suggestions = [
            KeywordSuggestion(**s) for s in data["suggestions"]
        ]
        aesthetic_hints = data.get("aesthetic_hints", [])
        keyword_categories = data.get("keyword_categories", {})
        narrative_beats = [
            NarrativeBeat(**b) for b in data.get("narrative_beats", [])
        ]

        suggestions = self._filter_blocklist(suggestions, narration)

        return SuggestionResponse(
            suggestions=suggestions,
            aesthetic_hints=aesthetic_hints,
            keyword_categories=keyword_categories,
            narrative_beats=narrative_beats,
        )

    def _research_fallback(self, narration: str) -> SuggestionResponse:
        """Extract concrete nouns and adjectives from narration when LLM fails.

        Uses simple word extraction to produce 5-8 keyword suggestions and
        returns generic aesthetic hints. Handles empty narration gracefully.
        """
        _GENERIC_TECHNICAL_TERMS = [
            "technology",
            "abstract",
            "data visualization",
            "circuit board",
            "digital network",
            "server rack",
            "code on screen",
            "microchip",
        ]
        _GENERIC_AESTHETIC_HINTS = [
            "dark lighting",
            "close-up detail",
            "slow motion",
        ]

        terms = self._extract_replacement_terms(narration) if narration.strip() else []

        # Take first 8 unique terms
        keywords = terms[:8]

        # Pad with generic technical terms if fewer than 5
        if len(keywords) < 5:
            for term in _GENERIC_TECHNICAL_TERMS:
                if term not in keywords:
                    keywords.append(term)
                if len(keywords) >= 5:
                    break

        # Cap at 8
        keywords = keywords[:8]

        suggestions = [
            KeywordSuggestion(keyword=kw, rank=i + 1, category="subject")
            for i, kw in enumerate(keywords)
        ]

        # Build basic category map from fallback terms
        keyword_categories = {"subject": keywords[:], "environment": [], "action": [], "abstract": []}

        return SuggestionResponse(
            suggestions=suggestions,
            aesthetic_hints=_GENERIC_AESTHETIC_HINTS,
            keyword_categories=keyword_categories,
            narrative_beats=[],
        )

    def _is_blocked(self, keyword: str) -> bool:
        """Check if keyword matches any blocklist pattern (case-insensitive substring match)."""
        keyword_lower = keyword.lower()
        return any(pattern in keyword_lower for pattern in BLOCKLIST)

    def _filter_blocklist(
        self, suggestions: list[KeywordSuggestion], narration: str
    ) -> list[KeywordSuggestion]:
        """Replace any blocklisted keywords with context-derived alternatives.

        Iterates through suggestions and replaces blocked keywords with
        concrete noun/adjective phrases extracted from the narration text.
        Logs each replacement for auditability.
        """
        filtered: list[KeywordSuggestion] = []
        replacements = self._extract_replacement_terms(narration)
        replacement_idx = 0

        for suggestion in suggestions:
            if self._is_blocked(suggestion.keyword):
                if replacement_idx < len(replacements):
                    replacement = replacements[replacement_idx]
                    replacement_idx += 1
                else:
                    replacement = "technical close-up"

                logger.info(
                    "Blocklist replacement: '%s' -> '%s'",
                    suggestion.keyword,
                    replacement,
                )
                filtered.append(
                    KeywordSuggestion(
                        keyword=replacement,
                        rank=suggestion.rank,
                        original_term=suggestion.original_term,
                        visual_synonym=suggestion.visual_synonym,
                    )
                )
            else:
                filtered.append(suggestion)

        return filtered

    @staticmethod
    def _extract_replacement_terms(narration: str) -> list[str]:
        """Extract concrete noun/adjective phrases from narration for replacements."""
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "shall", "can", "need", "to", "of", "in",
            "for", "on", "with", "at", "by", "from", "as", "into", "through",
            "during", "before", "after", "above", "below", "between", "out", "off",
            "over", "under", "again", "then", "once", "here", "there", "when",
            "where", "why", "how", "all", "both", "each", "few", "more", "most",
            "other", "some", "such", "no", "nor", "not", "only", "own", "same",
            "so", "than", "too", "very", "just", "now", "it", "its", "you", "your",
            "we", "our", "they", "their", "this", "that", "these", "those", "i",
            "me", "my", "he", "him", "his", "she", "her", "what", "which", "who",
            "whom", "but", "and", "or", "if", "about", "up", "down",
        }
        words = re.findall(r"[a-zA-Z]{3,}", narration.lower())
        # Collect unique content words preserving order
        seen: set[str] = set()
        terms: list[str] = []
        for w in words:
            if w not in stop_words and w not in seen:
                seen.add(w)
                terms.append(w)
        return terms
