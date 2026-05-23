"""Tests for CLI help output."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

_OPTION_LINE = re.compile(r"^  (?P<opts>\S(?:.*\S)?)  (?P<help>\S)")


def _help_text() -> str:
    result = subprocess.run(
        [sys.executable, "-m", "cloudflare_dns_updater.cli", "--help"],
        capture_output=True,
        text=True,
        check=True,
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "NO_COLOR": "1"},
    )
    return result.stdout


def test_help_option_descriptions_align() -> None:
    """First line of each option should leave help text in the same column."""
    widths: list[int] = []
    for line in _help_text().splitlines():
        match = _OPTION_LINE.match(line)
        if match is None:
            continue
        widths.append(len(match.group("opts")))

    assert widths, "expected at least one option line in --help output"
    assert len(set(widths)) == 1, f"option/help columns misaligned: {widths}"


def test_help_lists_expected_options() -> None:
    text = _help_text()
    for flag in ("--no-color", "-f", "--force", "-d", "--dry-run", "-v", "--verbose", "-c", "--config"):
        assert flag in text


def test_help_uses_colors_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    import argparse

    from cloudflare_dns_updater.terminal import ColoredHelpFormatter

    monkeypatch.setattr("cloudflare_dns_updater.terminal.use_color", lambda stream=None: True)
    parser = argparse.ArgumentParser(formatter_class=ColoredHelpFormatter)
    parser.add_argument("-f", "--force")
    parser.add_argument("-c", "--config", metavar="PATH")
    text = parser.format_help()
    assert "\033[" in text
