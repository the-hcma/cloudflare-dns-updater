"""Test helpers and mock data."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from cloudflare_dns_updater.config import DnsUpdaterConfig, _parse_config_data
from cloudflare_dns_updater.ip import ExternalAddresses

MOCK_IPV4: Final = "203.0.113.50"
MOCK_IPV6: Final = "2001:db8:home::50"
MOCK_IPV4_PREVIOUS: Final = "198.51.100.40"
MOCK_IPV6_PREVIOUS: Final = "2001:db8:home::40"
MOCK_ZONE: Final = "hcma.info"
MOCK_DNS_ENTRIES: Final = ("hcma.info", "ny.hcma.info")
MOCK_API_TOKEN: Final = "test-api-token"


@dataclass(frozen=True)
class MockExternalIps:
    """Fixture values for mocked external IP discovery."""

    ipv4: str = MOCK_IPV4
    ipv6: str | None = MOCK_IPV6
    previous_ipv4: str | None = MOCK_IPV4_PREVIOUS
    previous_ipv6: str | None = MOCK_IPV6_PREVIOUS

    @property
    def addresses(self) -> ExternalAddresses:
        return ExternalAddresses(
            ipv4=self.ipv4,
            ipv4_source="mock",
            ipv6=self.ipv6,
            ipv6_source="mock" if self.ipv6 else None,
            previous_ipv4=self.previous_ipv4,
            previous_ipv6=self.previous_ipv6,
        )

    @property
    def unchanged_addresses(self) -> ExternalAddresses:
        return ExternalAddresses(
            ipv4=self.ipv4,
            ipv4_source="mock",
            ipv6=self.ipv6,
            ipv6_source="mock" if self.ipv6 else None,
            previous_ipv4=self.ipv4,
            previous_ipv6=self.ipv6,
        )


def sample_config_dict(
    *,
    token: str = MOCK_API_TOKEN,
    zone: str = MOCK_ZONE,
    dns_entries: list[str] | None = None,
    record_ttl: int = 120,
    ipv6_enabled: bool = True,
    nest_router_url: str | None = "http://192.168.86.1",
) -> dict[str, object]:
    """Build a config.json-shaped dict for tests."""
    entries = list(MOCK_DNS_ENTRIES) if dns_entries is None else dns_entries
    return {
        "cloudflare_api_token": token,
        "zone": zone,
        "dns_entries": entries,
        "record_ttl": record_ttl,
        "ipv6_enabled": ipv6_enabled,
        "nest_router_url": nest_router_url,
    }


def write_config_file(path: Path, **overrides: object) -> Path:
    """Write a config.json file and return its path."""
    data = sample_config_dict()
    data.update(overrides)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="UTF-8")
    return path


def sample_config(**overrides: object) -> DnsUpdaterConfig:
    """Build a DnsUpdaterConfig for tests."""
    data = sample_config_dict()
    data.update(overrides)
    return _parse_config_data(data, Path("/test/config.json"))
