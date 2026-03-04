"""Streamlit entry point for the Pipeline UI.

Handles page configuration, environment variable validation,
session state initialization, and delegates to the current step panel.
"""

import logging
import os
import sys

# Ensure project root is on sys.path so all modules resolve correctly
# when Streamlit is launched via `streamlit run pipeline_ui/app.py`
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import streamlit as st
from dotenv import load_dotenv

from pipeline_ui.navigation import PipelineStep, render_progress_bar
from pipeline_ui.panels.convert_panel import render_convert_panel
from pipeline_ui.panels.render_panel import render_render_panel
from pipeline_ui.panels.review_panel import render_review_panel
from pipeline_ui.panels.script_input_panel import render_script_input_panel
from pipeline_ui.panels.search_panel import render_search_panel
from pipeline_ui.panels.select_topic_panel import render_select_topic_panel
from pipeline_ui.panels.synthesize_panel import render_synthesize_panel
from pipeline_ui.session_state import clear_session_state, get_pipeline, init_session_state
from research_agent.exceptions import AuthenticationError as RAAuthenticationError
from script_generator.exceptions import AuthenticationError as SGAuthenticationError
from script_generator.exceptions import ParseError, ValidationError
from voice_synthesizer.exceptions import AuthenticationError as VSAuthenticationError
from research_agent.exceptions import NetworkError, QuotaExceededError

logger = logging.getLogger("pipeline_ui")

# Key used in session_state to track which script is selected in History
_SELECTED_SCRIPT_KEY = "history_selected_script_id"

REQUIRED_ENV_VARS = ["OPENAI_API_KEY", "YOUTUBE_API_KEY", "ELEVENLABS_API_KEY"]

# Error classification tuples
CONFIGURATION_ERRORS = (RAAuthenticationError, SGAuthenticationError, VSAuthenticationError)
RECOVERABLE_ERRORS = (ParseError, ValidationError, NetworkError, QuotaExceededError)


def validate_env_vars(var_names: list[str]) -> list[str]:
    """Return the names of any environment variables that are not set.

    Pure function — no Streamlit dependency, testable in isolation.
    """
    return [name for name in var_names if not os.environ.get(name)]


def classify_error(exc: Exception) -> str:
    """Classify an exception as 'configuration' or 'recoverable'.

    Returns 'configuration' for AuthenticationError (from either module)
    and missing-env-var scenarios.  Returns 'recoverable' for ParseError,
    ValidationError, NetworkError, and QuotaExceededError.
    Returns 'unknown' for anything else.
    """
    if isinstance(exc, CONFIGURATION_ERRORS):
        return "configuration"
    if isinstance(exc, RECOVERABLE_ERRORS):
        return "recoverable"
    return "unknown"


# ------------------------------------------------------------------
# Panel dispatch
# ------------------------------------------------------------------

_PANEL_DISPATCH = {
    PipelineStep.SEARCH: render_search_panel,
    PipelineStep.SELECT_TOPIC: render_select_topic_panel,
    PipelineStep.SCRIPT_INPUT: render_script_input_panel,
    PipelineStep.CONVERT: render_convert_panel,
    PipelineStep.REVIEW: render_review_panel,
    PipelineStep.SYNTHESIZE: render_synthesize_panel,
    PipelineStep.RENDER: render_render_panel,
}


def _render_current_panel() -> None:
    """Delegate to the panel function for the current pipeline step."""
    pipeline = get_pipeline()
    step = PipelineStep(pipeline.current_step)
    panel_fn = _PANEL_DISPATCH.get(step)
    if panel_fn:
        try:
            panel_fn()
        except CONFIGURATION_ERRORS as exc:
            logger.error("[%s] Configuration error (%s): %s", step.name, type(exc).__name__, exc)
            st.error(f"⚙️ Configuration error: {exc}")
            st.info("Check your `.env` file and restart the application.")
        except RECOVERABLE_ERRORS as exc:
            logger.error("[%s] Recoverable error (%s): %s", step.name, type(exc).__name__, exc)
            st.error(f"❌ {exc}")
            st.info("You can retry or edit your input.")
        except Exception as exc:  # noqa: BLE001
            logger.error("[%s] Unexpected error (%s): %s", step.name, type(exc).__name__, exc)
            st.error(f"An unexpected error occurred: {exc}")


# ------------------------------------------------------------------
# Reset dialog
# ------------------------------------------------------------------


@st.dialog("Start New Pipeline")
def _confirm_reset() -> None:
    """Confirmation dialog before clearing all session state."""
    st.write("This will clear all progress and data. Are you sure?")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Yes, start fresh", key="confirm_reset_yes"):
            clear_session_state()
            st.rerun()
    with col2:
        if st.button("Cancel", key="confirm_reset_cancel"):
            st.rerun()


# ------------------------------------------------------------------
# History sidebar
# ------------------------------------------------------------------


