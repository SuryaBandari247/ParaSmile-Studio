"""Unit tests for stock footage integration in AssetOrchestrator."""

import os
from unittest.mock import patch, MagicMock

import pytest

from asset_orchestrator.orchestrator import AssetOrchestrator, STOCK_SCENE_TYPES


class TestStockSceneRouting:
    """Test that stock scene types are routed correctly."""

    def test_stock_types_defined(self):
        assert "stock_video" in STOCK_SCENE_TYPES
        assert "stock_with_text" in STOCK_SCENE_TYPES
        assert "stock_with_stat" in STOCK_SCENE_TYPES
        assert "stock_quote" in STOCK_SCENE_TYPES

    @patch("asset_orchestrator.orchestrator.AssetOrchestrator._process_stock_instruction")
    def test_stock_type_routes_to_stock_pipeline(self, mock_stock, tmp_path):
        mock_stock.return_value = {"status": "success", "output_path": "/fake.mp4"}
        orch = AssetOrchestrator()
        instruction = {
            "type": "stock_with_text",
            "title": "Test",
            "data": {"heading": "Hello", "body": "World"},
        }
        result = orch.process_instruction(instruction)
        assert result["status"] == "success"
        mock_stock.assert_called_once()

    def test_manim_type_does_not_route_to_stock(self):
        orch = AssetOrchestrator()
        # bar_chart should NOT be in stock types
        assert "bar_chart" not in STOCK_SCENE_TYPES


class TestProcessStockInstruction:
    """Test _process_stock_instruction method."""

    @patch("asset_orchestrator.ffmpeg_compositor.subprocess.run")
    def test_fallback_to_solid_background_when_no_pexels(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0)
        orch = AssetOrchestrator()
        orch._pexels = None  # No Pexels client

        instruction = {
            "type": "stock_with_text",
            "title": "Test",
            "data": {"heading": "Hello", "body": "World"},
        }
        result = orch._process_stock_instruction(instruction)
        assert result["status"] == "success"
        assert result["output_path"].endswith(".mp4")

    @patch("asset_orchestrator.ffmpeg_compositor.subprocess.run")
    def test_stock_with_stat_processes(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0)
        orch = AssetOrchestrator()
        orch._pexels = None

        instruction = {
            "type": "stock_with_stat",
            "title": "Tax Trap",
            "data": {"value": "$10,000", "label": "TAX BILL", "subtitle": "2026"},
        }
        result = orch._process_stock_instruction(instruction)
        assert result["status"] == "success"

    @patch("asset_orchestrator.ffmpeg_compositor.subprocess.run")
    def test_stock_quote_processes(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0)
        orch = AssetOrchestrator()
        orch._pexels = None

        instruction = {
            "type": "stock_quote",
            "title": "CTA",
            "data": {"quote": "Ask your question", "attribution": "Reddit"},
        }
        result = orch._process_stock_instruction(instruction)
        assert result["status"] == "success"

    @patch("asset_orchestrator.ffmpeg_compositor.subprocess.run")
    def test_stock_video_processes(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0)
        orch = AssetOrchestrator()
        orch._pexels = None

        instruction = {
            "type": "stock_video",
            "title": "Background",
            "data": {"keywords": ["abstract"]},
        }
        result = orch._process_stock_instruction(instruction)
        assert result["status"] == "success"

    @patch("asset_orchestrator.ffmpeg_compositor.subprocess.run")
    def test_uses_explicit_keywords(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0)
        mock_pexels = MagicMock()
        mock_pexels.search_and_download.return_value = None
        mock_pexels.search_and_download_multiple.return_value = []

        orch = AssetOrchestrator()
        orch._pexels = mock_pexels

        instruction = {
            "type": "stock_with_text",
            "title": "Test",
            "data": {"heading": "H", "keywords": ["taxes", "office"]},
        }
        orch._process_stock_instruction(instruction)
        mock_pexels.search_and_download_multiple.assert_called_once()
        call_query = mock_pexels.search_and_download_multiple.call_args[0][0]
        assert "taxes" in call_query

    @patch("asset_orchestrator.ffmpeg_compositor.subprocess.run")
    def test_extracts_keywords_from_narration(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0)
        mock_pexels = MagicMock()
        mock_pexels.search_and_download.return_value = None
        mock_pexels.search_and_download_multiple.return_value = []
        mock_extractor = MagicMock()
        mock_extractor.extract.return_value = ["taxes", "money"]

        orch = AssetOrchestrator()
        orch._pexels = mock_pexels
        orch._keyword_extractor = mock_extractor

        instruction = {
            "type": "stock_with_text",
            "title": "Tax",
            "data": {"heading": "H"},
        }
        orch._process_stock_instruction(
            instruction, narration_text="People worried about taxes and money"
        )
        mock_extractor.extract.assert_called_once()


class TestMixedBatch:
    """Test mixed Manim + stock scenes in same batch."""

    @patch("asset_orchestrator.ffmpeg_compositor.subprocess.run")
    @patch("asset_orchestrator.renderer.Renderer.render")
    def test_mixed_batch_processes_both(self, mock_render, mock_ffmpeg_run, tmp_path):
        mock_render.return_value = "/fake/manim_output.mp4"
        mock_ffmpeg_run.return_value = MagicMock(returncode=0)

        orch = AssetOrchestrator()
        orch._pexels = None

        instructions = [
            {"type": "stock_with_text", "title": "Stock", "data": {"heading": "H"}},
            {"type": "text_overlay", "title": "Manim", "data": {"text": "Hello"}},
        ]
        result = orch.process_batch(instructions)
        assert result.total == 2
        # At least one should succeed (stock with fallback)
        assert result.succeeded >= 1
