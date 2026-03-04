"""Unit tests for pipeline_ui.session_state module."""

from unittest.mock import patch

from pipeline_ui.session_state import PipelineData, clear_session_state, get_pipeline, init_session_state


class TestClearSessionState:
    """Tests for clear_session_state."""

    def test_produces_default_pipeline_data(self):
        mock_state = {"pipeline": PipelineData(current_step=3, max_completed_step=2, raw_script="old")}
        with patch("pipeline_ui.session_state.st") as mock_st:
            mock_st.session_state = mock_state
            clear_session_state()
            result = mock_state["pipeline"]
        assert result == PipelineData()

    def test_resets_all_fields(self):
        mock_state = {
            "pipeline": PipelineData(
                current_step=4,
                max_completed_step=3,
                search_results={"topics": []},
                selected_topic={"name": "x"},
                raw_script="some script",
                parsed_documents=[{"filename": "a.txt"}],
                video_script={"title": "v"},
                conversion_metadata={"model": "gpt-4o-mini"},
            )
        }
        with patch("pipeline_ui.session_state.st") as mock_st:
            mock_st.session_state = mock_state
            clear_session_state()
            result = mock_state["pipeline"]
        assert result.current_step == 0
        assert result.max_completed_step == -1
        assert result.search_results is None
        assert result.selected_topic is None
        assert result.raw_script == ""
        assert result.parsed_documents == []
        assert result.video_script is None
        assert result.conversion_metadata is None


class TestInitSessionState:
    """Tests for init_session_state."""

    def test_creates_default_when_absent(self):
        mock_state = {}
        with patch("pipeline_ui.session_state.st") as mock_st:
            mock_st.session_state = mock_state
            init_session_state()
        assert "pipeline" in mock_state
        assert mock_state["pipeline"] == PipelineData()

    def test_idempotent_does_not_overwrite(self):
        existing = PipelineData(current_step=2, raw_script="keep me")
        mock_state = {"pipeline": existing}
        with patch("pipeline_ui.session_state.st") as mock_st:
            mock_st.session_state = mock_state
            init_session_state()
            init_session_state()  # second call
        assert mock_state["pipeline"] is existing
        assert mock_state["pipeline"].raw_script == "keep me"


class TestGetPipeline:
    """Tests for get_pipeline."""

    def test_returns_pipeline_data_from_state(self):
        expected = PipelineData(current_step=1, search_results={"topics": [1, 2]})
        mock_state = {"pipeline": expected}
        with patch("pipeline_ui.session_state.st") as mock_st:
            mock_st.session_state = mock_state
            result = get_pipeline()
        assert result is expected
