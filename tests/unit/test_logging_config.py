"""Unit tests for logging configuration utilities."""

from __future__ import annotations

import io
import logging

import pytest

from code_inventory import logging_config


@pytest.fixture
def clean_root_logger() -> logging.Logger:
    """Provide a clean root logger and restore original handlers afterward.

    :return: Root logger with isolated handler state for the test.
    :rtype: logging.Logger
    """
    root_logger = logging.getLogger()

    original_handlers = list(root_logger.handlers)
    original_level = root_logger.level

    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    try:
        yield root_logger
    finally:
        for handler in list(root_logger.handlers):
            root_logger.removeHandler(handler)
            try:
                handler.close()
            except Exception:
                pass

        for handler in original_handlers:
            root_logger.addHandler(handler)
        root_logger.setLevel(original_level)


def test_configure_logging_sets_info_level_by_default(
    clean_root_logger: logging.Logger,
) -> None:
    """Verify default configuration uses INFO level.

    :param clean_root_logger: Isolated root logger fixture.
    :type clean_root_logger: logging.Logger
    :return: None
    :rtype: None
    """
    stream = io.StringIO()

    logging_config.configure_logging(stream=stream)

    root_logger = clean_root_logger
    assert root_logger.level == logging.INFO
    assert len(root_logger.handlers) == 1

    handler = root_logger.handlers[0]
    assert isinstance(handler, logging.StreamHandler)
    assert handler.level == logging.INFO
    assert handler.formatter is not None
    assert handler.formatter._fmt == logging_config.LOG_FORMAT  # noqa: SLF001
    assert handler.formatter.datefmt == logging_config.LOG_DATE_FORMAT


def test_configure_logging_sets_debug_level_when_verbose(
    clean_root_logger: logging.Logger,
) -> None:
    """Verify verbose mode configures DEBUG logging.

    :param clean_root_logger: Isolated root logger fixture.
    :type clean_root_logger: logging.Logger
    :return: None
    :rtype: None
    """
    stream = io.StringIO()

    logging_config.configure_logging(verbose=True, stream=stream)

    root_logger = clean_root_logger
    assert root_logger.level == logging.DEBUG
    assert len(root_logger.handlers) == 1
    assert root_logger.handlers[0].level == logging.DEBUG


def test_configure_logging_writes_to_custom_stream(
    clean_root_logger: logging.Logger,
) -> None:
    """Verify log messages are written to a provided stream.

    :param clean_root_logger: Isolated root logger fixture.
    :type clean_root_logger: logging.Logger
    :return: None
    :rtype: None
    """
    stream = io.StringIO()

    logging_config.configure_logging(verbose=False, stream=stream)

    logger = logging.getLogger("code_inventory.test")
    logger.info("hello log")

    output = stream.getvalue()
    assert "INFO" in output
    assert "[code_inventory.test]" in output
    assert "hello log" in output


def test_configure_logging_replaces_existing_handlers_no_duplicates(
    clean_root_logger: logging.Logger,
) -> None:
    """Verify repeated configuration replaces handlers instead of stacking them.

    :param clean_root_logger: Isolated root logger fixture.
    :type clean_root_logger: logging.Logger
    :return: None
    :rtype: None
    """
    stream_one = io.StringIO()
    stream_two = io.StringIO()

    logging_config.configure_logging(stream=stream_one)
    first_handler = clean_root_logger.handlers[0]

    logging_config.configure_logging(verbose=True, stream=stream_two)
    second_handler = clean_root_logger.handlers[0]

    assert len(clean_root_logger.handlers) == 1
    assert second_handler is not first_handler
    assert clean_root_logger.level == logging.DEBUG

    logger = logging.getLogger("code_inventory.test")
    logger.debug("debug-only-on-second-stream")

    assert "debug-only-on-second-stream" not in stream_one.getvalue()
    assert "debug-only-on-second-stream" in stream_two.getvalue()


def test_configure_logging_uses_sys_stderr_when_stream_not_provided(
    monkeypatch: pytest.MonkeyPatch,
    clean_root_logger: logging.Logger,
) -> None:
    """Verify default logging stream is sys.stderr.

    :param monkeypatch: Pytest monkeypatch fixture.
    :type monkeypatch: pytest.MonkeyPatch
    :param clean_root_logger: Isolated root logger fixture.
    :type clean_root_logger: logging.Logger
    :return: None
    :rtype: None
    """
    fake_stderr = io.StringIO()
    monkeypatch.setattr(logging_config.sys, "stderr", fake_stderr)

    logging_config.configure_logging()

    logger = logging.getLogger("code_inventory.stderr_test")
    logger.info("stderr message")

    output = fake_stderr.getvalue()
    assert "stderr message" in output
    assert "[code_inventory.stderr_test]" in output


def test_clear_handlers_removes_and_closes_handlers(
    clean_root_logger: logging.Logger,
) -> None:
    """Verify _clear_handlers removes and closes handlers.

    :param clean_root_logger: Isolated root logger fixture.
    :type clean_root_logger: logging.Logger
    :return: None
    :rtype: None
    """
    closed_flags: list[bool] = []

    class TrackingHandler(logging.StreamHandler):
        """Stream handler that records whether close() was called."""

        def close(self) -> None:
            """Record close calls and then close normally.

            :return: None
            :rtype: None
            """
            closed_flags.append(True)
            super().close()

    handler_one = TrackingHandler(io.StringIO())
    handler_two = TrackingHandler(io.StringIO())
    clean_root_logger.addHandler(handler_one)
    clean_root_logger.addHandler(handler_two)

    logging_config._clear_handlers(clean_root_logger)

    assert clean_root_logger.handlers == []
    assert len(closed_flags) == 2


def test_clear_handlers_swallows_close_exceptions(
    clean_root_logger: logging.Logger,
) -> None:
    """Verify _clear_handlers does not raise if handler.close() fails.

    :param clean_root_logger: Isolated root logger fixture.
    :type clean_root_logger: logging.Logger
    :return: None
    :rtype: None
    """
    class BadCloseHandler(logging.StreamHandler):
        """Handler whose close method raises an exception."""

        def close(self) -> None:
            """Raise an error on close.

            :return: None
            :rtype: None
            :raises RuntimeError: Always.
            """
            raise RuntimeError("close failed")

    bad_handler = BadCloseHandler(io.StringIO())
    clean_root_logger.addHandler(bad_handler)

    # Should not raise.
    logging_config._clear_handlers(clean_root_logger)

    assert clean_root_logger.handlers == []