"""Tests for external IP discovery."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from helpers import sample_config

from cloudflare_dns_updater.config import IpDiscoverySettings
from cloudflare_dns_updater.ip import (
    ExternalAddresses,
    discover_ipv4,
    discover_ipv4_from_nest,
    discover_ipv6,
    load_external_addresses,
    persist_external_addresses,
)


def _discovery(**overrides: object) -> IpDiscoverySettings:
    return sample_config(**overrides).ip_discovery


def test_external_addresses_changed_ipv4() -> None:
    addresses = ExternalAddresses(
        ipv4="1.2.3.4",
        ipv4_source="test",
        ipv6=None,
        ipv6_source=None,
        previous_ipv4="5.6.7.8",
        previous_ipv6=None,
    )
    assert addresses.changed is True


def test_external_addresses_unchanged() -> None:
    addresses = ExternalAddresses(
        ipv4="1.2.3.4",
        ipv4_source="test",
        ipv6="2001:db8::1",
        ipv6_source="test",
        previous_ipv4="1.2.3.4",
        previous_ipv6="2001:db8::1",
    )
    assert addresses.changed is False


def test_discover_ipv4_from_nest() -> None:
    mock_response = MagicMock()
    mock_response.json.return_value = {"wan": {"localIpAddress": "98.116.127.147"}}
    with patch("cloudflare_dns_updater.ip.requests.get", return_value=mock_response):
        assert discover_ipv4_from_nest("http://192.168.86.1") == "98.116.127.147"


@patch("cloudflare_dns_updater.ip.discover_ipv4_from_nest", return_value="203.0.113.10")
def test_discover_ipv4_prefers_nest(mock_nest: MagicMock) -> None:
    address, source = discover_ipv4(_discovery())
    assert address == "203.0.113.10"
    assert "Nest WiFi" in source
    mock_nest.assert_called_once_with("http://192.168.86.1")


@patch("cloudflare_dns_updater.ip._fetch_url", return_value="198.51.100.1")
@patch("cloudflare_dns_updater.ip.discover_ipv4_from_nest", return_value=None)
def test_discover_ipv4_http_fallback(mock_nest: MagicMock, mock_fetch: MagicMock) -> None:
    address, source = discover_ipv4(_discovery())
    assert address == "198.51.100.1"
    assert source.startswith("HTTP (")


@patch("cloudflare_dns_updater.ip._fetch_url", return_value="198.51.100.2")
@patch("cloudflare_dns_updater.ip.discover_ipv4_from_nest")
def test_discover_ipv4_skips_nest_when_disabled(mock_nest: MagicMock, mock_fetch: MagicMock) -> None:
    address, source = discover_ipv4(_discovery(nest_router_url=None))
    assert address == "198.51.100.2"
    assert source.startswith("HTTP (")
    mock_nest.assert_not_called()


@patch("cloudflare_dns_updater.ip._fetch_url", return_value="2001:db8::2")
def test_discover_ipv6_from_url(mock_fetch: MagicMock) -> None:
    address, source = discover_ipv6(_discovery())
    assert address == "2001:db8::2"
    assert "api6.ipify.org" in source


def test_discover_ipv6_disabled() -> None:
    address, source = discover_ipv6(_discovery(ipv6_enabled=False))
    assert address is None
    assert source is None


@patch("cloudflare_dns_updater.ip._fetch_url", return_value=None)
def test_discover_ipv6_unavailable(mock_fetch: MagicMock) -> None:
    address, source = discover_ipv6(_discovery())
    assert address is None
    assert source is None


@patch("cloudflare_dns_updater.ip.discover_ipv6", return_value=("2001:db8::5", "HTTP curl -6 (https://api6.ipify.org)"))
@patch(
    "cloudflare_dns_updater.ip.discover_ipv4",
    return_value=("203.0.113.5", "Nest WiFi (http://192.168.86.1/api/v1/status)"),
)
@patch("cloudflare_dns_updater.ip.load_config")
@patch("cloudflare_dns_updater.ip._read_state_file", side_effect=["203.0.113.5", "2001:db8::5"])
def test_load_external_addresses(
    mock_read: MagicMock,
    mock_load_config: MagicMock,
    mock_v4: MagicMock,
    mock_v6: MagicMock,
) -> None:
    mock_load_config.return_value = sample_config()
    addresses = load_external_addresses()
    assert addresses.ipv4 == "203.0.113.5"
    assert addresses.ipv6 == "2001:db8::5"
    assert addresses.changed is False


def test_persist_external_addresses(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ipv4_file = tmp_path / "ipv4"
    ipv6_file = tmp_path / "ipv6"
    monkeypatch.setattr("cloudflare_dns_updater.ip._IPV4_STATE_FILE", str(ipv4_file))
    monkeypatch.setattr("cloudflare_dns_updater.ip._IPV6_STATE_FILE", str(ipv6_file))

    addresses = ExternalAddresses(
        ipv4="203.0.113.9",
        ipv4_source="test",
        ipv6="2001:db8::9",
        ipv6_source="test",
        previous_ipv4=None,
        previous_ipv6=None,
    )
    persist_external_addresses(addresses)
    assert ipv4_file.read_text(encoding="UTF-8") == "203.0.113.9"
    assert ipv6_file.read_text(encoding="UTF-8") == "2001:db8::9"
