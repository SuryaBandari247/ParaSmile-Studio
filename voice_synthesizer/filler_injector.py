"""Conversational filler injection for natural-sounding narration."""

from __future__ import annotations

import random
import re


class FillerInjector:
    """Injects filler words, thinking pauses, and mid-sentence restarts
    into narration text to simulate natural human speech patterns."""

    DEFAULT_FILLERS: list[tuple[str, float]] = [
        ("uh", 0.20),
        ("um", 0.15),
        ("so", 0.15),
        ("like", 0.10),
        ("you know", 0.10),
        ("basically", 0.08),
        ("right", 0.07),
        ("I mean", 0.07),
        ("well", 0.05),
        ("hmm", 0.03),
    ]

    # Patterns that must never have fillers injected inside them
    PROTECTED_PATTERNS: list[str] = [
        r"`[^`]+`",                                  # Inline code
        r'"[^"]*"',                                  # Double-quoted strings
        r"'[^']*'",                                  # Single-quoted strings
        r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b",     # Multi-word proper nouns
        r"\b[A-Z]{2,}\b",                            # Acronyms (2+ uppercase)
    ]

    # Conjunctions and transitional words that mark natural pause points
    CONJUNCTION_PATTERN = re.compile(
        r"\b(and|but|or|so|yet|because|although|however|therefore|meanwhile)\b",
        re.IGNORECASE,
    )

    INTRODUCTORY_PATTERN = re.compile(
        r"^(However|In fact|Basically|So|Now|Well|Actually|Honestly|Look|See|Okay|Right),?\s",
        re.MULTILINE,
    )

    def __init__(
        self,
        filler_density: float = 0.15,
        restart_probability: float = 0.05,
        min_thinking_pause_ms: int = 150,
        max_thinking_pause_ms: int = 500,
        filler_vocabulary: list[str] | None = None,
        seed: int | None = None,
    ):
        self.filler_density = filler_density
        self.restart_probability = restart_probability
        self.min_thinking_pause_ms = min_thinking_pause_ms
        self.max_thinking_pause_ms = max_thinking_pause_ms
        self.seed = seed
        self._rng = random.Random(seed)

        if filler_vocabulary is not None:
            # Equal weights for custom vocabulary
            weight = 1.0 / len(filler_vocabulary) if filler_vocabulary else 1.0
            self._fillers = [(f, weight) for f in filler_vocabulary]
        else:
            self._fillers = list(self.DEFAULT_FILLERS)

        self._filler_words = [f for f, _ in self._fillers]
        self._filler_weights = [w for _, w in self._fillers]

    def inject(self, text: str) -> str:
        """Insert filler words, thinking pauses, and mid-sentence restarts."""
        if not text or not text.strip():
            return text

        # Reset RNG for deterministic output
        self._rng = random.Random(self.seed)

        protected_spans = self._find_protected_spans(text)
        insertion_points = self._find_insertion_points(text, protected_spans)

        if not insertion_points:
            return text

        # Process insertion points from end to start so indices stay valid
        result = text
        for pos in reversed(insertion_points):
            roll = self._rng.random()

            # Check for mid-sentence restart first (lower probability)
            if roll < self.restart_probability:
                result = self._apply_restart(result, pos)
            elif roll < self.restart_probability + self.filler_density:
                result = self._apply_filler(result, pos)

        return result

    def _find_protected_spans(self, text: str) -> list[tuple[int, int]]:
        """Find character ranges that must not be modified."""
        spans: list[tuple[int, int]] = []
        for pattern in self.PROTECTED_PATTERNS:
            for match in re.finditer(pattern, text):
                spans.append((match.start(), match.end()))
        return spans

    def _find_insertion_points(
        self, text: str, protected_spans: list[tuple[int, int]]
    ) -> list[int]:
        """Find character positions eligible for filler insertion."""
        points: list[int] = []

        # Before conjunctions
        for match in self.CONJUNCTION_PATTERN.finditer(text):
            pos = match.start()
            if not self._in_protected_span(pos, protected_spans):
                points.append(pos)

        # After commas (clause boundaries)
        for i, ch in enumerate(text):
            if ch == "," and i + 1 < len(text) and text[i + 1] == " ":
                pos = i + 2  # After ", "
                if pos < len(text) and not self._in_protected_span(
                    pos, protected_spans
                ):
                    points.append(pos)

        # Deduplicate and sort
        points = sorted(set(points))
        return points

    def _in_protected_span(
        self, pos: int, spans: list[tuple[int, int]]
    ) -> bool:
        """Check if a position falls within any protected span."""
        return any(start <= pos < end for start, end in spans)

    def _pick_filler(self) -> str:
        """Select a random filler word using weighted distribution."""
        return self._rng.choices(self._filler_words, self._filler_weights, k=1)[0]

    def _random_pause_ms(self) -> int:
        """Generate a random thinking pause duration."""
        return self._rng.randint(self.min_thinking_pause_ms, self.max_thinking_pause_ms)

    def _apply_filler(self, text: str, pos: int) -> str:
        """Insert a filler word with thinking pause at the given position."""
        filler = self._pick_filler()
        pause_ms = self._random_pause_ms()
        insertion = f"{{{{pause:{pause_ms}ms}}}} {filler}, "
        return text[:pos] + insertion + text[pos:]

    def _apply_restart(self, text: str, pos: int) -> str:
        """Insert a mid-sentence restart at the given position."""
        # Find the end of the current word cluster (2-4 words after pos)
        words_after = text[pos:].split()
        if len(words_after) < 3:
            # Not enough words for a restart, fall back to filler
            return self._apply_filler(text, pos)

        # Take 2-3 words as the false start
        n_words = min(self._rng.randint(2, 3), len(words_after) - 1)
        false_start_words = words_after[:n_words]
        false_start = " ".join(false_start_words)

        filler = self._pick_filler()
        pause_ms = self._random_pause_ms()

        restart_text = (
            f"{false_start}— "
            f"{{{{pause:{pause_ms}ms}}}} {filler}, "
        )
        return text[:pos] + restart_text + text[pos:]
