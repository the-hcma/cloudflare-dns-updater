"""Tests for default Nest router URL resolution."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from dns_updater.config import (
    _parse_config_data,
    default_nest_router_url,
    host_dot_one,
)


def test_host_dot_one() -> None:
    assert host_dot_one("192.168.86.147") == "192.168.86.1"
    assert host_dot_one("10.0.5.254") == "10.0.5.1"


def test_host_dot_one_rejects_invalid() -> None:
    with pytest.raises(RuntimeError, match="invalid IPv4"):
        host_dot_one("not-an-ip")


@patch("dns_updater.config._ipv4_default_gateway", return_value="192.168.1.254")
def test_default_nest_router_url_uses_dot_one(mock_gateway: MagicMock) -> None:
    assert default_nest_router_url() == "http://192.168.1.1"


@patch("dns_updater.config._ipv4_default_gateway", return_value=None)
def test_default_nest_router_url_google_wifi_fallback(mock_gateway: MagicMock) -> None:
    assert default_nest_router_url() == "http://192.168.86.1"


def test_parse_config_omitted_nest_url_uses_dot_one() -> None:
    with patch("dns_updater.config.default_nest_router_url", return_value="http://10.0.0.1"):
        config = _parse_config_data(
            {
                "cloudflare_api_token": "token",
                "zone": "example.com",
                "dns_entries": ["example.com"],
            },
            Path("/test/config.json"),
        )
    assert config.ip_discovery.nest_router_url == "http://10.0.0.1"
