"""
Unit tests for logging functionality.

Tests logging setup, structured logging, log formatting, and helper functions
for API requests, errors, and quota warnings.
"""

import pytest
import logging
import logging.handlers
import json
import tempfile
from pathlib import Path
from io import StringIO

from research_agent.logger import (
    setup_logging,
    get_logger,
    log_api_request,
    log_error_with_context,
    log_quota_warning,
    log_trend_analysis_results,
    log_cache_operation,
    StructuredFormatter,
    HumanReadableFormatter
)


class TestLoggingSetup:
    """Test suite for logging setup and configuration."""
    
    def test_setup_logging_with_default_level(self):
        """Test that setup_logging configures logger with default INFO level."""
        logger = setup_logging()
        
        assert logger.name == "research_agent"
        assert logger.level == logging.INFO
        assert len(logger.handlers) > 0
    
    def test_setup_logging_with_custom_level(self):
        """Test that setup_logging accepts custom log levels."""
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            logger = setup_logging(log_level=level)
            assert logger.level == getattr(logging, level)
    
    def test_setup_logging_with_structured_output(self):
        """Test that structured logging uses StructuredFormatter."""
        logger = setup_logging(structured=True)
        
        # Check that at least one handler uses StructuredFormatter
        has_structured_formatter = any(
            isinstance(handler.formatter, StructuredFormatter)
            for handler in logger.handlers
        )
        assert has_structured_formatter
    
    def test_setup_logging_with_human_readable_output(self):
        """Test that non-structured logging uses HumanReadableFormatter."""
        logger = setup_logging(structured=False)
        
        # Check that at least one handler uses HumanReadableFormatter
        has_human_formatter = any(
            isinstance(handler.formatter, HumanReadableFormatter)
            for handler in logger.handlers
        )
        assert has_human_formatter
    
    def test_setup_logging_with_log_file(self):
        """Test that setup_logging creates file handler when log_file specified."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            logger = setup_logging(log_file=str(log_file))
            
            # Log a message
            logger.info("Test message")
            
            # Verify file was created and contains the message
            assert log_file.exists()
            content = log_file.read_text()
            assert "Test message" in content
    
    def test_get_logger_returns_component_logger(self):
        """Test that get_logger returns logger with correct component name."""
        logger = get_logger("api_client")
        
        assert logger.name == "research_agent.api_client"
    
    def test_logger_does_not_propagate_to_root(self):
        """Test that research_agent logger doesn't propagate to root logger."""
        logger = setup_logging()
        
        assert logger.propagate is False


class TestStructuredFormatter:
    """Test suite for StructuredFormatter."""
    
    def test_structured_formatter_outputs_json(self):
        """Test that StructuredFormatter outputs valid JSON."""
        formatter = StructuredFormatter()
        
        # Create a log record
        logger = logging.getLogger("test")
        record = logger.makeRecord(
            "test", logging.INFO, "test.py", 1, "Test message", (), None
        )
        
        output = formatter.format(record)
        
        # Should be valid JSON
        log_data = json.loads(output)
        assert log_data["level"] == "INFO"
        assert log_data["message"] == "Test message"
        assert log_data["component"] == "test"
        assert "timestamp" in log_data
    
    def test_structured_formatter_includes_custom_fields(self):
        """Test that StructuredFormatter includes custom fields from extra."""
        formatter = StructuredFormatter()
        
        logger = logging.getLogger("test")
        record = logger.makeRecord(
            "test", logging.INFO, "test.py", 1, "API request", (), None,
            extra={
                "operation": "search_videos",
                "quota_cost": 100,
                "quota_remaining": 9900,
                "duration_ms": 250
            }
        )
        
        output = formatter.format(record)
        log_data = json.loads(output)
        
        assert log_data["operation"] == "search_videos"
        assert log_data["quota_cost"] == 100
        assert log_data["quota_remaining"] == 9900
        assert log_data["duration_ms"] == 250
    
    def test_structured_formatter_includes_exception_info(self):
        """Test that StructuredFormatter includes exception information."""
        formatter = StructuredFormatter()
        
        logger = logging.getLogger("test")
        
        try:
            raise ValueError("Test error")
        except ValueError:
            import sys
            record = logger.makeRecord(
                "test", logging.ERROR, "test.py", 1, "Error occurred", (), 
                exc_info=sys.exc_info()
            )
        
        output = formatter.format(record)
        log_data = json.loads(output)
        
        assert "exception" in log_data
        assert "ValueError: Test error" in log_data["exception"]


