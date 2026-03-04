"""Convert panel — Step 4 of the pipeline.

Concatenates the raw script with extracted document text and invokes
the Script Converter to produce a structured VideoScript.
"""

import logging

import streamlit as st

from pipeline_ui.document_parser import ParsedDocument, concatenate_extracted_text
from pipeline_ui.navigation import PipelineStep, go_to_step
from pipeline_ui.session_state import get_pipeline
from script_generator.converter import ScriptConverter
from script_generator.exceptions import AuthenticationError, ParseError, ValidationError

logger = logging.getLogger("pipeline_ui")


def render_convert_panel() -> None:
    """Step 4: Convert raw script + documents into a VideoScript."""
    pipeline = get_pipeline()

    st.subheader("Convert to VideoScript")

    # Show current script summary
    script_len = len(pipeline.raw_script) if pipeline.raw_script else 0
    doc_count = sum(
        1 for d in pipeline.parsed_documents if d.get("success")
    )
    st.caption(
        f"Script: {script_len} characters | "
        f"Supplementary documents: {doc_count}"
    )

    # Display conversion metadata if a previous conversion succeeded
    if pipeline.conversion_metadata:
        _render_metadata(pipeline.conversion_metadata)

    if st.button("Convert to VideoScript", key="convert_btn"):
        _run_conversion(pipeline)

    # Show existing video_script info if already converted
    if pipeline.video_script and not pipeline.conversion_metadata:
        st.success("VideoScript already generated.")


def _run_conversion(pipeline) -> None:  # noqa: ANN001
    """Build concatenated input, invoke ScriptConverter, handle results."""
    # Build concatenated text
    full_text = pipeline.raw_script or ""

    if pipeline.parsed_documents:
        docs = [
            ParsedDocument(
                filename=d["filename"],
                text=d.get("text", ""),
                char_count=d.get("char_count", 0),
                success=d.get("success", False),
                error=d.get("error"),
            )
            for d in pipeline.parsed_documents
        ]
        extracted = concatenate_extracted_text(docs)
        if extracted:
            full_text += "\n\n--- SUPPLEMENTARY DOCUMENT CONTEXT ---\n" + extracted

    with st.spinner("Converting script via GPT-4o-mini…"):
        try:
            converter = ScriptConverter()
            video_script = converter.convert(full_text)

            pipeline.video_script = video_script
            pipeline.conversion_metadata = {
                "model": converter._config.llm_model,
                "prompt_tokens": None,
                "completion_tokens": None,
            }
            pipeline.max_completed_step = max(
                pipeline.max_completed_step,
                int(PipelineStep.CONVERT),
            )

            st.success("Conversion complete!")

            # Auto-save script to content store
            try:
                from content_store import ContentStore

                with ContentStore() as store:
                    doc_count = sum(
                        1 for d in pipeline.parsed_documents if d.get("success")
                    )
                    script_id = store.save_script(
                        video_script=video_script,
                        raw_script=pipeline.raw_script,
                        selected_topic=pipeline.selected_topic,
                        documents_used=doc_count,
                    )
                st.success(f"Script saved to history (#{script_id})")
            except Exception as exc:
                logger.warning("[Convert] Auto-save failed: %s", exc)
                st.warning(f"Auto-save failed: {exc}")

            _render_metadata(pipeline.conversion_metadata)
            go_to_step(PipelineStep.REVIEW, pipeline)
            st.rerun()

        except (ParseError, ValidationError) as exc:
            logger.error("[Convert] %s: %s", type(exc).__name__, exc)
            st.error(f"Conversion failed: {exc}")
            st.info(
                "Try editing your script in the previous step and retry."
            )
        except AuthenticationError as exc:
            logger.error("[Convert] AuthenticationError: %s", exc)
            st.error(f"⚙️ Configuration error: {exc}")
            st.info(
                "Ensure `OPENAI_API_KEY` is set correctly in your `.env` file "
                "and restart the application."
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("[Convert] Unexpected error: %s", exc)
            st.error(f"Conversion failed: {exc}")
            st.info("You can retry the conversion.")


def _render_metadata(metadata: dict) -> None:
    """Display model name and token counts."""
    model = metadata.get("model", "unknown")
    prompt_tokens = metadata.get("prompt_tokens")
    completion_tokens = metadata.get("completion_tokens")

    parts = [f"Model: {model}"]
    if prompt_tokens is not None:
        parts.append(f"Prompt tokens: {prompt_tokens}")
    if completion_tokens is not None:
        parts.append(f"Completion tokens: {completion_tokens}")

    st.caption(" | ".join(parts))
