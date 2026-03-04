"""
Shared pytest fixtures for research_agent tests.

This module provides common fixtures used across unit and property-based tests.
"""

import pytest
import tempfile
import shutil
import logging
from pathlib import Path


@pytest.fixture(autouse=True)
def reset_logging():
    """
    Reset logging configuration before each test.
    
    This ensures that caplog can properly capture log records
    by removing any handlers that might have been added by previous tests.
    """
    loggers_to_reset = ['research_agent', 'asset_orchestrator']
    saved = {}

    for name in loggers_to_reset:
        logger = logging.getLogger(name)
        saved[name] = {
            'handlers': logger.handlers[:],
            'level': logger.level,
            'propagate': logger.propagate,
        }
        logger.handlers = []
        logger.setLevel(logging.DEBUG)
        logger.propagate = True

    yield

    for name, state in saved.items():
        logger = logging.getLogger(name)
        logger.handlers = state['handlers']
        logger.level = state['level']
        logger.propagate = state['propagate']


@pytest.fixture
def temp_cache_dir():
    """
    Provide a temporary directory for cache files during tests.
    
    Yields:
        Path: Temporary directory path
        
    Cleanup:
        Automatically removes the directory after test completion
    """
    temp_dir = tempfile.mkdtemp()
    try:
        yield Path(temp_dir)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def quota_state_file(temp_cache_dir):
    """
    Provide a temporary quota state file path.
    
    Args:
        temp_cache_dir: Temporary directory fixture
        
    Returns:
        str: Path to quota state file
    """
    return str(temp_cache_dir / "quota_state.json")


# ---------------------------------------------------------------------------
# Asset Orchestrator fixtures
# ---------------------------------------------------------------------------

import subprocess
from unittest.mock import patch, MagicMock


@pytest.fixture
def sample_bar_chart_instruction():
    """Sample bar chart Visual_Instruction dict."""
    return {
        "type": "bar_chart",
        "title": "Test Chart",
        "data": {"labels": ["A", "B", "C"], "values": [10, 20, 30]},
    }


@pytest.fixture
def sample_line_chart_instruction():
    """Sample line chart Visual_Instruction dict."""
    return {
        "type": "line_chart",
        "title": "Test Line Chart",
        "data": {"labels": ["Jan", "Feb", "Mar"], "values": [5, 15, 10]},
    }


@pytest.fixture
def sample_pie_chart_instruction():
    """Sample pie chart Visual_Instruction dict."""
    return {
        "type": "pie_chart",
        "title": "Test Pie Chart",
        "data": {"labels": ["X", "Y", "Z"], "values": [40, 35, 25]},
    }


@pytest.fixture
def sample_code_snippet_instruction():
    """Sample code snippet Visual_Instruction dict."""
    return {
        "type": "code_snippet",
        "title": "Test Code",
        "data": {"code": "print('hello')", "language": "python"},
    }


@pytest.fixture
def sample_text_overlay_instruction():
    """Sample text overlay Visual_Instruction dict."""
    return {
        "type": "text_overlay",
        "title": "Test Overlay",
        "data": {"text": "Hello World"},
    }


@pytest.fixture
def temp_output_dir():
    """Provide a temporary output directory, cleaned up after the test."""
    tmp = tempfile.mkdtemp()
    try:
        yield Path(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def mock_manim_subprocess():
    """Patch subprocess.run to simulate a successful Manim render."""
    result = subprocess.CompletedProcess(
        args=["manim", "render"],
        returncode=0,
        stdout="Manim render complete",
        stderr="",
    )
    with patch("subprocess.run", return_value=result) as mock_run:
        yield mock_run


@pytest.fixture
def mock_ffmpeg_subprocess():
    """Patch subprocess.run to simulate a successful FFmpeg compose."""
    result = subprocess.CompletedProcess(
        args=["ffmpeg", "-i", "input.mp4"],
        returncode=0,
        stdout="FFmpeg compose complete",
        stderr="",
    )
    with patch("subprocess.run", return_value=result) as mock_run:
        yield mock_run


@pytest.fixture
def mock_ffmpeg_on_path():
    """Patch shutil.which so that ffmpeg appears to be installed."""
    with patch("shutil.which", return_value="/usr/local/bin/ffmpeg") as mock_which:
        yield mock_which
