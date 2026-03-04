"""
Logging configuration and utilities for the Research Agent.

This module provides structured logging with configurable levels, JSON output support,
and helper functions for logging API requests, quota costs, and errors with stack traces.
"""

import logging
import json
import sys
import traceback
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pathlib import Path


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter for structured JSON logging.
    
    Outputs log records as JSON with consistent field names:
    - timestamp: ISO 8601 timestamp
    - level: Log level (DEBUG, INFO, WARNING, ERROR)
    - component: Component/module name
    - operation: Operation being performed
    - message: Log message
    - Additional fields: quota_cost, quota_remaining, duration_ms, etc.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.
        
        Args:
            record: Log record to format
        
        Returns:
            JSON string representation of log record
        """
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "level": record.levelname,
            "component": record.name,
            "message": record.getMessage()
        }
        
        # Add custom fields from extra parameter
        if hasattr(record, "operation"):
            log_data["operation"] = record.operation
        
        if hasattr(record, "quota_cost"):
            log_data["quota_cost"] = record.quota_cost
        
        if hasattr(record, "quota_remaining"):
            log_data["quota_remaining"] = record.quota_remaining
        
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        
        if hasattr(record, "result_count"):
            log_data["result_count"] = record.result_count
        
        if hasattr(record, "error_type"):
            log_data["error_type"] = record.error_type
        
        if hasattr(record, "stack_trace"):
            log_data["stack_trace"] = record.stack_trace
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


class HumanReadableFormatter(logging.Formatter):
    """
    Custom formatter for human-readable logging.
    
    Format: [timestamp] [LEVEL] [component] message (operation: op_name, quota_cost: X)
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as human-readable text.
        
        Args:
            record: Log record to format
        
        Returns:
            Formatted log string
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        base_msg = f"[{timestamp}] [{record.levelname}] [{record.name}] {record.getMessage()}"
        
        # Add custom fields
        extras = []
        if hasattr(record, "operation"):
            extras.append(f"operation={record.operation}")
        if hasattr(record, "quota_cost"):
            extras.append(f"quota_cost={record.quota_cost}")
        if hasattr(record, "quota_remaining"):
            extras.append(f"quota_remaining={record.quota_remaining}")
        if hasattr(record, "duration_ms"):
            extras.append(f"duration_ms={record.duration_ms}")
        if hasattr(record, "result_count"):
            extras.append(f"result_count={record.result_count}")
        
        if extras:
            base_msg += f" ({', '.join(extras)})"
        
        # Add exception info if present
        if record.exc_info:
            base_msg += "\n" + self.formatException(record.exc_info)
        
        return base_msg


def setup_logging(
    log_level: str = "INFO",
    structured: bool = False,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Configure logging for the Research Agent.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        structured: If True, output logs in JSON format
        log_file: Optional path to log file (logs to stdout if None)
    
    Returns:
        Configured logger instance
    """
    # Get root logger for research_agent
    logger = logging.getLogger("research_agent")
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Choose formatter based on structured flag
    if structured:
        formatter = StructuredFormatter()
    else:
        formatter = HumanReadableFormatter()
    
    # Console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        # Create log directory if it doesn't exist
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


def get_logger(component: str) -> logging.Logger:
    """
    Get a logger for a specific component.
    
    Args:
        component: Component name (e.g., "api_client", "analyzer")
    
    Returns:
        Logger instance for the component
    """
    return logging.getLogger(f"research_agent.{component}")


def log_api_request(
    logger: logging.Logger,
    endpoint: str,
    quota_cost: int,
    quota_remaining: int,
    operation: str,
    duration_ms: Optional[int] = None,
    result_count: Optional[int] = None
) -> None:
    """
    Log an API request with quota cost and timing information.
    
    Args:
        logger: Logger instance
        endpoint: API endpoint URL
        quota_cost: API units consumed by this request
        quota_remaining: Remaining API units after this request
        operation: Operation name (e.g., "search_videos", "get_video_details")
        duration_ms: Request duration in milliseconds (optional)
        result_count: Number of results returned (optional)
    """
    extra = {
        "operation": operation,
        "quota_cost": quota_cost,
        "quota_remaining": quota_remaining
    }
    
    if duration_ms is not None:
        extra["duration_ms"] = duration_ms
    
    if result_count is not None:
        extra["result_count"] = result_count
    
    logger.info(
        f"API request to {endpoint}",
        extra=extra
    )


def log_error_with_context(
    logger: logging.Logger,
    error: Exception,
    operation: str,
    context: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log an error with full stack trace and contextual information.
    
    Args:
        logger: Logger instance
        error: Exception that occurred
        operation: Operation being performed when error occurred
        context: Additional context information (optional)
    """
    # Get stack trace
    stack_trace = "".join(traceback.format_exception(
        type(error), error, error.__traceback__
    ))
    
    extra = {
        "operation": operation,
        "error_type": type(error).__name__,
        "stack_trace": stack_trace
    }
    
    # Build context message
    context_msg = ""
    if context:
        context_items = [f"{k}={v}" for k, v in context.items()]
        context_msg = f" (context: {', '.join(context_items)})"
    
    logger.error(
        f"Error in {operation}: {str(error)}{context_msg}",
        extra=extra,
        exc_info=True
    )


def log_quota_warning(
    logger: logging.Logger,
    consumed: int,
    remaining: int,
    daily_limit: int,
    percentage: float
) -> None:
    """
    Log a quota warning when consumption exceeds threshold.
    
    Args:
        logger: Logger instance
        consumed: API units consumed
        remaining: API units remaining
        daily_limit: Daily quota limit
        percentage: Usage percentage
    """
    logger.warning(
        f"API quota at {percentage:.1f}% ({consumed}/{daily_limit} units consumed, {remaining} remaining)",
        extra={
            "operation": "quota_check",
            "quota_cost": 0,
            "quota_remaining": remaining
        }
    )


def log_trend_analysis_results(
    logger: logging.Logger,
    topic_count: int,
    average_score: float,
    total_videos: int,
    operation: str = "analyze_trends"
) -> None:
    """
    Log trend analysis results summary.
    
    Args:
        logger: Logger instance
        topic_count: Number of topics identified
        average_score: Average trend score across all topics
        total_videos: Total number of videos analyzed
        operation: Operation name
    """
    logger.info(
        f"Trend analysis complete: {topic_count} topics identified, "
        f"average score {average_score:.2f}, {total_videos} videos analyzed",
        extra={
            "operation": operation,
            "result_count": topic_count
        }
    )


def log_cache_operation(
    logger: logging.Logger,
    operation: str,
    cache_key: str,
    hit: bool,
    age_hours: Optional[float] = None
) -> None:
    """
    Log cache hit/miss operations.
    
    Args:
        logger: Logger instance
        operation: Operation name ("cache_get", "cache_set", "cache_invalidate")
        cache_key: Cache key
        hit: True if cache hit, False if cache miss
        age_hours: Age of cached data in hours (for hits)
    """
    if hit:
        age_msg = f" (age: {age_hours:.1f}h)" if age_hours is not None else ""
        logger.debug(
            f"Cache hit for key '{cache_key}'{age_msg}",
            extra={"operation": operation}
        )
    else:
        logger.debug(
            f"Cache miss for key '{cache_key}'",
            extra={"operation": operation}
        )
