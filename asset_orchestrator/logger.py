"""Logging factory for the Asset Orchestrator module.

Provides a consistent logger configuration across all components with
structured formatting: timestamp, level, module name, and message.
"""

import logging

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

VALID_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR"}


def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    """Create and return a configured logger.

    Args:
        name: Logger name, typically the module's ``__name__``.
        level: Log level string — one of DEBUG, INFO, WARNING, ERROR.
               Defaults to INFO.

    Returns:
        A :class:`logging.Logger` with a ``StreamHandler`` and consistent
        formatting applied.
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(getattr(logging, level.upper(), logging.INFO))
        formatter = logging.Formatter(LOG_FORMAT)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
