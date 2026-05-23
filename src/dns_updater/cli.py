"""Command-line entry point for cloudflare-dns-updater."""

from __future__ import annotations

import argparse
import logging
import sys
import traceback
from pathlib import Path

from dns_updater.build_info import format_cli_version_line, format_help_version_line
from dns_updater.cloudflare_dns import update_dns_entries
from dns_updater.ip import load_external_addresses, persist_external_addresses
from dns_updater.terminal import (
    ColoredHelpFormatter,
    configure_root_logging,
    print_address_line,
    print_banner,
    print_error,
    print_section,
    set_color_enabled,
)

_LOGGER = logging.getLogger("dns_updater")
_LOGGERS_VERBOSE: tuple[str, ...] = (
    "dns_updater",
    "dns_updater.config",
    "dns_updater.ip",
    "dns_updater.cloudflare_dns",
)

_DESCRIPTION = """\
Update Cloudflare A and AAAA records when your external IP address changes.

Discovers the current WAN IPv4 (Nest WiFi or HTTP fallback) and optional IPv6,
then creates or updates DNS records defined in config.json.
"""

_EPILOG = """\
examples:
  %(prog)s                 update only when the address changed
  %(prog)s -f              recheck Cloudflare even if local state is unchanged
  %(prog)s -d              dry-run: show planned DNS changes only
  %(prog)s -v -d           verbose dry-run with discovery details

exit status: 0 if no update was needed, 1 if records were updated or dry-run completed

colors are enabled on terminals; set NO_COLOR=1 or pass --no-color to disable
"""


def _description() -> str:
    return f"{format_help_version_line()}\n\n{_DESCRIPTION}"


def _configure_logging(*, verbose: bool) -> None:
    configure_root_logging()
    level = logging.INFO if verbose else logging.WARNING
    for logger_name in _LOGGERS_VERBOSE:
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
        if verbose and logger_name == "dns_updater.config":
            logger.setLevel(logging.DEBUG)


def run(
    *,
    force: bool = False,
    verbose: bool = False,
    dry_run: bool = False,
    config_path: Path | None = None,
) -> int:
    """Discover external IPs and update Cloudflare when they change."""
    addresses = load_external_addresses(config_path=config_path)
    if verbose or dry_run:
        print_section("Discovered addresses")
        print_address_line("IPv4", addresses.ipv4, addresses.ipv4_source)
        print_address_line("IPv6", addresses.ipv6, addresses.ipv6_source)

    if not force and not addresses.changed:
        return 0

    if force and not addresses.changed:
        _LOGGER.info(
            "forcing Cloudflare check despite unchanged local state (IPv4=%s, IPv6=%s)",
            addresses.ipv4,
            addresses.ipv6 or "none",
        )

    if dry_run:
        print_banner(
            "Dry-run",
            "skipping Cloudflare API calls and state file writes",
            kind="warn",
        )
        update_dns_entries(
            addresses.ipv4,
            addresses.ipv6,
            config_path=config_path,
            dry_run=True,
        )
        return 1

    persist_external_addresses(addresses)
    update_dns_entries(addresses.ipv4, addresses.ipv6, config_path=config_path)
    return 1


def main() -> None:
    """Parse arguments and run the updater."""
    parser = argparse.ArgumentParser(
        prog="cloudflare-dns-updater",
        description=_description(),
        epilog=_EPILOG,
        formatter_class=ColoredHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=format_cli_version_line(prog="cloudflare-dns-updater"),
        help="show version and source commit, then exit",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="disable ANSI colors even when writing to a terminal",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help=(
            "check Cloudflare even when the locally stored address is unchanged "
            "(records are only modified when Cloudflare differs)"
        ),
    )
    parser.add_argument(
        "-d",
        "--dry-run",
        action="store_true",
        help="discover addresses and print planned updates without calling Cloudflare",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="enable verbose logging and print address discovery sources",
    )
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        metavar="PATH",
        help=(
            "path to config.json (default: ./config.json, then "
            "~/.config/cloudflare-dns-updater/config.json, or CLOUDFLARE_DNS_UPDATER_CONFIG)"
        ),
    )
    args = parser.parse_args()

    if args.no_color:
        set_color_enabled(False)

    _configure_logging(verbose=args.verbose)

    try:
        raise SystemExit(
            run(
                force=args.force,
                verbose=args.verbose,
                dry_run=args.dry_run,
                config_path=args.config,
            )
        )
    except KeyboardInterrupt:
        print("\n")
        print_error("interrupted")
        raise SystemExit(1) from None
    except Exception as exception:
        traceback.print_exc(file=sys.stderr)
        print_error(f"execution failed: {exception}")
        raise SystemExit(1) from exception


if __name__ == "__main__":
    main()
