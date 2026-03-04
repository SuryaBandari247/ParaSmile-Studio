"""Topic selection panel — Step 2 of the pipeline.

Displays the Story Pitch Board from the Search step and allows
the user to browse, select, and confirm a topic for scripting.
"""

import logging

import streamlit as st

from pipeline_ui.navigation import PipelineStep, go_to_step
from pipeline_ui.session_state import get_pipeline

logger = logging.getLogger("pipeline_ui")


def render_select_topic_panel() -> None:
    """Step 2: Browse and select a topic from the Story Pitch Board."""
    pipeline = get_pipeline()

    st.subheader("Select a Topic")

    if not pipeline.search_results:
        st.warning("No search results available. Please complete the Search step first.")
        return

    topics = pipeline.search_results.get("unified", pipeline.search_results.get("topics", []))
    if not topics:
        st.info("No topics found in search results. Go back and search again.")
        return

    # Build radio options from topic list
    options = [
        f"{topic.get('topic_name', 'Untitled')} — {topic.get('category', 'N/A')}"
        for topic in topics
    ]

    selected_index = st.radio(
        "Choose a topic:",
        range(len(options)),
        format_func=lambda i: options[i],
        key="topic_selection_radio",
    )

    # Show full details for the selected topic
    if selected_index is not None:
        _render_topic_details(topics[selected_index])

    # Confirm selection button
    if st.button("Confirm Selection", key="confirm_topic"):
        if selected_index is not None:
            pipeline.selected_topic = topics[selected_index]
            pipeline.max_completed_step = max(
                pipeline.max_completed_step,
                int(PipelineStep.SELECT_TOPIC),
            )
            go_to_step(PipelineStep.SCRIPT_INPUT, pipeline)
            st.rerun()


def _render_topic_details(topic: dict) -> None:
    """Display full source trend details for the selected topic."""
    st.markdown("---")
    st.markdown(f"### {topic.get('topic_name', 'Untitled')}")

    cols = st.columns(4)
    cols[0].metric("Category", topic.get("category", "N/A"))
    confidence = topic.get("category_confidence", 0)
    cols[1].metric("Confidence", f"{confidence:.0%}")
    cols[2].metric("Trend Score", f"{topic.get('trend_score', 0):.1f}")
    cols[3].metric("Videos", str(topic.get("video_count", 0)))

    # Finance context
    finance_ctx = topic.get("finance_context")
    if finance_ctx:
        with st.expander("Finance Context"):
            st.json(finance_ctx)

    # Top videos / source trends
    top_videos = topic.get("top_videos", [])
    if top_videos:
        with st.expander(f"Source Trends ({len(top_videos)} videos)"):
            for video in top_videos:
                if isinstance(video, dict):
                    title = video.get("title", "Untitled")
                    views = video.get("view_count", "N/A")
                    st.markdown(f"- **{title}** — {views} views")
                else:
                    st.markdown(f"- {video}")

    fetched_at = topic.get("fetched_at")
    if fetched_at:
        st.caption(f"Fetched at: {fetched_at}")
