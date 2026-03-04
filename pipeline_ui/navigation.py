"""Step management for the pipeline workflow.

Defines the PipelineStep enum, step labels, transition logic,
and the progress bar renderer.
"""

from enum import IntEnum

import streamlit as st

from pipeline_ui.session_state import PipelineData


class PipelineStep(IntEnum):
    """Pipeline workflow steps."""

    SEARCH = 0
    SELECT_TOPIC = 1
    SCRIPT_INPUT = 2
    CONVERT = 3
    REVIEW = 4
    SYNTHESIZE = 5
    RENDER = 6


STEP_LABELS = [
    "Search", "Select Topic", "Script Input", "Convert",
    "Review", "Synthesize", "Render",
]


def can_advance(current_step: PipelineStep, pipeline_data: PipelineData) -> bool:
    """Check if the current step is complete and the user can advance.

    Pure logic function — no Streamlit dependency.
    """
    if current_step == PipelineStep.SEARCH:
        return pipeline_data.search_results is not None
    if current_step == PipelineStep.SELECT_TOPIC:
        return pipeline_data.selected_topic is not None
    if current_step == PipelineStep.SCRIPT_INPUT:
        return bool(pipeline_data.raw_script and pipeline_data.raw_script.strip())
    if current_step == PipelineStep.CONVERT:
        return pipeline_data.video_script is not None
    if current_step == PipelineStep.REVIEW:
        return pipeline_data.video_script is not None
    if current_step == PipelineStep.SYNTHESIZE:
        return pipeline_data.audio_manifest is not None
    # RENDER is the last step — cannot advance further
    return False


def go_to_step(step: int, pipeline_data: PipelineData) -> bool:
    """Navigate to a specific step if allowed.

    Navigation is permitted only to steps <= max_completed_step + 1.
    Updates pipeline_data.current_step on success.
    Returns True if navigation succeeded, False otherwise.
    """
    if step < 0 or step > PipelineStep.RENDER:
        return False
    if step <= pipeline_data.max_completed_step + 1:
        pipeline_data.current_step = step
        return True
    return False


def render_progress_bar() -> None:
    """Render a horizontal step indicator showing current/completed steps."""
    pipeline_data: PipelineData = st.session_state["pipeline"]
    cols = st.columns(len(STEP_LABELS))
    for i, (col, label) in enumerate(zip(cols, STEP_LABELS)):
        with col:
            if i == pipeline_data.current_step:
                st.markdown(f"**🔵 {label}**")
            elif i <= pipeline_data.max_completed_step:
                if st.button(f"✅ {label}", key=f"nav_{i}"):
                    go_to_step(i, pipeline_data)
                    st.rerun()
            else:
                st.markdown(f"⚪ {label}")
