"""Run logging helpers: always append to a log; mail stderr on non-success when not a TTY."""

from __future__ import annotations

import contextlib
import io
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import TextIO, cast

from dns_updater.exit_codes import EXIT_FAILURE, EXIT_OK, EXIT_UPDATED
from dns_updater.terminal import set_color_enabled

DEFAULT_LOG_NAME = "updater.log"
_SUCCESS_EXIT_CODES = frozenset({EXIT_OK, EXIT_UPDATED})


def default_log_path() -> Path:
    """Return the per-user default log path under ``XDG_STATE_HOME``."""
    state_home = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    return state_home / "cloudflare-dns-updater" / DEFAULT_LOG_NAME


# Backwards-compatible alias for docs/tests that reference the module attribute.
DEFAULT_LOG = default_log_path()


class _TeeTextIO(io.StringIO):
    """Capture writes to a shared log buffer while optionally mirroring live."""

    def __init__(self, log_buffer: io.StringIO, mirror: TextIO | None) -> None:
        super().__init__()
        self._log_buffer = log_buffer
        self._mirror = mirror

    def write(self, s: str) -> int:  # noqa: A003 — TextIO API
        self._log_buffer.write(s)
        super().write(s)
        if self._mirror is not None:
            self._mirror.write(s)
        return len(s)

    def flush(self) -> None:
        self._log_buffer.flush()
        super().flush()
        if self._mirror is not None:
            self._mirror.flush()

    def isatty(self) -> bool:
        return bool(self._mirror is not None and self._mirror.isatty())


def normalize_exit_code(code: object) -> int:
    """Map ``SystemExit.code`` values to a process exit status."""
    if code is None:
        return EXIT_OK
    if isinstance(code, int):
        return code
    return EXIT_FAILURE


def append_log(log_path: Path, output: str) -> None:
    """Append run output to ``log_path``, creating parents as needed.

    Opens with ``O_NOFOLLOW`` so a symlink at the log path cannot redirect writes
    into an attacker-chosen file (important for predictable paths under shared dirs).
    """
    log_path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW
    fd = os.open(log_path, flags, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as handle:
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


def run_with_logging(
    *,
    log_path: Path,
    body: Callable[[], None],
    mirror_stderr: bool | None = None,
) -> int:
    """Run ``body`` with captured I/O; always append to the log.

    Stdout is always mirrored to the real stdout (so redirects/pipes keep working).
    Stderr is mirrored live when ``mirror_stderr`` is true (default: real stderr is a
    TTY). When stderr is not mirrored (typical cron), write captured output to
    stderr only on non-success exits so cron mail is actionable without spam on
    exit ``0``/``1``.

    ``body`` should raise ``SystemExit`` with the CLI exit code (same as ``cli.main``).
    """
    real_stdout = sys.stdout
    real_stderr = sys.stderr
    if mirror_stderr is None:
        mirror_stderr = bool(getattr(real_stderr, "isatty", lambda: False)())

    if not mirror_stderr:
        os.environ["NO_COLOR"] = "1"
        set_color_enabled(False)

    log_buffer = io.StringIO()
    stdout_tee = _TeeTextIO(log_buffer, real_stdout)
    stderr_tee = _TeeTextIO(log_buffer, real_stderr if mirror_stderr else None)
    exit_code = EXIT_OK
    try:
        sys.stdout = cast(TextIO, stdout_tee)
        sys.stderr = cast(TextIO, stderr_tee)
        try:
            body()
        except SystemExit as exc:
            exit_code = normalize_exit_code(exc.code)
    finally:
        sys.stdout = real_stdout
        sys.stderr = real_stderr

    output = log_buffer.getvalue()
    try:
        append_log(log_path, output)
    except OSError as error:
        with contextlib.suppress(OSError):
            real_stderr.write(f"cloudflare-dns-updater: failed to write log {log_path}: {error}\n")

    if exit_code not in _SUCCESS_EXIT_CODES and not mirror_stderr:
        with contextlib.suppress(OSError):
            emit_failure_mail(
                exit_code=exit_code,
                output=output,
                log_path=log_path,
                stream=real_stderr,
            )

    return exit_code
