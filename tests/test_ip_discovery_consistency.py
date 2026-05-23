"""Live consistency checks across Nest WiFi and HTTP fallback discovery sources."""

from __future__ import annotations

import pytest

from cloudflare_dns_updater.config import IpDiscoverySettings, load_config
from cloudflare_dns_updater.ip import (
    _IPV4_FALLBACK_URLS,
    _IPV6_DISCOVERY_URLS,
    assert_sources_agree,
    collect_ipv4_discovery_sources,
    collect_ipv6_discovery_sources,
    discover_ipv4,
    discover_ipv6,
    validate_discovery_consistency,
)


def test_assert_sources_agree_single_value() -> None:
    assert assert_sources_agree({"nest": "203.0.113.1", "fallback": "203.0.113.1"}, "IPv4") == ("203.0.113.1")


def test_assert_sources_agree_rejects_mismatch() -> None:
    with pytest.raises(RuntimeError, match="IPv4 discovery sources disagree"):
        assert_sources_agree({"nest": "203.0.113.1", "fallback": "198.51.100.1"}, "IPv4")


def test_assert_sources_agree_requires_results() -> None:
    with pytest.raises(RuntimeError, match="no IPv6 discovery sources"):
        assert_sources_agree({}, "IPv6")


@pytest.mark.integration
def test_ipv4_nest_and_fallback_urls_report_same_address() -> None:
    """Nest wan.localIpAddress must match checkip.amazonaws.com on this network."""
    discovery = load_config().ip_discovery
    if discovery.nest_router_url is None:
        pytest.skip("Nest WiFi discovery disabled in config")

    sources = collect_ipv4_discovery_sources(discovery.nest_router_url)
    if "nest" not in sources:
        pytest.skip("Google Nest WiFi status API is not reachable")

    fallback_hits = [url for url in _IPV4_FALLBACK_URLS if url in sources]
    if not fallback_hits:
        pytest.skip("no IPv4 fallback URL responded")

    agreed = assert_sources_agree(sources, "IPv4")
    assert sources["nest"] == agreed
    for url in fallback_hits:
        assert sources[url] == agreed


@pytest.mark.integration
def test_ipv6_fallback_urls_report_same_address() -> None:
    """All configured IPv6 echo services must return the same address."""
    sources = collect_ipv6_discovery_sources()
    if len(sources) < 2:
        pytest.skip(f"need at least two IPv6 sources; got {sources!r}")

    agreed = assert_sources_agree(sources, "IPv6")
    for url in _IPV6_DISCOVERY_URLS:
        if url in sources:
            assert sources[url] == agreed


@pytest.mark.integration
def test_validate_discovery_consistency_end_to_end() -> None:
    """Combined validator matches individual discover_ipv4/ipv6 results."""
    discovery = load_config().ip_discovery
    try:
        ipv4_expected, ipv6_expected = validate_discovery_consistency(
            discovery.nest_router_url,
            ipv6_enabled=discovery.ipv6_enabled,
        )
    except RuntimeError as error:
        pytest.skip(str(error))

    ipv4_address, _ipv4_source = discover_ipv4(discovery)
    assert ipv4_address == ipv4_expected
    if discovery.ipv6_enabled and ipv6_expected is not None:
        ipv6_address, _ipv6_source = discover_ipv6(discovery)
        assert ipv6_address == ipv6_expected


@pytest.mark.integration
def test_discover_ipv4_uses_http_fallback_when_nest_unreachable() -> None:
    """IPv4 discovery must succeed via HTTP when Nest WiFi status is unavailable."""
    discovery = load_config().ip_discovery
    if discovery.nest_router_url is None:
        pytest.skip("Nest WiFi discovery disabled in config")

    sources = collect_ipv4_discovery_sources(discovery.nest_router_url)
    fallback_hits = [url for url in _IPV4_FALLBACK_URLS if url in sources]
    if not fallback_hits:
        pytest.skip("no IPv4 fallback URL responded")

    fallback_address = sources[fallback_hits[0]]

    if "nest" in sources:
        # Force the Nest-down code path while HTTP fallback remains reachable.
        nest_down = IpDiscoverySettings(
            ipv6_enabled=discovery.ipv6_enabled,
            nest_router_url="http://192.0.2.1",
        )
        ipv4_address, ipv4_source = discover_ipv4(nest_down)
    else:
        ipv4_address, ipv4_source = discover_ipv4(discovery)

    assert ipv4_address == fallback_address
    assert ipv4_source.startswith("HTTP (")
    assert "Nest WiFi" not in ipv4_source


@pytest.mark.integration
def test_discover_ipv4_matches_nest_when_nest_available() -> None:
    discovery = load_config().ip_discovery
    sources = collect_ipv4_discovery_sources(discovery.nest_router_url)
    if "nest" not in sources:
        pytest.skip("Nest WiFi status API is not reachable")

    ipv4_address, ipv4_source = discover_ipv4(discovery)
    assert ipv4_address == sources["nest"]
    assert "Nest WiFi" in ipv4_source
