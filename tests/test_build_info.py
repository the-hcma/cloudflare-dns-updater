"""Tests for version and commit resolution."""

from __future__ import annotations

from unittest.mock import patch

from dns_updater.build_info import format_cli_version_line, format_help_version_line, get_build_info


def test_format_help_version_line() -> None:
    with (
        patch("dns_updater.build_info._resolve_version", return_value="0.1.0"),
        patch("dns_updater.build_info._resolve_commit", return_value="abc123def456"),
    ):
        get_build_info.cache_clear()
        line = format_help_version_line()
    assert line == "version: 0.1.0 (abc123def456)"


def test_format_cli_version_line() -> None:
    with (
        patch("dns_updater.build_info._resolve_version", return_value="0.1.0"),
        patch("dns_updater.build_info._resolve_commit", return_value="abc123def456"),
    ):
        get_build_info.cache_clear()
        line = format_cli_version_line(prog="cloudflare-dns-updater")
    assert line == "cloudflare-dns-updater 0.1.0 (abc123def456)"
