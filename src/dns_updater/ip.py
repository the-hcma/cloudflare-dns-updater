"""Discover the machine's current external IPv4 and IPv6 addresses."""

from __future__ import annotations

import ipaddress
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import netifaces
import requests

from dns_updater.config import IpDiscoverySettings, load_config
from dns_updater.exit_codes import EXIT_FAILURE

_LOGGER = logging.getLogger(__name__)

_STATE_DIR = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state")) / "cloudflare-dns-updater"
_IPV4_STATE_FILE = str(_STATE_DIR / "ipv4")
_IPV6_STATE_FILE = str(_STATE_DIR / "ipv6")
_NEST_STATUS_PATH: Final = "/api/v1/status"
_IPV4_FALLBACK_URLS: Final = ("https://checkip.amazonaws.com",)


@dataclass(frozen=True)
class ExternalAddresses:
    """Last-known and newly discovered external addresses."""

    ipv4: str
    ipv4_source: str
    ipv6: str | None
    ipv6_source: str | None
    previous_ipv4: str | None
    previous_ipv6: str | None

    @property
    def changed(self) -> bool:
        if self.previous_ipv4 != self.ipv4:
            return True
        return self.previous_ipv6 != self.ipv6


@dataclass(frozen=True)
class HostIpv6Candidate:
    """A globally addressable IPv6 assigned to a local network interface."""

    address: str
    interface: str
    temporary: bool = False
    deprecated: bool = False


def _read_state_file(path: str) -> str | None:
    try:
        with open(path, encoding="UTF-8") as state_file:
            return state_file.read().strip() or None
    except FileNotFoundError:
        return None