class TestHumanReadableFormatter:
    """Test suite for HumanReadableFormatter."""
    
    def test_human_readable_formatter_output_format(self):
        """Test that HumanReadableFormatter produces readable output."""
        formatter = HumanReadableFormatter()
        
        logger = logging.getLogger("test")
        record = logger.makeRecord(
            "test", logging.INFO, "test.py", 1, "Test message", (), None
        )
        
        output = formatter.format(record)
        
        # Should contain timestamp, level, component, and message
        assert "[INFO]" in output
        assert "[test]" in output
        assert "Test message" in output
    
    def test_human_readable_formatter_includes_custom_fields(self):
        """Test that HumanReadableFormatter includes custom fields."""
        formatter = HumanReadableFormatter()
        
        logger = logging.getLogger("test")
        record = logger.makeRecord(
            "test", logging.INFO, "test.py", 1, "API request", (), None,
            extra={
                "operation": "search_videos",
                "quota_cost": 100,
                "quota_remaining": 9900
            }
        )
        
        output = formatter.format(record)
        
        assert "operation=search_videos" in output
        assert "quota_cost=100" in output
        assert "quota_remaining=9900" in output


class TestLogHelperFunctions:
    """Test suite for log helper functions."""
    
    def test_log_api_request_logs_with_correct_fields(self):
        """Test that log_api_request logs with all required fields."""
        logger = get_logger("test")
        logger.setLevel(logging.DEBUG)
        
        # Create a handler to capture logs
        handler = logging.handlers.MemoryHandler(capacity=100)
        logger.addHandler(handler)
        
        try:
            log_api_request(
                logger=logger,
                endpoint="https://youtube.googleapis.com/youtube/v3/search",
                quota_cost=100,
                quota_remaining=9900,
                operation="search_videos",
                duration_ms=250,
                result_count=50
            )
            
            handler.flush()
            assert len(handler.buffer) == 1
            record = handler.buffer[0]
            assert record.levelname == "INFO"
            assert "search" in record.getMessage()
            assert record.operation == "search_videos"
            assert record.quota_cost == 100
            assert record.quota_remaining == 9900
            assert record.duration_ms == 250
            assert record.result_count == 50
        finally:
            logger.removeHandler(handler)
    
    def test_log_error_with_context_includes_stack_trace(self):
        """Test that log_error_with_context includes full stack trace."""
        logger = get_logger("test")
        logger.setLevel(logging.DEBUG)
        
        handler = logging.handlers.MemoryHandler(capacity=100)
        logger.addHandler(handler)
        
        try:
            try:
                raise ValueError("Test error")
            except ValueError as e:
                log_error_with_context(
                    logger=logger,
                    error=e,
                    operation="test_operation",
                    context={"video_id": "abc123", "attempt": 1}
                )
            
            handler.flush()
            assert len(handler.buffer) == 1
            record = handler.buffer[0]
            assert record.levelname == "ERROR"
            assert "Test error" in record.getMessage()
            assert record.operation == "test_operation"
            assert record.error_type == "ValueError"
            assert "video_id=abc123" in record.getMessage()
            assert "attempt=1" in record.getMessage()
            assert hasattr(record, "stack_trace")
        finally:
            logger.removeHandler(handler)
    
    def test_log_quota_warning_logs_at_warning_level(self):
        """Test that log_quota_warning logs at WARNING level."""
        logger = get_logger("test")
        logger.setLevel(logging.DEBUG)
        
        handler = logging.handlers.MemoryHandler(capacity=100)
        logger.addHandler(handler)
        
        try:
            log_quota_warning(
                logger=logger,
                consumed=8500,
                remaining=1500,
                daily_limit=10000,
                percentage=85.0
            )
            
            handler.flush()
            assert len(handler.buffer) == 1
            record = handler.buffer[0]
            assert record.levelname == "WARNING"
            assert "85.0%" in record.getMessage()
            assert "8500" in record.getMessage()
            assert "1500 remaining" in record.getMessage()
        finally:
            logger.removeHandler(handler)
    
    def test_log_trend_analysis_results_logs_summary(self):
        """Test that log_trend_analysis_results logs analysis summary."""
        logger = get_logger("test")
        logger.setLevel(logging.DEBUG)
        
        handler = logging.handlers.MemoryHandler(capacity=100)
        logger.addHandler(handler)
        
        try:
            log_trend_analysis_results(
                logger=logger,
                topic_count=15,
                average_score=67.5,
                total_videos=150
            )
            
            handler.flush()
            assert len(handler.buffer) == 1
            record = handler.buffer[0]
            assert record.levelname == "INFO"
            msg = record.getMessage()
            assert "15 topics" in msg
            assert "67.5" in msg or "67.50" in msg
            assert "150 videos" in msg
        finally:
            logger.removeHandler(handler)
    
    def test_log_cache_operation_logs_cache_hit(self):
        """Test that log_cache_operation logs cache hits."""
        logger = get_logger("test")
        logger.setLevel(logging.DEBUG)
        
        handler = logging.handlers.MemoryHandler(capacity=100)
        logger.addHandler(handler)
        
        try:
            log_cache_operation(
                logger=logger,
                operation="cache_get",
                cache_key="test_key",
                hit=True,
                age_hours=2.5
            )
            
            handler.flush()
            assert len(handler.buffer) == 1
            record = handler.buffer[0]
            assert record.levelname == "DEBUG"
            msg = record.getMessage()
            assert "Cache hit" in msg
            assert "test_key" in msg
            assert "2.5h" in msg
        finally:
            logger.removeHandler(handler)
    
    def test_log_cache_operation_logs_cache_miss(self):
        """Test that log_cache_operation logs cache misses."""
        logger = get_logger("test")
        logger.setLevel(logging.DEBUG)
        
        handler = logging.handlers.MemoryHandler(capacity=100)
        logger.addHandler(handler)
        
        try:
            log_cache_operation(
                logger=logger,
                operation="cache_get",
                cache_key="test_key",
                hit=False
            )
            
            handler.flush()
            assert len(handler.buffer) == 1
            record = handler.buffer[0]
            assert record.levelname == "DEBUG"
            msg = record.getMessage()
            assert "Cache miss" in msg
            assert "test_key" in msg
        finally:
            logger.removeHandler(handler)
    
    def test_log_api_request_without_optional_fields(self):
        """Test that log_api_request works without optional fields."""
        logger = get_logger("test")
        logger.setLevel(logging.DEBUG)
        
        handler = logging.handlers.MemoryHandler(capacity=100)
        logger.addHandler(handler)
        
        try:
            log_api_request(
                logger=logger,
                endpoint="https://youtube.googleapis.com/youtube/v3/videos",
                quota_cost=1,
                quota_remaining=9999,
                operation="get_video_details"
            )
            
            handler.flush()
            assert len(handler.buffer) == 1
            record = handler.buffer[0]
            assert record.levelname == "INFO"
            assert record.quota_cost == 1
            assert not hasattr(record, "duration_ms")
            assert not hasattr(record, "result_count")
        finally:
            logger.removeHandler(handler)


