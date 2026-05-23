"""Tests for external IP discovery."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import netifaces
import pytest
from helpers import sample_config

from dns_updater.config import IpDiscoverySettings
from dns_updater.ip import (
    ExternalAddresses,
    HostIpv6Candidate,
    _collect_host_global_ipv6_candidates,
    _select_preferred_global_ipv6,
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
    with patch("dns_updater.ip.requests.get", return_value=mock_response):
        assert discover_ipv4_from_nest("http://192.168.86.1") == "98.116.127.147"


@patch("dns_updater.ip.discover_ipv4_from_nest", return_value="203.0.113.10")
def test_discover_ipv4_prefers_nest(mock_nest: MagicMock) -> None:
    address, source = discover_ipv4(_discovery())
    assert address == "203.0.113.10"
    assert "Nest WiFi" in source
    mock_nest.assert_called_once_with("http://192.168.86.1")


@patch("dns_updater.ip._fetch_url", return_value="198.51.100.1")
@patch("dns_updater.ip.discover_ipv4_from_nest", return_value=None)
def test_discover_ipv4_http_fallback(mock_nest: MagicMock, mock_fetch: MagicMock) -> None:
    address, source = discover_ipv4(_discovery())
    assert address == "198.51.100.1"
    assert source.startswith("HTTP (")


@patch("dns_updater.ip._fetch_url", return_value="198.51.100.2")
@patch("dns_updater.ip.discover_ipv4_from_nest")
def test_discover_ipv4_skips_nest_when_disabled(mock_nest: MagicMock, mock_fetch: MagicMock) -> None:
    address, source = discover_ipv4(_discovery(nest_router_url=None))
    assert address == "198.51.100.2"
    assert source.startswith("HTTP (")
    mock_nest.assert_not_called()


@patch("dns_updater.ip.netifaces.interfaces", return_value=["lo0", "en0"])
@patch("dns_updater.ip.netifaces.ifaddresses")
def test_collect_host_global_ipv6_via_netifaces(mock_ifaddresses: MagicMock, mock_interfaces: MagicMock) -> None:
    mock_ifaddresses.side_effect = lambda iface: {
        "lo0": {netifaces.AF_INET6: [{"addr": "::1"}]},
        "en0": {
            netifaces.AF_INET6: [
                {"addr": "fe80::1%en0"},
                {"addr": "2600:4041:5f4a:7200::10"},
                {"addr": "2600:4041:5f4a:7200::11"},
            ],
        },
    }[iface]

    candidates = _collect_host_global_ipv6_candidates()
    assert [candidate.address for candidate in candidates] == [
        "2600:4041:5f4a:7200::10",
        "2600:4041:5f4a:7200::11",
    ]
    mock_interfaces.assert_called_once()


def test_select_preferred_global_ipv6() -> None:
    candidates = [
        HostIpv6Candidate("2600:4041:5f4a:7200::1", "en0", temporary=True),
        HostIpv6Candidate("2600:4041:5f4a:7200::2", "en0", deprecated=True),
        HostIpv6Candidate("2600:4041:5f4a:7200::3", "en0"),
    ]
    selected = _select_preferred_global_ipv6(candidates)
    assert selected is not None
    assert selected.address == "2600:4041:5f4a:7200::3"


@patch(
    "dns_updater.ip._collect_host_global_ipv6_candidates",
    return_value=[HostIpv6Candidate("2600:4041:5f4a:7200::2", "en0")],
)
def test_discover_ipv6_from_host_interface(mock_collect: MagicMock) -> None:
    address, source = discover_ipv6(_discovery())
    assert address == "2600:4041:5f4a:7200::2"
    assert source == "host interface (en0)"
    mock_collect.assert_called_once()


def test_discover_ipv6_disabled() -> None:
    address, source = discover_ipv6(_discovery(ipv6_enabled=False))
    assert address is None
    assert source is None


@patch("dns_updater.ip._collect_host_global_ipv6_candidates", return_value=[])
def test_discover_ipv6_unavailable(mock_collect: MagicMock) -> None:
    address, source = discover_ipv6(_discovery())
    assert address is None
    assert source is None
    mock_collect.assert_called_once()


@patch("dns_updater.ip.discover_ipv6", return_value=("2001:db8::5", "host interface (en0)"))
@patch(
    "dns_updater.ip.discover_ipv4",
    return_value=("203.0.113.5", "Nest WiFi (http://192.168.86.1/api/v1/status)"),
)
@patch("dns_updater.ip.load_config")
@patch("dns_updater.ip._read_state_file", side_effect=["203.0.113.5", "2001:db8::5"])
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
    monkeypatch.setattr("dns_updater.ip._IPV4_STATE_FILE", str(ipv4_file))
    monkeypatch.setattr("dns_updater.ip._IPV6_STATE_FILE", str(ipv6_file))

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
