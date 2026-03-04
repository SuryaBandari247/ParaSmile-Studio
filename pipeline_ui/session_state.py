"""Session state initialization and accessors.

Manages PipelineData stored in Streamlit session state,
providing typed helpers for reading, writing, and resetting state.
"""

from dataclasses import dataclass, field
from typing import Any, Optional

import streamlit as st


@dataclass
class PipelineData:
    """All pipeline state stored in session."""

    current_step: int = 0
    max_completed_step: int = -1

    # Step 1: Search
    search_results: Optional[dict] = None

    # Step 2: Select Topic
    selected_topic: Optional[dict] = None

    # Step 3: Script Input
    raw_script: str = ""
    parsed_documents: list[dict] = field(default_factory=list)

    # Step 4: Convert
    video_script: Optional[Any] = None
    conversion_metadata: Optional[dict] = None

    # Step 5: Synthesize
    audio_manifest: Optional[Any] = None

    # Step 6: Render
    render_result: Optional[Any] = None
    final_video_path: Optional[str] = None


def init_session_state() -> None:
    """Initialize session state with PipelineData if not present."""
    if "pipeline" not in st.session_state:
        st.session_state["pipeline"] = PipelineData()


def get_pipeline() -> PipelineData:
    """Return the current PipelineData from session state."""
    return st.session_state["pipeline"]


def clear_session_state() -> None:
    """Reset all pipeline state to defaults."""
    st.session_state["pipeline"] = PipelineData()
