"""Integration-style tests with mocked external IP discovery."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from helpers import MockExternalIps

from dns_updater.cli import run
from dns_updater.ip import ExternalAddresses


@patch("dns_updater.cli.update_dns_entries")
@patch("dns_updater.cli.persist_external_addresses")
@patch("dns_updater.cli.load_external_addresses")
def test_run_updates_when_mock_external_ipv4_changes(
    mock_load: MagicMock,
    mock_persist: MagicMock,
    mock_update: MagicMock,
    mock_external_ips: MockExternalIps,
) -> None:
    mock_load.return_value = mock_external_ips.addresses
    assert run(force=False) == 1
    mock_persist.assert_called_once_with(mock_external_ips.addresses)
    mock_update.assert_called_once_with(
        mock_external_ips.ipv4,
        mock_external_ips.ipv6,
        config_path=None,
    )


@patch("dns_updater.cli.update_dns_entries")
@patch("dns_updater.cli.persist_external_addresses")
@patch("dns_updater.cli.load_external_addresses")
def test_run_skips_when_mock_external_ips_unchanged(
    mock_load: MagicMock,
    mock_persist: MagicMock,
    mock_update: MagicMock,
    mock_external_ips: MockExternalIps,
) -> None:
    mock_load.return_value = mock_external_ips.unchanged_addresses
    assert run(force=False) == 0
    mock_persist.assert_not_called()
    mock_update.assert_not_called()


@patch("dns_updater.cli.update_dns_entries")
@patch("dns_updater.cli.persist_external_addresses")
@patch("dns_updater.ip.discover_ipv6")
@patch("dns_updater.ip.discover_ipv4")
@patch("dns_updater.ip._read_state_file", return_value=None)
def test_run_discovers_mock_ipv4_only(
    mock_read: MagicMock,
    mock_discover_v4: MagicMock,
    mock_discover_v6: MagicMock,
    mock_persist: MagicMock,
    mock_update: MagicMock,
    mock_external_ips: MockExternalIps,
) -> None:
    mock_discover_v4.return_value = (mock_external_ips.ipv4, "mock-ipv4")
    mock_discover_v6.return_value = (None, None)
    from dns_updater.ip import load_external_addresses

    addresses = load_external_addresses()
    assert addresses.ipv4 == mock_external_ips.ipv4
    assert addresses.ipv6 is None
    assert addresses.changed is True


@patch("dns_updater.cli.update_dns_entries")
@patch("dns_updater.cli.persist_external_addresses")
@patch("dns_updater.ip.discover_ipv6")
@patch("dns_updater.ip.discover_ipv4")
@patch("dns_updater.ip._read_state_file")
def test_run_discovers_mock_ipv4_and_ipv6(
    mock_read: MagicMock,
    mock_discover_v4: MagicMock,
    mock_discover_v6: MagicMock,
    mock_persist: MagicMock,
    mock_update: MagicMock,
    mock_external_ips: MockExternalIps,
) -> None:
    mock_discover_v4.return_value = (mock_external_ips.ipv4, "mock-ipv4")
    mock_discover_v6.return_value = (mock_external_ips.ipv6, "mock-ipv6")
    mock_read.side_effect = [mock_external_ips.previous_ipv4, mock_external_ips.previous_ipv6]

    from dns_updater.ip import load_external_addresses

    addresses = load_external_addresses()
    assert addresses.ipv4 == mock_external_ips.ipv4
    assert addresses.ipv6 == mock_external_ips.ipv6
    assert addresses.changed is True


@patch("dns_updater.cloudflare_dns.load_config")
@patch("dns_updater.cloudflare_dns._cloudflare_client")
@patch("dns_updater.cli.persist_external_addresses")
@patch("dns_updater.cli.load_external_addresses")
def test_run_uses_config_json_for_cloudflare(
    mock_load: MagicMock,
    mock_persist: MagicMock,
    mock_client_factory: MagicMock,
    mock_load_config: MagicMock,
    mock_external_ips: MockExternalIps,
    tmp_path: Path,
) -> None:
    from helpers import write_config_file

    config_file = write_config_file(
        tmp_path / "config.json",
        cloudflare_api_token="integration-test-token",
    )
    mock_client = MagicMock()
    zone = MagicMock()
    zone.id = "zone-abc"
    zone.name = "hcma.info"
    mock_client.zones.list.return_value.result = [zone]
    mock_client.dns.records.list.return_value.result = []
    from helpers import sample_config

    config = sample_config(cloudflare_api_token="integration-test-token")
    mock_load_config.return_value = config
    mock_client_factory.return_value = mock_client
    mock_load.return_value = mock_external_ips.addresses

    assert run(force=False, config_path=config_file) == 1
    mock_load_config.assert_called_once_with(config_file)
    mock_client_factory.assert_called_once_with(config)


@patch("dns_updater.cli.update_dns_entries")
@patch("dns_updater.cli.load_external_addresses")
def test_run_ipv6_only_change_triggers_update(
    mock_load: MagicMock,
    mock_update: MagicMock,
    mock_external_ips: MockExternalIps,
) -> None:
    addresses = ExternalAddresses(
        ipv4=mock_external_ips.ipv4,
        ipv4_source="mock",
        ipv6="2001:db8:home::99",
        ipv6_source="mock",
        previous_ipv4=mock_external_ips.ipv4,
        previous_ipv6=mock_external_ips.ipv6,
    )
    mock_load.return_value = addresses
    with patch("dns_updater.cli.persist_external_addresses") as mock_persist:
        assert run(force=False) == 1
        mock_persist.assert_called_once()
        mock_update.assert_called_once_with(
            mock_external_ips.ipv4,
            "2001:db8:home::99",
            config_path=None,
        )
