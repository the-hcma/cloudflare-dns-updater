"""Tests for default run logging and cron-friendly failure mail."""

from __future__ import annotations

import io
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from dns_updater.cli import main
from dns_updater.cron import append_log, default_log_path, run_with_logging
from dns_updater.exit_codes import EXIT_FAILURE, EXIT_OK, EXIT_UPDATED


def _run_non_tty(*, log_path: Path, argv: list[str], fake_run: object) -> tuple[int, str, str]:
    """Invoke ``main`` with non-TTY stderr; return exit code, log text, and mail stderr."""
    mail_stderr = io.StringIO()
    previous = sys.stderr
    sys.stderr = mail_stderr
    try:
        with (
            patch("dns_updater.cli.run", side_effect=fake_run),
            patch("dns_updater.cron.run_with_logging") as mock_logging,
        ):
            # Call the real helper but force non-TTY mirroring off via direct path
            mock_logging.side_effect = lambda **kwargs: run_with_logging(
                log_path=kwargs["log_path"],
                body=kwargs["body"],
                mirror_stderr=False,
            )
            with pytest.raises(SystemExit) as exc_info:
                main(["--log", str(log_path), *argv])
    finally:
        sys.stderr = previous

    code = exc_info.value.code
    assert isinstance(code, int)
    return code, log_path.read_text(encoding="utf-8"), mail_stderr.getvalue()


def test_success_exit_ok_is_quiet_when_not_tty(tmp_path: Path) -> None:
    log_path = tmp_path / "updater.log"

    def fake_run(**_kwargs: object) -> int:
        print("addresses unchanged", file=sys.stderr)
        return EXIT_OK

    code, log_text, mail = _run_non_tty(log_path=log_path, argv=[], fake_run=fake_run)

    assert code == EXIT_OK
    assert "addresses unchanged" in log_text
    assert mail == ""


def test_success_exit_updated_is_quiet_when_not_tty(tmp_path: Path) -> None:
    log_path = tmp_path / "updater.log"

    def fake_run(**_kwargs: object) -> int:
        print("updated AAAA example.com", file=sys.stderr)
        return EXIT_UPDATED

    code, log_text, mail = _run_non_tty(log_path=log_path, argv=["-f"], fake_run=fake_run)

    assert code == EXIT_UPDATED
    assert "updated AAAA" in log_text
    assert mail == ""


def test_non_success_includes_actionable_output_when_not_tty(tmp_path: Path) -> None:
    log_path = tmp_path / "updater.log"

    def fake_run(**_kwargs: object) -> int:
        raise RuntimeError("Cloudflare API error")

    code, log_text, mail = _run_non_tty(log_path=log_path, argv=[], fake_run=fake_run)

    assert code == EXIT_FAILURE
    assert "Cloudflare API error" in log_text
    assert f"cloudflare-dns-updater failed (exit {EXIT_FAILURE}):" in mail
    assert "Cloudflare API error" in mail


def test_tty_mirrors_stderr_even_on_success(tmp_path: Path) -> None:
    log_path = tmp_path / "updater.log"
    terminal = io.StringIO()

    def body() -> None:
        print("addresses unchanged", file=sys.stderr)
        raise SystemExit(EXIT_OK)

    previous = sys.stderr
    sys.stderr = terminal
    try:
        code = run_with_logging(log_path=log_path, body=body, mirror_stderr=True)
    finally:
        sys.stderr = previous

    assert code == EXIT_OK
    assert "addresses unchanged" in terminal.getvalue()
    assert "addresses unchanged" in log_path.read_text(encoding="utf-8")
    assert "failed (exit" not in terminal.getvalue()


def test_stdout_always_mirrored_for_redirects(tmp_path: Path) -> None:
    log_path = tmp_path / "updater.log"
    captured_out = io.StringIO()

    def body() -> None:
        print("plan line", file=sys.stdout)
        raise SystemExit(EXIT_OK)

    previous_out, previous_err = sys.stdout, sys.stderr
    sys.stdout = captured_out
    sys.stderr = io.StringIO()  # non-TTY stderr (cron-like)
    try:
        code = run_with_logging(log_path=log_path, body=body, mirror_stderr=False)
    finally:
        sys.stdout = previous_out
        sys.stderr = previous_err

    assert code == EXIT_OK
    assert "plan line" in captured_out.getvalue()
    assert "plan line" in log_path.read_text(encoding="utf-8")


def test_append_log_failure_does_not_mask_exit_code(tmp_path: Path) -> None:
    log_path = tmp_path / "blocked" / "updater.log"
    mail_stderr = io.StringIO()

    def body() -> None:
        raise SystemExit(EXIT_FAILURE)

    previous = sys.stderr
    sys.stderr = mail_stderr
    try:
        with patch("dns_updater.cron.append_log", side_effect=PermissionError("denied")):
            code = run_with_logging(log_path=log_path, body=body, mirror_stderr=False)
    finally:
        sys.stderr = previous

    assert code == EXIT_FAILURE
    assert "failed to write log" in mail_stderr.getvalue()
    assert f"exit {EXIT_FAILURE}" in mail_stderr.getvalue()


def test_append_log_creates_parent(tmp_path: Path) -> None:
    log_path = tmp_path / "nested" / "updater.log"
    append_log(log_path, "hello")
    assert log_path.read_text(encoding="utf-8") == "hello\n"


def test_append_log_rejects_symlink(tmp_path: Path) -> None:
    target = tmp_path / "victim"
    target.write_text("keep\n", encoding="utf-8")
    link = tmp_path / "updater.log"
    link.symlink_to(target)
    with pytest.raises(OSError):
        append_log(link, "injected")
    assert target.read_text(encoding="utf-8") == "keep\n"


def test_default_log_is_under_xdg_state(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    state_home = tmp_path / "state"
    monkeypatch.setenv("XDG_STATE_HOME", str(state_home))
    assert default_log_path() == state_home / "cloudflare-dns-updater" / "updater.log"
