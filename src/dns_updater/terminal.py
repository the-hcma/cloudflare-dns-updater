"""ANSI terminal styling for cloudflare-dns-updater CLI output."""

from __future__ import annotations

import argparse
import logging
import os
import re
import sys
from datetime import datetime
from typing import Final, TextIO

_HELP_OPTION_LINE = re.compile(
    r"^(?P<indent>  )(?P<opts>.+?)(?P<gap>  +)(?P<help>\S.*)$",
)

_RESET: Final = "\033[0m"
_STYLES: Final[dict[str, str]] = {
    "bold": "\033[1m",
    "dim": "\033[2m",
    "cyan": "\033[36m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "red": "\033[31m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
}

_LEVEL_STYLES: Final[dict[str, tuple[str, ...]]] = {
    "DEBUG": ("dim", "cyan"),
    "INFO": ("bold", "blue"),
    "WARNING": ("bold", "yellow"),
    "ERROR": ("bold", "red"),
    "CRITICAL": ("bold", "red"),
}

_COLOR_DISABLED: bool = False


def set_color_enabled(enabled: bool) -> None:
    """Enable or disable color output for the current process."""
    global _COLOR_DISABLED
    _COLOR_DISABLED = not enabled


def use_color(stream: TextIO | None = None) -> bool:
    """Return True when ANSI styling should be applied."""
    if _COLOR_DISABLED or os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("TERM", "").lower() == "dumb":
        return False
    stream = stream or sys.stdout
    return hasattr(stream, "isatty") and stream.isatty()


def style(text: str, *names: str, stream: TextIO | None = None) -> str:
    """Apply ANSI styles when color output is enabled."""
    if not use_color(stream):
        return text
    codes = "".join(_STYLES[name] for name in names if name in _STYLES)
    if not codes:
        return text
    return f"{codes}{text}{_RESET}"


def _short_logger_name(name: str) -> str:
    if name.startswith("dns_updater."):
        return name.removeprefix("dns_updater.")
    return name


class TerminalFormatter(logging.Formatter):
    """Compact, colorized log lines for interactive terminals."""

    def __init__(self) -> None:
        super().__init__()
        self._name_width = 14

    def format(self, record: logging.LogRecord) -> str:
        created = datetime.fromtimestamp(record.created)
        timestamp = f"{created.strftime('%m-%d %H:%M:%S')}.{int(record.msecs):03d}"
        module = _short_logger_name(record.name).ljust(self._name_width)[: self._name_width]
        level = record.levelname.ljust(5)
        message = record.getMessage()

        if use_color():
            timestamp = style(timestamp, "dim")
            module = style(module, "dim")
            level = style(level, *_LEVEL_STYLES.get(record.levelname, ()))
            message = self._style_message(message, record.levelname)

        return f"{timestamp}  {level}  {module}  {message}"

    def _style_message(self, message: str, level: str) -> str:
        if message.startswith("[dry-run]"):
            return style(message, "magenta")
        if level == "WARNING" and ("registered " in message or "updated " in message):
            return style(message, "green")
        if level == "INFO" and message.startswith("Cloudflare A ") and " already set to " in message:
            return style(message, "dim")
        if level == "WARNING" and (
            message.startswith("Cloudflare: all ") or "unchanged" in message and "skipping Cloudflare update" in message
        ):
            return style(message, "dim")
        if message.startswith("external "):
            return self._style_external_address(message)
        return message

    def _style_external_address(self, message: str) -> str:
        rest = message.removeprefix("external ")
        parts = rest.split(" ", 3)
        if len(parts) != 4 or parts[2] != "from":
            return message
        family, address, _, source = parts
        return (
            f"{style('external', 'dim')} {style(family, 'bold')} "
            f"{style(address, 'cyan', 'bold')} {style('from', 'dim')} {style(source, 'dim')}"
        )


class ColoredHelpFormatter(argparse.RawDescriptionHelpFormatter):
    """Argument help with colors applied after argparse computes column alignment."""

    def __init__(
        self,
        prog: str,
        indent_increment: int = 2,
        max_help_position: int = 32,
        width: int | None = None,
    ) -> None:
        super().__init__(prog, indent_increment, max_help_position, width)

    def _format_action(self, action: argparse.Action) -> str:
        formatted = super()._format_action(action)
        if not use_color():
            return formatted
        return "".join(self._colorize_help_line(line) for line in formatted.splitlines(keepends=True))

    def start_section(self, heading: str | None) -> None:
        if heading is not None and use_color():
            heading = style(heading, "bold", "cyan")
        super().start_section(heading)

    def _colorize_help_line(self, line: str) -> str:
        if line.startswith("usage:"):
            prefix, separator, rest = line.partition(":")
            return f"{style(prefix + separator, 'bold', 'cyan')}{rest}"

        content = line.rstrip("\n")
        newline = "\n" if line.endswith("\n") else ""
        match = _HELP_OPTION_LINE.match(content)
        if match is None:
            return line

        opts = " ".join(
            style(token, "bold", "green") if token.startswith("-") else style(token, "cyan")
            for token in match.group("opts").split()
        )
        return f"{match.group('indent')}{opts}{match.group('gap')}{match.group('help')}{newline}"


def configure_root_logging() -> None:
    """Attach a colorized handler to the root logger."""
    handler = logging.StreamHandler()
    handler.setFormatter(TerminalFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.WARNING)


def print_section(title: str) -> None:
    """Print a titled section header."""
    print(style(f"\n{title}", "bold", "cyan"))


def print_address_line(family: str, address: str | None, source: str | None) -> None:
    """Print a discovered address with its source."""
    label = f"External {family}"
    if address is not None and source is not None:
        print(f"  {style(label + ':', 'bold')} {style(address, 'cyan', 'bold')} {style(f'(from {source})', 'dim')}")
        return
    print(f"  {style(label + ':', 'bold')} {style('(not available)', 'dim')}")


def print_banner(title: str, detail: str, *, kind: str = "info") -> None:
    """Print a highlighted notice banner."""
    styles: tuple[str, ...] = ("bold", "yellow") if kind == "warn" else ("bold", "blue")
    print(f"\n{style(title, *styles)}")
    print(style(f"  {detail}", "dim"))


def print_error(message: str, *, stream: TextIO | None = None) -> None:
    """Print an error line to stderr."""
    stream = stream or sys.stderr
    stream.write(style(f"\n✗ {message}\n", "bold", "red", stream=stream))
