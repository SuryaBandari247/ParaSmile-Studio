"""Script input panel — Step 3 of the pipeline.

Provides a text area for pasting raw script text and a file uploader
for supplementary documents (PDF, XLSX, CSV, TXT, MD, DOCX).
"""

import logging

import streamlit as st

from pipeline_ui.document_parser import SUPPORTED_EXTENSIONS, ParsedDocument, parse_files
from pipeline_ui.navigation import PipelineStep, go_to_step
from pipeline_ui.session_state import get_pipeline

logger = logging.getLogger("pipeline_ui")


def render_script_input_panel() -> None:
    """Step 3: Raw script text area and document upload."""
    pipeline = get_pipeline()

    # Context header — show selected topic info
    if pipeline.selected_topic:
        topic_name = pipeline.selected_topic.get("topic_name", "Untitled")
        hook = pipeline.selected_topic.get("hook", "")
        st.subheader(topic_name)
        if hook:
            st.caption(hook)
    else:
        st.subheader("Script Input")

    # Raw script text area
    raw_script = st.text_area(
        "Paste your raw script",
        value=pipeline.raw_script,
        height=300,
        key="script_text_area",
    )
    pipeline.raw_script = raw_script

    # Character count
    st.caption(f"Character count: {len(raw_script)}")

    # File uploader
    st.markdown("---")
    st.markdown("**Upload supporting documents**")
    accepted_exts = sorted(SUPPORTED_EXTENSIONS)
    uploaded_files = st.file_uploader(
        "Upload files (PDF, XLSX, CSV, TXT, MD, DOCX)",
        accept_multiple_files=True,
        type=[ext.lstrip(".") for ext in accepted_exts],
        key="doc_uploader",
    )

    if uploaded_files:
        file_tuples = [(f.name, f.read()) for f in uploaded_files]
        parsed = parse_files(file_tuples)

        # Display warnings for failed parses
        for doc in parsed:
            if not doc.success:
                st.warning(f"Failed to parse **{doc.filename}**: {doc.error}")

        # Display successfully parsed documents
        successful = [doc for doc in parsed if doc.success]
        if successful:
            st.markdown(f"**{len(successful)} document(s) parsed successfully**")
            for doc in successful:
                st.text(f"  {doc.filename} — {doc.char_count} characters")

        # Store serialized parsed documents in pipeline state
        pipeline.parsed_documents = [
            {
                "filename": doc.filename,
                "text": doc.text,
                "char_count": doc.char_count,
                "success": doc.success,
                "error": doc.error,
            }
            for doc in parsed
        ]

    # Advance button — disabled when text area is empty
    st.markdown("---")
    can_proceed = bool(raw_script and raw_script.strip())
    if st.button("Continue to Convert", disabled=not can_proceed, key="advance_script"):
        pipeline.max_completed_step = max(
            pipeline.max_completed_step,
            int(PipelineStep.SCRIPT_INPUT),
        )
        go_to_step(PipelineStep.CONVERT, pipeline)
        st.rerun()

    if not can_proceed:
        st.info("Enter script text above to continue.")
