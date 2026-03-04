"""
Logging factory for the Script Converter.

Provides a simple logger factory that creates configured loggers
with timestamp, level, module name, and message formatting.
"""

import logging
import sys

_VALID_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR"}


def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    """
    Create a configured logger for a script_generator component.

    Args:
        name: Component name (e.g., "converter", "llm_client").
        level: Log level string — DEBUG, INFO, WARNING, or ERROR.
               Defaults to INFO.

    Returns:
        Configured logging.Logger instance.
    """
    level = level.upper()
    if level not in _VALID_LEVELS:
        level = "INFO"

    logger = logging.getLogger(f"script_generator.{name}")
    logger.setLevel(getattr(logging, level))

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.propagate = False
    return logger
