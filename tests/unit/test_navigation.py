"""Unit tests for pipeline_ui.navigation module."""

import pytest

from pipeline_ui.navigation import PipelineStep, STEP_LABELS, can_advance, go_to_step
from pipeline_ui.session_state import PipelineData


# ---------------------------------------------------------------------------
# can_advance tests
# ---------------------------------------------------------------------------


class TestCanAdvance:
    """Tests for the can_advance pure logic function."""

    def test_search_false_when_no_results(self):
        data = PipelineData()
        assert can_advance(PipelineStep.SEARCH, data) is False

    def test_search_true_when_results_present(self):
        data = PipelineData(search_results={"topics": []})
        assert can_advance(PipelineStep.SEARCH, data) is True

    def test_select_topic_false_when_no_selection(self):
        data = PipelineData()
        assert can_advance(PipelineStep.SELECT_TOPIC, data) is False

    def test_select_topic_true_when_topic_selected(self):
        data = PipelineData(selected_topic={"topic_name": "AI Trends"})
        assert can_advance(PipelineStep.SELECT_TOPIC, data) is True

    def test_script_input_false_when_empty(self):
        data = PipelineData(raw_script="")
        assert can_advance(PipelineStep.SCRIPT_INPUT, data) is False

    def test_script_input_false_when_whitespace_only(self):
        data = PipelineData(raw_script="   \n\t  ")
        assert can_advance(PipelineStep.SCRIPT_INPUT, data) is False

    def test_script_input_true_when_has_content(self):
        data = PipelineData(raw_script="Hello world script")
        assert can_advance(PipelineStep.SCRIPT_INPUT, data) is True

    def test_convert_false_when_no_video_script(self):
        data = PipelineData()
        assert can_advance(PipelineStep.CONVERT, data) is False

    def test_convert_true_when_video_script_present(self):
        data = PipelineData(video_script={"title": "Test"})
        assert can_advance(PipelineStep.CONVERT, data) is True

    def test_review_true_when_video_script_present(self):
        data = PipelineData(
            search_results={"topics": []},
            selected_topic={"topic_name": "X"},
            raw_script="script",
            video_script={"title": "T"},
        )
        assert can_advance(PipelineStep.REVIEW, data) is True

    def test_review_false_when_no_video_script(self):
        data = PipelineData(
            search_results={"topics": []},
            selected_topic={"topic_name": "X"},
            raw_script="script",
        )
        assert can_advance(PipelineStep.REVIEW, data) is False

    def test_synthesize_false_when_no_manifest(self):
        data = PipelineData()
        assert can_advance(PipelineStep.SYNTHESIZE, data) is False

    def test_synthesize_true_when_manifest_present(self):
        data = PipelineData(audio_manifest={"entries": []})
        assert can_advance(PipelineStep.SYNTHESIZE, data) is True

    def test_render_always_false(self):
        data = PipelineData(
            audio_manifest={"entries": []},
            render_result={"total": 1},
        )
        assert can_advance(PipelineStep.RENDER, data) is False


# ---------------------------------------------------------------------------
# go_to_step tests
# ---------------------------------------------------------------------------


class TestGoToStep:
    """Tests for the go_to_step navigation function."""

    def test_succeeds_for_step_within_completed(self):
        data = PipelineData(current_step=3, max_completed_step=3)
        assert go_to_step(1, data) is True
        assert data.current_step == 1

    def test_succeeds_for_next_uncompleted_step(self):
        """Can navigate to max_completed_step + 1."""
        data = PipelineData(current_step=0, max_completed_step=1)
        assert go_to_step(2, data) is True
        assert data.current_step == 2

    def test_fails_for_step_beyond_allowed(self):
        data = PipelineData(current_step=0, max_completed_step=0)
        assert go_to_step(2, data) is False
        assert data.current_step == 0  # unchanged

    def test_fails_for_negative_step(self):
        data = PipelineData(current_step=0, max_completed_step=2)
        assert go_to_step(-1, data) is False

    def test_fails_for_step_beyond_render(self):
        data = PipelineData(current_step=0, max_completed_step=6)
        assert go_to_step(7, data) is False

    def test_navigate_to_step_zero_always_allowed(self):
        data = PipelineData(current_step=2, max_completed_step=-1)
        assert go_to_step(0, data) is True
        assert data.current_step == 0


# ---------------------------------------------------------------------------
# STEP_LABELS sanity check
# ---------------------------------------------------------------------------


def test_step_labels_length_matches_enum():
    assert len(STEP_LABELS) == len(PipelineStep)
