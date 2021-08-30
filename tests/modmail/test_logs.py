import contextlib
import io
import logging

import pytest

from modmail.log import ModmailLogger

"""
Test custom logging levels
"""


@pytest.mark.dependency(name="create_logger")
def test_create_logging():
    """Modmail logging is importable and sets root logger correctly."""
    log = logging.getLogger(__name__)
    assert isinstance(log, ModmailLogger)


@pytest.fixture
def log() -> ModmailLogger:
    """
    Pytest fixture.

    ModmailLogger logging instance
    """
    log: ModmailLogger = logging.getLogger(__name__)
    return log


@pytest.mark.dependency(depends=["create_logger"])
def test_notice_level(log):
    """Test notice logging level prints a notice response."""
    notice_test_phrase = "Kinda important info"
    stdout = io.StringIO()

    with contextlib.redirect_stderr(stdout):
        log.notice(notice_test_phrase)
    resp = stdout.getvalue()

    assert notice_test_phrase in resp
    assert "NOTICE" in resp


@pytest.mark.dependency(depends=["create_logger"])
def test_trace_level(log):
    """Test trace logging level prints a trace response."""
    trace_test_phrase = "Getting in the weeds"
    stdout = io.StringIO()

    with contextlib.redirect_stderr(stdout):
        log.trace(trace_test_phrase)
    resp = stdout.getvalue()

    assert "TRACE" in resp
    assert trace_test_phrase in resp
