"""Unit tests for the PDF Forensic effect template."""

from __future__ import annotations

import ast
import os
import tempfile
from unittest.mock import patch

import pytest

from effects_catalog.templates.pdf_forensic import (
    InvalidPDFPathError,
    PageRangeError,
    TextNotFoundError,
    generate,
    validate_instruction,
)


# ── generate() tests ────────────────────────────────────────


class TestGenerate:
    """Tests for the Manim code generation."""

    def test_generates_valid_python(self):
        instruction = {
            "data": {
                "pdf_path": "/tmp/report.pdf",
                "page_number": 1,
                "highlights": [
                    {"bbox": {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.05}, "style": "rectangle"}
                ],
            },
            "title": "Annual Report",
        }
        code = generate(instruction)
        # Must be parseable Python
        ast.parse(code)

    def test_contains_scene_class(self):
        code = generate({"data": {"pdf_path": "x.pdf", "page_number": 1, "highlights": []}})
        assert "class PDFForensicScene(MovingCameraScene)" in code

    def test_contains_moving_camera_scene(self):
        code = generate({"data": {"pdf_path": "x.pdf", "page_number": 1, "highlights": []}})
        assert "MovingCameraScene" in code

    def test_highlight_styles(self):
        """All three highlight styles should appear in generated code."""
        for style in ("rectangle", "underline", "margin_annotation"):
            instruction = {
                "data": {
                    "pdf_path": "report.pdf",
                    "page_number": 1,
                    "highlights": [
                        {"bbox": {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.05}, "style": style}
                    ],
                },
            }
            code = generate(instruction)
            ast.parse(code)
            assert style in code

    def test_multiple_highlights_sequential(self):
        """Multiple highlights should produce code with Restore between them."""
        instruction = {
            "data": {
                "pdf_path": "report.pdf",
                "page_number": 1,
                "highlights": [
                    {"bbox": {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.05}},
                    {"bbox": {"x": 0.5, "y": 0.6, "width": 0.2, "height": 0.04}},
                ],
            },
        }
        code = generate(instruction)
        ast.parse(code)
        # Both highlights are embedded in the generated code
        assert "Restore" in code

    def test_empty_highlights(self):
        code = generate({"data": {"pdf_path": "x.pdf", "page_number": 1, "highlights": []}})
        ast.parse(code)

    def test_title_included(self):
        code = generate({"data": {"pdf_path": "x.pdf", "page_number": 1, "highlights": []}, "title": "Q4 Earnings"})
        assert "Q4 Earnings" in code

    def test_custom_color_and_opacity(self):
        instruction = {
            "data": {
                "pdf_path": "report.pdf",
                "page_number": 2,
                "highlights": [
                    {"bbox": {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.05}, "color": "#00FF00", "opacity": 0.5}
                ],
            },
        }
        code = generate(instruction)
        assert "#00FF00" in code
        assert "0.5" in code


# ── validate_instruction() tests ─────────────────────────────


class TestValidateInstruction:
    """Tests for input validation."""

    def test_empty_pdf_path_raises(self):
        with pytest.raises(InvalidPDFPathError):
            validate_instruction({"pdf_path": "", "page_number": 1, "highlights": []})

    def test_missing_pdf_file_raises(self):
        with pytest.raises(InvalidPDFPathError):
            validate_instruction({"pdf_path": "/nonexistent/file.pdf", "page_number": 1, "highlights": []})

    def test_negative_page_number_raises(self):
        """Page number < 1 should raise PageRangeError."""
        # Create a temp file to pass the file-exists check
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF-1.4 fake")
            tmp_path = f.name
        try:
            with pytest.raises(PageRangeError):
                validate_instruction({"pdf_path": tmp_path, "page_number": 0, "highlights": []})
        finally:
            os.unlink(tmp_path)

    def test_valid_pdf_path_no_error(self):
        """A real file with page_number=1 should not raise (pdfinfo may not be installed)."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF-1.4 fake")
            tmp_path = f.name
        try:
            # Should not raise — pdfinfo may not be installed, so page count check is skipped
            validate_instruction({"pdf_path": tmp_path, "page_number": 1, "highlights": []})
        finally:
            os.unlink(tmp_path)

    def test_page_out_of_range_with_pdfinfo(self):
        """When pdfinfo reports page count, out-of-range page should raise."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF-1.4 fake")
            tmp_path = f.name
        try:
            mock_result = type("Result", (), {"returncode": 0, "stdout": "Pages:          3\n", "stderr": ""})()
            with patch("subprocess.run", return_value=mock_result):
                with pytest.raises(PageRangeError) as exc_info:
                    validate_instruction({"pdf_path": tmp_path, "page_number": 5, "highlights": []})
                assert exc_info.value.page == 5
                assert exc_info.value.max_pages == 3
        finally:
            os.unlink(tmp_path)

    def test_text_search_not_found_raises(self):
        """text_search that can't be resolved should raise TextNotFoundError."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF-1.4 fake")
            tmp_path = f.name
        try:
            # Mock _resolve_text_search to return None
            with patch("effects_catalog.templates.pdf_forensic._resolve_text_search", return_value=None):
                with pytest.raises(TextNotFoundError) as exc_info:
                    validate_instruction({
                        "pdf_path": tmp_path,
                        "page_number": 1,
                        "highlights": [{"text_search": "nonexistent text"}],
                    })
                assert exc_info.value.text == "nonexistent text"
                assert exc_info.value.page == 1
        finally:
            os.unlink(tmp_path)

    def test_text_search_resolved_to_bbox(self):
        """When text_search resolves, bbox should be populated on the highlight."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF-1.4 fake")
            tmp_path = f.name
        try:
            fake_bbox = {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.04}
            with patch("effects_catalog.templates.pdf_forensic._resolve_text_search", return_value=fake_bbox):
                highlights = [{"text_search": "Revenue"}]
                validate_instruction({
                    "pdf_path": tmp_path,
                    "page_number": 1,
                    "highlights": highlights,
                })
                assert highlights[0]["bbox"] == fake_bbox
        finally:
            os.unlink(tmp_path)

    def test_highlight_with_bbox_skips_text_search(self):
        """Highlights that already have bbox should not trigger text search."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF-1.4 fake")
            tmp_path = f.name
        try:
            highlights = [
                {"bbox": {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.05}, "text_search": "Revenue"}
            ]
            # Should not raise even without mocking _resolve_text_search
            validate_instruction({
                "pdf_path": tmp_path,
                "page_number": 1,
                "highlights": highlights,
            })
        finally:
            os.unlink(tmp_path)
