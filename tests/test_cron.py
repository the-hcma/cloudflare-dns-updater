"""Tests for CLI --cron mode."""

from __future__ import annotations

import io
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from dns_updater.cli import main
from dns_updater.exit_codes import EXIT_FAILURE, EXIT_OK, EXIT_UPDATED


def _run_cron(*, log_path: Path, argv: list[str], fake_run: object) -> tuple[int, str, str]:
    """Invoke ``main`` with ``--cron``; return exit code, log text, and mail stderr."""
    mail_stderr = io.StringIO()
    previous = sys.stderr
    sys.stderr = mail_stderr
    try:
        with patch("dns_updater.cli.run", side_effect=fake_run), pytest.raises(SystemExit) as exc_info:
            main(["--cron", "--log", str(log_path), *argv])
    finally:
        sys.stderr = previous

    code = exc_info.value.code
    assert isinstance(code, int)
    return code, log_path.read_text(encoding="utf-8"), mail_stderr.getvalue()


def test_cron_success_exit_ok_is_quiet(tmp_path: Path) -> None:
    log_path = tmp_path / "updater.log"

    def fake_run(**_kwargs: object) -> int:
        print("addresses unchanged", file=sys.stderr)
        return EXIT_OK

    code, log_text, mail = _run_cron(log_path=log_path, argv=[], fake_run=fake_run)

    assert code == EXIT_OK
    assert "addresses unchanged" in log_text
    assert mail == ""


def test_cron_success_exit_updated_is_quiet(tmp_path: Path) -> None:
    log_path = tmp_path / "updater.log"

    def fake_run(**_kwargs: object) -> int:
        print("updated AAAA example.com", file=sys.stderr)
        return EXIT_UPDATED

    code, log_text, mail = _run_cron(log_path=log_path, argv=["-f"], fake_run=fake_run)

    assert code == EXIT_UPDATED
    assert "updated AAAA" in log_text
    assert mail == ""


def test_cron_non_success_includes_actionable_output(tmp_path: Path) -> None:
    log_path = tmp_path / "updater.log"

    def fake_run(**_kwargs: object) -> int:
        raise RuntimeError("Cloudflare API error")

    code, log_text, mail = _run_cron(log_path=log_path, argv=[], fake_run=fake_run)

    assert code == EXIT_FAILURE
    assert "Cloudflare API error" in log_text
    assert f"cloudflare-dns-updater failed (exit {EXIT_FAILURE}):" in mail
    assert "Cloudflare API error" in mail


def test_cron_empty_capture_falls_back_to_log_path(tmp_path: Path) -> None:
    log_path = tmp_path / "updater.log"

    with patch("dns_updater.cli._execute", side_effect=SystemExit(EXIT_FAILURE)):
        mail_stderr = io.StringIO()
        previous = sys.stderr
        sys.stderr = mail_stderr
        try:
            with pytest.raises(SystemExit) as exc_info:
                main(["--cron", "--log", str(log_path)])
        finally:
            sys.stderr = previous

    assert exc_info.value.code == EXIT_FAILURE
    mail = mail_stderr.getvalue()
    assert f"exit {EXIT_FAILURE}" in mail
    assert str(log_path) in mail


def test_log_without_cron_errors() -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--log", "/tmp/x.log"])
    assert exc_info.value.code == 2


def test_cron_default_log_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    default_log = tmp_path / "default.log"
    monkeypatch.setattr("dns_updater.cli.DEFAULT_CRON_LOG", default_log)

    def fake_run(**_kwargs: object) -> int:
        return EXIT_OK

    with patch("dns_updater.cli.run", side_effect=fake_run), pytest.raises(SystemExit) as exc_info:
        main(["--cron"])

    assert exc_info.value.code == EXIT_OK
    assert default_log.is_file()


def test_cron_mode_invokes_capture(tmp_path: Path) -> None:
    log_path = tmp_path / "via-argv.log"
    with (
        patch("dns_updater.cli.run_cron_capture", return_value=EXIT_OK) as mock_capture,
        patch("dns_updater.cli._build_parser") as mock_parser,
    ):
        ns = MagicMock(
            cron=True,
            log=log_path,
            no_color=False,
            force=False,
            dry_run=False,
            verbose=False,
            config=None,
        )
        mock_parser.return_value.parse_args.return_value = ns
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code == EXIT_OK
    mock_capture.assert_called_once()
    assert mock_capture.call_args.kwargs["log_path"] == log_path