def _write_state_file(path: str, value: str) -> None:
    state_path = Path(path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    with state_path.open(encoding="UTF-8", mode="w") as state_file:
        state_file.write(value)


def _nest_status_url(nest_router_url: str) -> str:
    return f"{nest_router_url.rstrip('/')}{_NEST_STATUS_PATH}"


def _ipv6_candidate(
    raw: str,
    interface: str,
    *,
    temporary: bool,
    deprecated: bool,
) -> HostIpv6Candidate | None:
    host = raw.split("%", 1)[0]
    try:
        parsed = ipaddress.IPv6Address(host)
    except ValueError:
        return None
    if not parsed.is_global:
        return None
    return HostIpv6Candidate(
        address=str(parsed),
        interface=interface,
        temporary=temporary,
        deprecated=deprecated,
    )


def _collect_host_global_ipv6_candidates() -> list[HostIpv6Candidate]:
    candidates: list[HostIpv6Candidate] = []
    for interface in netifaces.interfaces():
        try:
            addresses = netifaces.ifaddresses(interface)
        except (OSError, ValueError) as error:
            _LOGGER.debug("netifaces.ifaddresses(%s) failed (%s)", interface, error)
            continue
        for entry in addresses.get(netifaces.AF_INET6, []):
            if not isinstance(entry, dict):
                continue
            raw = entry.get("addr")
            if not isinstance(raw, str):
                continue
            candidate = _ipv6_candidate(
                raw,
                interface,
                temporary=False,
                deprecated=False,
            )
            if candidate is not None:
                candidates.append(candidate)
    return candidates


def _select_preferred_global_ipv6(candidates: list[HostIpv6Candidate]) -> HostIpv6Candidate | None:
    if not candidates:
        return None

    def rank(candidate: HostIpv6Candidate) -> tuple[int, str]:
        score = 0
        if candidate.temporary:
            score += 2
        if candidate.deprecated:
            score += 1
        return score, candidate.address

    return min(candidates, key=rank)


def collect_ipv4_discovery_sources(nest_router_url: str | None) -> dict[str, str]:
    """Query every IPv4 source and return successful results keyed by source name."""
    sources: dict[str, str] = {}
    if nest_router_url is not None:
        nest_address = discover_ipv4_from_nest(nest_router_url)
        if nest_address is not None:
            sources["nest"] = nest_address
    for url in _IPV4_FALLBACK_URLS:
        address = _fetch_url(url)
        if address and "." in address:
            sources[url] = address
    return sources


def collect_ipv6_discovery_sources() -> dict[str, str]:
    """Return globally addressable IPv6 addresses keyed by interface name."""
    sources: dict[str, str] = {}
    for candidate in _collect_host_global_ipv6_candidates():
        key = candidate.interface or candidate.address
        sources[key] = candidate.address
    return sources


def assert_sources_agree(sources: dict[str, str], address_family: str) -> str:
    """Require all discovery sources to report the same address; return that address."""
    if not sources:
        msg = f"no {address_family} discovery sources returned an address"
        raise RuntimeError(msg)
    unique = set(sources.values())
    if len(unique) != 1:
        msg = f"{address_family} discovery sources disagree: {sources}"
        raise RuntimeError(msg)
    return unique.pop()


def validate_discovery_consistency(
    nest_router_url: str | None,
    *,
    ipv6_enabled: bool = True,
) -> tuple[str, str | None]:
    """Validate Nest/fallback IPv4 sources agree; return IPv4 and preferred host IPv6."""
    ipv4_sources = collect_ipv4_discovery_sources(nest_router_url)
    ipv4_address = assert_sources_agree(ipv4_sources, "IPv4")

    ipv6_address: str | None = None
    if ipv6_enabled:
        selected = _select_preferred_global_ipv6(_collect_host_global_ipv6_candidates())
        if selected is not None:
            ipv6_address = selected.address
    return ipv4_address, ipv6_address


def discover_ipv4_from_nest(nest_router_url: str) -> str | None:
    """Read WAN IPv4 from Google Nest / Google Wifi status API."""
    url = _nest_status_url(nest_router_url)
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as error:
        _LOGGER.debug("Nest WiFi status request failed (%s): %s", url, error)
        return None

    if not isinstance(data, dict):
        return None
    wan = data.get("wan")
    if not isinstance(wan, dict):
        return None
    address = wan.get("localIpAddress")
    if isinstance(address, str) and "." in address:
        return address.strip()
    return None


def _fetch_url(url: str) -> str | None:
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.text.strip() or None
    except requests.RequestException as error:
        _LOGGER.debug("HTTP request failed for %s (%s)", url, error)
    return None


def _log_discovered_address(address_family: str, address: str, source: str) -> None:
    _LOGGER.info("external %s %s from %s", address_family, address, source)


def discover_ipv4(discovery: IpDiscoverySettings) -> tuple[str, str]:
    """Return the current external IPv4 address and where it was discovered."""
    if discovery.nest_router_url is not None:
        nest_url = _nest_status_url(discovery.nest_router_url)
        address = discover_ipv4_from_nest(discovery.nest_router_url)
        if address:
            source = f"Nest WiFi ({nest_url})"
            _log_discovered_address("IPv4", address, source)
            return address, source
        _LOGGER.warning("Nest WiFi IPv4 lookup failed (%s); trying HTTP fallback", nest_url)

    for url in _IPV4_FALLBACK_URLS:
        address = _fetch_url(url)
        if address and "." in address:
            source = f"HTTP ({url})"
            _log_discovered_address("IPv4", address, source)
            return address, source

    msg = "failed to discover external IPv4 address"
    raise RuntimeError(msg)


def discover_ipv6(discovery: IpDiscoverySettings) -> tuple[str | None, str | None]:
    """Return the host's preferred globally addressable IPv6 and its source."""
    if not discovery.ipv6_enabled:
        _LOGGER.info("IPv6 discovery disabled in configuration")
        return None, None

    selected = _select_preferred_global_ipv6(_collect_host_global_ipv6_candidates())
    if selected is None:
        _LOGGER.info(
            "no globally addressable IPv6 on this host (set ipv6_enabled to false in config.json to skip AAAA updates)"
        )
        return None, None

    source = f"host interface ({selected.interface or 'unknown'})"
    _log_discovered_address("IPv6", selected.address, source)
    return selected.address, source


def load_external_addresses(*, config_path: Path | None = None) -> ExternalAddresses:
    """Load previous state and discover current external addresses."""
    discovery = load_config(config_path).ip_discovery
    ipv4, ipv4_source = discover_ipv4(discovery)
    ipv6, ipv6_source = discover_ipv6(discovery)
    return ExternalAddresses(
        ipv4=ipv4,
        ipv4_source=ipv4_source,
        ipv6=ipv6,
        ipv6_source=ipv6_source,
        previous_ipv4=_read_state_file(_IPV4_STATE_FILE),
        previous_ipv6=_read_state_file(_IPV6_STATE_FILE),
    )


def persist_external_addresses(addresses: ExternalAddresses) -> None:
    """Persist discovered addresses for the next run."""
    _write_state_file(_IPV4_STATE_FILE, addresses.ipv4)
    if addresses.ipv6 is not None:
        _write_state_file(_IPV6_STATE_FILE, addresses.ipv6)
    elif os.path.exists(_IPV6_STATE_FILE):
        os.remove(_IPV6_STATE_FILE)


def print_external_ipv4() -> None:
    """Print external IPv4 for shell wrappers (replaces external_ipv4_address_retriever)."""
    address, _source = discover_ipv4(load_config().ip_discovery)
    print(address)


def print_external_ipv6() -> None:
    """Print external IPv6 for shell wrappers (replaces external_ipv6_address_retriever)."""
    address, _source = discover_ipv6(load_config().ip_discovery)
    if address is None:
        raise SystemExit(EXIT_FAILURE)
    print(address)
