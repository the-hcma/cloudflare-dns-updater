"""Tests for the CLI runner."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from dns_updater.cli import run
from dns_updater.exit_codes import EXIT_OK, EXIT_UPDATED
from dns_updater.ip import ExternalAddresses


@patch("dns_updater.cli.update_dns_entries")
@patch("dns_updater.cli.persist_external_addresses")
@patch("dns_updater.cli.load_external_addresses")
def test_run_skips_when_unchanged(
    mock_load: MagicMock,
    mock_persist: MagicMock,
    mock_update: MagicMock,
) -> None:
    mock_load.return_value = ExternalAddresses(
        ipv4="1.2.3.4",
        ipv4_source="Nest WiFi (http://192.168.86.1/api/v1/status)",
        ipv6=None,
        ipv6_source=None,
        previous_ipv4="1.2.3.4",
        previous_ipv6=None,
    )
    assert run(force=False) == EXIT_OK
    mock_persist.assert_not_called()
    mock_update.assert_not_called()


@patch("dns_updater.cli.update_dns_entries")
@patch("dns_updater.cli.persist_external_addresses")
@patch("dns_updater.cli.load_external_addresses")
def test_run_updates_when_forced(
    mock_load: MagicMock,
    mock_persist: MagicMock,
    mock_update: MagicMock,
) -> None:
    mock_load.return_value = ExternalAddresses(
        ipv4="1.2.3.4",
        ipv4_source="HTTP (https://checkip.amazonaws.com)",
        ipv6="2001:db8::1",
        ipv6_source="host interface (en0)",
        previous_ipv4="1.2.3.4",
        previous_ipv6="2001:db8::1",
    )
    assert run(force=True) == EXIT_UPDATED
    mock_persist.assert_called_once()
    mock_update.assert_called_once_with("1.2.3.4", "2001:db8::1", config_path=None)


@patch("dns_updater.cli.update_dns_entries")
@patch("dns_updater.cli.persist_external_addresses")
@patch("dns_updater.cli.load_external_addresses")
def test_run_dry_run_skips_persist_and_calls_update_with_dry_run(
    mock_load: MagicMock,
    mock_persist: MagicMock,
    mock_update: MagicMock,
) -> None:
    mock_load.return_value = ExternalAddresses(
        ipv4="1.2.3.4",
        ipv4_source="HTTP (https://checkip.amazonaws.com)",
        ipv6=None,
        ipv6_source=None,
        previous_ipv4="1.2.3.4",
        previous_ipv6=None,
    )
    assert run(force=True, dry_run=True) == EXIT_UPDATED
    mock_persist.assert_not_called()
    mock_update.assert_called_once_with(
        "1.2.3.4",
        None,
        config_path=None,
        dry_run=True,
    )


@patch("dns_updater.cli.update_dns_entries")
@patch("dns_updater.cli.persist_external_addresses")
@patch("dns_updater.cli.load_external_addresses")
def test_run_dry_run_skips_when_unchanged_without_force(
    mock_load: MagicMock,
    mock_persist: MagicMock,
    mock_update: MagicMock,
) -> None:
    mock_load.return_value = ExternalAddresses(
        ipv4="1.2.3.4",
        ipv4_source="HTTP (https://checkip.amazonaws.com)",
        ipv6=None,
        ipv6_source=None,
        previous_ipv4="1.2.3.4",
        previous_ipv6=None,
    )
    assert run(dry_run=True) == EXIT_OK
    mock_persist.assert_not_called()
    mock_update.assert_not_called()