def _render_history_sidebar() -> None:
    """Render the History section in the sidebar.

    Lazily imports ContentStore so the sidebar never crashes even if
    the content_store package or database is unavailable.
    """
    st.sidebar.divider()
    st.sidebar.subheader("History")

    try:
        from content_store import ContentStore
    except Exception:
        st.sidebar.caption("Content store unavailable.")
        return

    # --- Filter controls ---
    keyword = st.sidebar.text_input("Keyword search", key="history_keyword")
    col_start, col_end = st.sidebar.columns(2)
    with col_start:
        start_date = st.sidebar.date_input("From", value=None, key="history_start")
    with col_end:
        end_date = st.sidebar.date_input("To", value=None, key="history_end")
    category = st.sidebar.text_input("Topic category", key="history_category")

    # Build filter kwargs
    filters: dict = {}
    if keyword:
        filters["keyword"] = keyword
    if category:
        filters["category"] = category
    if start_date is not None:
        filters["start_date"] = str(start_date)
    if end_date is not None:
        filters["end_date"] = str(end_date)

    try:
        with ContentStore() as store:
            scripts = store.list_scripts(**filters)
            sessions = store.list_search_sessions()
    except Exception as exc:
        st.sidebar.warning(f"Could not load history: {exc}")
        return

    # --- Script list ---
    st.sidebar.markdown("**Scripts**")
    if not scripts:
        st.sidebar.caption("No scripts found.")
    else:
        for s in scripts:
            label = f"{s['title']}  \n{s.get('created_at', '')[:10]} · {s.get('word_count', 0)}w · {s.get('scene_count', 0)} scenes"
            if st.sidebar.button(label, key=f"hist_script_{s['id']}"):
                st.session_state[_SELECTED_SCRIPT_KEY] = s["id"]
                st.rerun()

    # --- Search session list ---
    st.sidebar.markdown("**Search Sessions**")
    if not sessions:
        st.sidebar.caption("No search sessions found.")
    else:
        for sess in sessions:
            st.sidebar.caption(
                f"{sess.get('query_date', '')[:10]} · {sess.get('topics_found', 0)} topics"
            )

    # --- Script detail + related + link creation ---
    selected_id = st.session_state.get(_SELECTED_SCRIPT_KEY)
    if selected_id is not None:
        _render_script_detail(selected_id)


def _render_script_detail(script_id: int) -> None:
    """Show full script details and related scripts in the sidebar."""
    try:
        from content_store import ContentStore
    except Exception:
        return

    try:
        with ContentStore() as store:
            script = store.get_script(script_id)
            if script is None:
                st.sidebar.warning("Script not found.")
                st.session_state.pop(_SELECTED_SCRIPT_KEY, None)
                return

            related = store.find_related_scripts(script_id)
            all_scripts = store.list_scripts()
    except Exception as exc:
        st.sidebar.warning(f"Could not load script details: {exc}")
        return

    st.sidebar.divider()
    st.sidebar.markdown(f"**{script['title']}**")

    with st.sidebar.expander("Raw Script"):
        st.text(script.get("raw_script", ""))

    with st.sidebar.expander("VideoScript JSON"):
        st.code(script.get("video_script_json", ""), language="json")

    if script.get("selected_topic_json"):
        with st.sidebar.expander("Selected Topic"):
            st.code(script["selected_topic_json"], language="json")

    # --- Related Scripts ---
    st.sidebar.markdown("**Related Scripts**")
    if not related:
        st.sidebar.caption("No related scripts.")
    else:
        for r in related:
            rtype = r.get("relationship_type", "")
            if rtype == "linked":
                st.sidebar.caption(
                    f"🔗 [{r.get('link_type', '')}] {r['title']}"
                    + (f" — {r['note']}" if r.get("note") else "")
                )
            elif rtype == "same_category":
                st.sidebar.caption(f"📂 Same category: {r['title']}")
            elif rtype == "keyword_overlap":
                st.sidebar.caption(f"🔑 Keyword overlap: {r['title']}")

    # --- Link creation ---
    _render_link_creation(script_id, all_scripts)


def _render_link_creation(source_id: int, all_scripts: list[dict]) -> None:
    """Render controls to create a new link from the selected script."""
    st.sidebar.markdown("**Create Link**")

    # Build target options excluding the source script
    targets = {s["id"]: s["title"] for s in all_scripts if s["id"] != source_id}
    if not targets:
        st.sidebar.caption("No other scripts to link to.")
        return

    target_titles = list(targets.values())
    target_ids = list(targets.keys())

    selected_idx = st.sidebar.selectbox(
        "Target script",
        range(len(target_titles)),
        format_func=lambda i: target_titles[i],
        key="link_target_idx",
    )

    link_type = st.sidebar.selectbox(
        "Link type",
        ["continuation", "deep_dive", "see_also", "related"],
        key="link_type",
    )

    note = st.sidebar.text_input("Note (optional)", key="link_note")

    if st.sidebar.button("Create Link", key="create_link_btn"):
        try:
            from content_store import ContentStore

            with ContentStore() as store:
                store.link_scripts(
                    source_id=source_id,
                    target_id=target_ids[selected_idx],
                    link_type=link_type,
                    note=note or None,
                )
            st.sidebar.success("Link created.")
            st.rerun()
        except Exception as exc:
            st.sidebar.warning(f"Link creation failed: {exc}")


# ------------------------------------------------------------------
# Main entry point
# ------------------------------------------------------------------


def main() -> None:
    """Streamlit entry point."""
    st.set_page_config(page_title="Pipeline UI", layout="wide")
    load_dotenv()

    missing = validate_env_vars(REQUIRED_ENV_VARS)
    if missing:
        st.error(f"Missing required environment variables: {', '.join(missing)}")
        st.stop()

    init_session_state()
    render_progress_bar()

    _render_current_panel()

    # Sidebar reset button
    with st.sidebar:
        if st.button("Start New Pipeline", key="reset_pipeline"):
            _confirm_reset()

    _render_history_sidebar()


if __name__ == "__main__":
    main()
