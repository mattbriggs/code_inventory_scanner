"""Logging configuration utilities for the code inventory scanner."""

from __future__ import annotations

import logging
import sys
from typing import Final, TextIO

LOG_FORMAT: Final[str] = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
LOG_DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"


def configure_logging(
    verbose: bool = False,
    stream: TextIO | None = None,
) -> None:
    """Configure application logging.

    This function configures the root logger for CLI execution and test runs.
    If logging has already been configured, existing handlers are replaced so
    repeated calls do not produce duplicate log lines.

    :param verbose: If ``True``, use ``DEBUG`` level; otherwise ``INFO``.
    :type verbose: bool
    :param stream: Optional output stream for log messages. Defaults to
        ``sys.stderr`` when not provided.
    :type stream: TextIO | None
    :return: None
    :rtype: None
    """
    level = logging.DEBUG if verbose else logging.INFO
    target_stream = stream if stream is not None else sys.stderr

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    _clear_handlers(root_logger)

    handler = logging.StreamHandler(target_stream)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT))

    root_logger.addHandler(handler)


def _clear_handlers(logger: logging.Logger) -> None:
    """Remove and close all handlers attached to a logger.

    :param logger: Logger whose handlers should be removed.
    :type logger: logging.Logger
    :return: None
    :rtype: None
    """
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        try:
            handler.close()
        except Exception:
            # Logging cleanup should not crash the application.
            pass