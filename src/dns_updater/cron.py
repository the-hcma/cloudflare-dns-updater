"""Cron-mode helpers: log every run; emit actionable output on non-success."""

from __future__ import annotations

import io
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import TextIO

from dns_updater.exit_codes import EXIT_FAILURE, EXIT_OK, EXIT_UPDATED
from dns_updater.terminal import set_color_enabled

DEFAULT_CRON_LOG = Path("/tmp/cloudflare-dns-updater.log")
_SUCCESS_EXIT_CODES = frozenset({EXIT_OK, EXIT_UPDATED})


def normalize_exit_code(code: object) -> int:
    """Map ``SystemExit.code`` values to a process exit status."""
    if code is None:
        return EXIT_OK
    if isinstance(code, int):
        return code
    return EXIT_FAILURE


def append_log(log_path: Path, output: str) -> None:
    """Append run output to ``log_path``, creating parents as needed."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(output)
        if output and not output.endswith("\n"):
            handle.write("\n")


def emit_failure_mail(*, exit_code: int, output: str, log_path: Path, stream: TextIO) -> None:
    """Write a cron-mailable failure summary to ``stream``."""
    stream.write(f"cloudflare-dns-updater failed (exit {exit_code}):\n")
    body = output.strip()
    if body:
        stream.write(body)
        stream.write("\n")
    else:
        stream.write(f"(no captured output; see {log_path})\n")


def run_cron_capture(*, log_path: Path, body: Callable[[], None]) -> int:
    """Run ``body`` with captured I/O; log always; mail stderr on non-success.

    ``body`` should raise ``SystemExit`` with the CLI exit code (same as ``cli.main``).
    """
    os.environ["NO_COLOR"] = "1"
    set_color_enabled(False)

    buffer = io.StringIO()
    real_stdout = sys.stdout
    real_stderr = sys.stderr
    exit_code = EXIT_OK
    try:
        sys.stdout = buffer
        sys.stderr = buffer
        try:
            body()
        except SystemExit as exc:
            exit_code = normalize_exit_code(exc.code)
    finally:
        sys.stdout = real_stdout
        sys.stderr = real_stderr

    output = buffer.getvalue()
    append_log(log_path, output)

    if exit_code not in _SUCCESS_EXIT_CODES:
        emit_failure_mail(
            exit_code=exit_code,
            output=output,
            log_path=log_path,
            stream=real_stderr,
        )

    return exit_code
