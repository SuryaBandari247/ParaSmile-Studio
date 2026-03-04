"""
Human-in-the-loop topic selector for the Research Agent.

Presents a StoryPitchBoard to the content producer and handles interactive
selection, regeneration, and detail inspection commands.
"""

from typing import Any, Dict, List

from research_agent.logger import get_logger
from research_agent.models import StoryPitch, StoryPitchBoard

logger = get_logger("TopicSelector")


class TopicSelector:
    """
    Presents Story_Pitch_Board and handles human selection.
    Supports selection by index, "regenerate", and "details N" commands.
    """

    def __init__(self, pitch_generator: Any) -> None:
        """
        Initialize topic selector.

        Args:
            pitch_generator: PitchGenerator instance for regeneration support.
        """
        self._pitch_generator = pitch_generator

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def present_and_select(
        self,
        board: StoryPitchBoard,
        unified_topics: List[Dict[str, Any]],
    ) -> StoryPitch:
        """
        Present pitch board and handle user selection loop.

        Supported commands:
        - Integer index (1-N): select that pitch
        - "regenerate": generate new pitches from the same trends
        - "details N": show full source trend data for pitch N

        Args:
            board: StoryPitchBoard to present.
            unified_topics: Original unified topics (used for regeneration).

        Returns:
            The selected StoryPitch dataclass.
        """
        while True:
            rendered = self._render_board(board)
            print(rendered)
            print(
                "\nEnter a number to select a pitch, "
                '"regenerate" for new pitches, '
                'or "details N" to inspect a pitch.'
            )

            user_input = input("> ").strip()

            if not user_input:
                print("Error: empty input. Please enter a valid command.")
                continue

            # --- "regenerate" command ---
            if user_input.lower() == "regenerate":
                logger.info("User requested pitch regeneration")
                print("\nRegenerating pitches from the same trends…\n")
                board = self._pitch_generator.generate_pitches(unified_topics)
                continue

            # --- "details N" command ---
            if user_input.lower().startswith("details"):
                parts = user_input.split(None, 1)
                if len(parts) < 2 or not parts[1].isdigit():
                    print("Error: usage is 'details N' where N is a pitch number.")
                    continue
                idx = int(parts[1])
                if idx < 1 or idx > len(board.pitches):
                    print(
                        f"Error: invalid pitch number {idx}. "
                        f"Choose between 1 and {len(board.pitches)}."
                    )
                    continue
                detail_text = self._show_details(board.pitches[idx - 1])
                print(detail_text)
                continue

            # --- Integer index selection ---
            if user_input.isdigit():
                idx = int(user_input)
                if idx < 1 or idx > len(board.pitches):
                    print(
                        f"Error: invalid selection {idx}. "
                        f"Choose between 1 and {len(board.pitches)}."
                    )
                    continue
                selected = board.pitches[idx - 1]
                logger.info("User selected pitch %d: %s", idx, selected.title)
                print(f"\n✓ Selected: {selected.title}\n")
                return selected

            # --- Unrecognized input ---
            print(
                f"Error: unrecognized command '{user_input}'. "
                "Enter a number, 'regenerate', or 'details N'."
            )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _render_board(self, board: StoryPitchBoard) -> str:
        """Render pitch board as a numbered list with title, hook, context_type, category."""
        lines: List[str] = []
        lines.append("")
        lines.append("=" * 60)
        lines.append("  STORY PITCH BOARD")
        lines.append("=" * 60)

        for i, pitch in enumerate(board.pitches, start=1):
            lines.append(f"\n  [{i}] {pitch.title}")
            lines.append(f"      Hook: {pitch.hook}")
            lines.append(f"      Type: {pitch.context_type}  |  Category: {pitch.category}")

        lines.append("")
        lines.append("=" * 60)
        lines.append(f"  {len(board.pitches)} pitches generated from {board.source_topic_count} topics")
        lines.append("=" * 60)
        return "\n".join(lines)

    def _show_details(self, pitch: StoryPitch) -> str:
        """Render full source trend data for a pitch."""
        lines: List[str] = []
        lines.append("")
        lines.append("-" * 60)
        lines.append(f"  DETAILS: {pitch.title}")
        lines.append("-" * 60)
        lines.append(f"  Hook:     {pitch.hook}")
        lines.append(f"  Type:     {pitch.context_type}")
        lines.append(f"  Category: {pitch.category}")
        lines.append(f"  Interest: {pitch.estimated_interest:.1f}")
        if pitch.data_note:
            lines.append(f"  Note:     {pitch.data_note}")

        lines.append("")
        lines.append("  Source Trends:")
        if not pitch.source_trends:
            lines.append("    (no source trends recorded)")
        else:
            for j, st in enumerate(pitch.source_trends, start=1):
                lines.append(f"    {j}. [{st.source_name}] {st.source_url}")
                fetched = (
                    st.fetched_at.isoformat()
                    if hasattr(st.fetched_at, "isoformat")
                    else str(st.fetched_at)
                )
                lines.append(f"       Fetched: {fetched}")
                if st.raw_data:
                    for key, value in st.raw_data.items():
                        lines.append(f"       {key}: {value}")

        lines.append("-" * 60)
        return "\n".join(lines)