class TestLoggingIntegration:
    """Integration tests for logging functionality."""
    
    def test_structured_logging_end_to_end(self):
        """Test structured logging from setup to output."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "structured.log"
            logger = setup_logging(
                log_level="INFO",
                structured=True,
                log_file=str(log_file)
            )
            
            # Log various types of messages
            log_api_request(
                logger=logger,
                endpoint="https://api.example.com/test",
                quota_cost=100,
                quota_remaining=9900,
                operation="test_operation",
                duration_ms=150,
                result_count=25
            )
            
            # Read log file and verify JSON format
            content = log_file.read_text()
            lines = content.strip().split('\n')
            
            for line in lines:
                log_data = json.loads(line)
                assert "timestamp" in log_data
                assert "level" in log_data
                assert "component" in log_data
                assert "message" in log_data
    
    def test_human_readable_logging_end_to_end(self):
        """Test human-readable logging from setup to output."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "readable.log"
            logger = setup_logging(
                log_level="DEBUG",
                structured=False,
                log_file=str(log_file)
            )
            
            # Log various messages
            logger.info("Test info message")
            logger.warning("Test warning message")
            logger.error("Test error message")
            
            # Read log file and verify format
            content = log_file.read_text()
            
            assert "[INFO]" in content
            assert "[WARNING]" in content
            assert "[ERROR]" in content
            assert "Test info message" in content
            assert "Test warning message" in content
            assert "Test error message" in content
