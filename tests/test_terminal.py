"""Tests for terminal styling helpers."""

from __future__ import annotations

import logging
from io import StringIO

import pytest

from cloudflare_dns_updater.terminal import (
    TerminalFormatter,
    print_address_line,
    set_color_enabled,
    style,
    use_color,
)


def test_use_color_disabled_by_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    set_color_enabled(False)
    assert use_color() is False
    set_color_enabled(True)


def test_style_without_color() -> None:
    set_color_enabled(False)
    assert style("hello", "red", "bold") == "hello"
    set_color_enabled(True)


def test_terminal_formatter_plain_output() -> None:
    set_color_enabled(False)
    record = logging.LogRecord(
        name="cloudflare_dns_updater.ip",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="external IPv4 %s from %s",
        args=("203.0.113.1", "Nest WiFi"),
        exc_info=None,
    )
    formatted = TerminalFormatter().format(record)
    assert "ip" in formatted
    assert "INFO" in formatted
    assert formatted.index("INFO") < formatted.index("ip")
    assert formatted[:20].count(".") == 1  # e.g. 05-23 07:37:40.797
    assert "203.0.113.1" in formatted
    assert "\033[" not in formatted
    set_color_enabled(True)


def test_print_address_line_no_color(capsys: pytest.CaptureFixture[str]) -> None:
    set_color_enabled(False)
    print_address_line("IPv4", "203.0.113.1", "Nest WiFi")
    captured = capsys.readouterr().out
    assert "External IPv4:" in captured
    assert "203.0.113.1" in captured
    assert "Nest WiFi" in captured
    assert "\033[" not in captured
    set_color_enabled(True)


def test_print_error_writes_to_stderr() -> None:
    set_color_enabled(False)
    stream = StringIO()
    from cloudflare_dns_updater.terminal import print_error

    print_error("boom", stream=stream)
    assert "boom" in stream.getvalue()
    set_color_enabled(True)
