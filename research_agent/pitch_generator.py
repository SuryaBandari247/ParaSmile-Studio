"""
Pitch Generator for the Research Agent.

Uses OpenAI GPT-4o-mini to synthesize raw trends into compelling Story Pitches.
Generates curiosity-driven questions grounded in real-time data, avoiding
clickbait, hyperbole, and generic phrasing per product.md standards.
"""

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List

from openai import OpenAI

from research_agent.exceptions import AuthenticationError, PitchGenerationError
from research_agent.logger import get_logger
from research_agent.models import SourceTrend, StoryPitch, StoryPitchBoard

logger = get_logger("PitchGenerator")


class PitchGenerator:
    """
    Uses OpenAI GPT-4o-mini to synthesize raw trends into Story Pitches.
    Reads OPENAI_API_KEY from environment.
    """

    MODEL = "gpt-4o-mini"

    def __init__(self) -> None:
        """
        Initialize Pitch Generator.

        Raises:
            AuthenticationError: If OPENAI_API_KEY is missing or empty.
        """
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise AuthenticationError(
                "OPENAI_API_KEY environment variable is missing or empty. "
                "Set it to a valid OpenAI API key."
            )
        self._client = OpenAI(api_key=api_key)
        logger.info("PitchGenerator initialized with model %s", self.MODEL)

    def generate_pitches(
        self,
        unified_topics: List[Dict[str, Any]],
        count: int = 12,
    ) -> StoryPitchBoard:
        """
        Generate Story Pitches from unified trending topics.

        Args:
            unified_topics: Merged/deduplicated topics from CrossReferenceEngine.
            count: Target number of pitches (clamped to 10-15 range).

        Returns:
            StoryPitchBoard containing 10-15 ranked StoryPitches.

        Raises:
            PitchGenerationError: If the OpenAI API call fails or response is unparseable.
        """
        count = max(10, min(15, count))

        if not unified_topics:
            logger.warning("No unified topics provided; returning empty pitch board")
            return StoryPitchBoard(pitches=[], source_topic_count=0)

        prompt = self._build_prompt(unified_topics, count)

        try:
            response = self._client.chat.completions.create(
                model=self.MODEL,
                messages=[
                    {"role": "system", "content": "You are a research analyst for a data-driven video production engine. You output valid JSON only."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=4000,
            )
            response_text = response.choices[0].message.content or ""
        except Exception as exc:
            logger.error("OpenAI API call failed: %s", exc)
            raise PitchGenerationError(f"OpenAI API call failed: {exc}") from exc

        pitches = self._parse_response(response_text, unified_topics)
        ranked = self._rank_pitches(pitches)

        # Clamp to 10-15 pitches
        ranked = ranked[:15]

        board = StoryPitchBoard(
            pitches=ranked,
            generated_at=datetime.now(timezone.utc),
            source_topic_count=len(unified_topics),
        )
        logger.info(
            "Generated %d pitches from %d topics",
            len(ranked),
            len(unified_topics),
        )
        return board

    def _build_prompt(self, topics: List[Dict[str, Any]], count: int) -> str:
        """
        Build GPT-4o-mini prompt instructing it to generate curiosity-driven pitches.

        Instructs the model to:
        - Generate curiosity-driven questions or provocative angles
        - Avoid clickbait, hyperbole, generic phrasing
        - Classify each pitch as recent_event or historic_topic
        - Include source trend references
        """
        topic_summaries = []
        for i, topic in enumerate(topics, 1):
            name = topic.get("topic_name", topic.get("title", f"Topic {i}"))
            category = topic.get("category", "Uncategorized")
            trend_score = topic.get("trend_score", 0)
            source_count = topic.get("source_count", 1)
            sources = topic.get("sources", [])
            source_names = [s.get("source_name", "unknown") for s in sources] if sources else ["unknown"]

            topic_summaries.append(
                f"  {i}. \"{name}\" | category: {category} | trend_score: {trend_score} "
                f"| source_count: {source_count} | sources: {', '.join(source_names)}"
            )

        topics_block = "\n".join(topic_summaries)

        return f"""Analyze the following trending topics and generate exactly {count} story pitches for a data-driven video production engine.

TRENDING TOPICS:
{topics_block}

RULES — follow these strictly:
1. Each pitch title MUST be a specific, curiosity-driven QUESTION (e.g., "Why did NVIDIA's stock surge 15% in one day?" NOT "NVIDIA Stock Surges").
2. NEVER use clickbait language, hyperbole, superlatives ("unbelievable", "shocking", "you won't believe"), or generic phrasing.
3. Each pitch must reference real data points from the source trends.
4. Classify each pitch as either "recent_event" (breaking/current news with real-time data available) or "historic_topic" (evergreen angle with historical context and data visualization opportunity).
5. The hook must be one sentence explaining why this topic is interesting RIGHT NOW, grounded in a specific data point or trend.
6. Include the topic index numbers that informed each pitch in the "source_topic_indices" field.

Return ONLY valid JSON in this exact format (no markdown, no explanation):
{{
  "pitches": [
    {{
      "title": "A specific curiosity-driven question?",
      "hook": "One sentence with a concrete data point explaining why this matters now.",
      "context_type": "recent_event",
      "category": "Finance",
      "source_topic_indices": [1, 3]
    }}
  ]
}}"""

    def _parse_response(
        self, response_text: str, topics: List[Dict[str, Any]]
    ) -> List[StoryPitch]:
        """
        Parse GPT-4o-mini response into StoryPitch objects.

        Handles JSON extraction, builds SourceTrend references from topic indices,
        and assigns data_note based on context_type.
        """
        # Strip markdown code fences if present
        text = response_text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first and last lines (```json and ```)
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse GPT response as JSON: %s", exc)
            raise PitchGenerationError(
                f"Failed to parse GPT response as JSON: {exc}"
            ) from exc

        raw_pitches = data.get("pitches", [])
        if not isinstance(raw_pitches, list):
            raise PitchGenerationError("GPT response 'pitches' field is not a list")

        pitches: List[StoryPitch] = []
        now = datetime.now(timezone.utc)

        for raw in raw_pitches:
            if not isinstance(raw, dict):
                continue

            title = raw.get("title", "").strip()
            hook = raw.get("hook", "").strip()
            context_type = raw.get("context_type", "recent_event")
            category = raw.get("category", "Uncategorized")
            source_indices = raw.get("source_topic_indices", [])

            if not title or not hook:
                continue

            # Validate context_type
            if context_type not in ("recent_event", "historic_topic"):
                context_type = "recent_event"

            # Build SourceTrend references from topic indices
            source_trends: List[SourceTrend] = []
            trend_score_sum = 0.0
            total_source_count = 0

            for idx in source_indices:
                if isinstance(idx, int) and 1 <= idx <= len(topics):
                    topic = topics[idx - 1]
                    trend_score_sum += float(topic.get("trend_score", 0))
                    total_source_count += int(topic.get("source_count", 1))

                    # Pull existing sources from the topic
                    topic_sources = topic.get("sources", [])
                    for src in topic_sources:
                        source_trends.append(
                            SourceTrend(
                                source_name=src.get("source_name", "unknown"),
                                source_url=src.get("source_url", ""),
                                fetched_at=now,
                                raw_data=src,
                            )
                        )

                    # If no sources list, create a generic reference
                    if not topic_sources:
                        source_trends.append(
                            SourceTrend(
                                source_name="aggregated",
                                source_url="",
                                fetched_at=now,
                                raw_data={"topic_name": topic.get("topic_name", "")},
                            )
                        )

            # Calculate estimated_interest = trend_score × source_count
            avg_trend = trend_score_sum / max(len(source_indices), 1)
            estimated_interest = avg_trend * max(total_source_count, 1)

            # Assign data_note based on context_type
            source_names = list({st.source_name for st in source_trends})
            if context_type == "recent_event":
                data_note = f"Real-time data available from {', '.join(source_names) if source_names else 'source trends'}"
            else:
                data_note = "Historical context and data visualization opportunity"

            pitches.append(
                StoryPitch(
                    title=title,
                    hook=hook,
                    source_trends=source_trends,
                    context_type=context_type,
                    category=category,
                    data_note=data_note,
                    estimated_interest=estimated_interest,
                )
            )

        return pitches

    def _rank_pitches(self, pitches: List[StoryPitch]) -> List[StoryPitch]:
        """
        Rank pitches by estimated_interest (trend_score × source_count) descending.
        """
        return sorted(pitches, key=lambda p: p.estimated_interest, reverse=True)
