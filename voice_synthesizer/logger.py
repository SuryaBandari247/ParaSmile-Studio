"""Logging factory for the Voice Synthesizer module."""

import logging


def get_logger(name: str = "voice_synthesizer", level: str = "INFO") -> logging.Logger:
    """Create a configured logger instance.

    Args:
        name: Logger name.
        level: Log level string (DEBUG, INFO, WARNING, ERROR).

    Returns:
        Configured Logger instance.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        fmt = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
        handler.setFormatter(fmt)
        logger.addHandler(handler)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    return logger
