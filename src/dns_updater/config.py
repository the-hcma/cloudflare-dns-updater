"""Load cloudflare-dns-updater settings from JSON configuration."""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from subprocess import run
from typing import Final

_LOGGER = logging.getLogger(__name__)

_CONFIG_ENV_VAR: Final = "CLOUDFLARE_DNS_UPDATER_CONFIG"
_TOKEN_ENV_VAR: Final = "CLOUDFLARE_API_TOKEN"
_CONFIG_DIR_NAME: Final = "cloudflare-dns-updater"
_DEFAULT_ZONE: Final = "example.com"
_DEFAULT_DNS_ENTRIES: Final = ("example.com", "home.example.com")
_DEFAULT_RECORD_TTL: Final = 120
_DEFAULT_ROUTE_VIA: Final = re.compile(r"\bvia\s+(\d+\.\d+\.\d+\.\d+)\b")


@dataclass(frozen=True)
class IpDiscoverySettings:
    """How external IPv4/IPv6 addresses are discovered."""

    ipv6_enabled: bool
    nest_router_url: str | None


@dataclass(frozen=True)
class DnsUpdaterConfig:
    """Settings loaded from config.json."""

    cloudflare_api_token: str
    zone: str
    dns_entries: tuple[str, ...]
    ip_discovery: IpDiscoverySettings
    record_ttl: int = _DEFAULT_RECORD_TTL
    config_path: Path | None = None


def _xdg_config_home() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))


def default_config_path() -> Path:
    """Return the default user config path (~/.config/cloudflare-dns-updater/config.json)."""
    return _xdg_config_home() / _CONFIG_DIR_NAME / "config.json"


def example_config_path() -> Path:
    """Return the path to config.example.json in the repository or install tree."""
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / "config.example.json"


def host_dot_one(ipv4_address: str) -> str:
    """Return the .1 host on the same /24 subnet as the reference address."""
    octets = ipv4_address.split(".")
    if len(octets) != 4:
        msg = f"invalid IPv4 address for router discovery: {ipv4_address}"
        raise RuntimeError(msg)
    octets[3] = "1"
    return ".".join(octets)


def _ipv4_default_gateway() -> str | None:
    try:
        route = run(
            ("ip", "-4", "route", "show", "default"),
            capture_output=True,
            check=True,
            text=True,
            timeout=5,
        )
    except (OSError, Exception):
        return None
    match = _DEFAULT_ROUTE_VIA.search(route.stdout)
    if match:
        return match.group(1)
    return None


def default_nest_router_url() -> str:
    """Default Nest / Google Wifi base URL: http://<LAN-subnet>.1."""
    gateway = _ipv4_default_gateway()
    if gateway is not None:
        return f"http://{host_dot_one(gateway)}"
    return "http://192.168.86.1"


def resolve_config_path(config_path: Path | None = None) -> Path:
    """Resolve the config file path from an argument, env var, cwd, or XDG default."""
    if config_path is not None:
        return config_path
    env_path = os.environ.get(_CONFIG_ENV_VAR)
    if env_path:
        return Path(env_path)
    cwd_config = Path.cwd() / "config.json"
    if cwd_config.is_file():
        return cwd_config
    return default_config_path()


def _parse_nest_router_url(data: dict[str, object], path: Path) -> str | None:
    if "nest_router_url" not in data:
        return default_nest_router_url()
    nest_raw = data["nest_router_url"]
    if nest_raw is None:
        return None
    if isinstance(nest_raw, str) and nest_raw.strip():
        return nest_raw.strip().rstrip("/")
    msg = f"nest_router_url must be a string or null in {path}"
    raise RuntimeError(msg)


def _parse_ip_discovery(data: dict[str, object], path: Path) -> IpDiscoverySettings:
    ipv6_enabled = data.get("ipv6_enabled", True)
    if not isinstance(ipv6_enabled, bool):
        msg = f"ipv6_enabled must be a boolean in {path}"
        raise RuntimeError(msg)
    return IpDiscoverySettings(
        ipv6_enabled=ipv6_enabled,
        nest_router_url=_parse_nest_router_url(data, path),
    )


def _parse_config_data(data: object, path: Path) -> DnsUpdaterConfig:
    if not isinstance(data, dict):
        msg = f"invalid config format in {path}: expected a JSON object"
        raise RuntimeError(msg)

    token = data.get("cloudflare_api_token")
    if not isinstance(token, str) or not token.strip():
        msg = f"cloudflare_api_token missing or empty in {path}"
        raise RuntimeError(msg)

    zone = data.get("zone", _DEFAULT_ZONE)
    if not isinstance(zone, str) or not zone.strip():
        msg = f"zone missing or empty in {path}"
        raise RuntimeError(msg)

    raw_entries = data.get("dns_entries", list(_DEFAULT_DNS_ENTRIES))
    if not isinstance(raw_entries, list) or not raw_entries:
        msg = f"dns_entries must be a non-empty array in {path}"
        raise RuntimeError(msg)
    dns_entries: list[str] = []
    for entry in raw_entries:
        if not isinstance(entry, str) or not entry.strip():
            msg = f"dns_entries must contain non-empty strings in {path}"
            raise RuntimeError(msg)
        dns_entries.append(entry.strip())

    record_ttl = data.get("record_ttl", _DEFAULT_RECORD_TTL)
    if not isinstance(record_ttl, (int, float)) or record_ttl <= 0:
        msg = f"record_ttl must be a positive number in {path}"
        raise RuntimeError(msg)
    if isinstance(record_ttl, float) and not record_ttl.is_integer():
        msg = f"record_ttl must be a whole number of seconds in {path}"
        raise RuntimeError(msg)

    return DnsUpdaterConfig(
        cloudflare_api_token=token.strip(),
        zone=zone.strip(),
        dns_entries=tuple(dns_entries),
        ip_discovery=_parse_ip_discovery(data, path),
        record_ttl=int(record_ttl),
        config_path=path,
    )


def _log_config_source(path: Path, *, token_from_env: bool, config_file_used: bool) -> None:
    """Log where settings are loaded from without printing secrets."""
    resolved = path.resolve()
    if token_from_env and config_file_used:
        _LOGGER.debug(
            "loading settings from %s (Cloudflare API token from %s environment variable)",
            resolved,
            _TOKEN_ENV_VAR,
        )
        return
    if token_from_env:
        _LOGGER.debug(
            "using built-in defaults for zone, DNS entries, and IP discovery "
            "(Cloudflare API token from %s environment variable; config file not found at %s)",
            _TOKEN_ENV_VAR,
            resolved,
        )
        return
    _LOGGER.debug("loading configuration from %s", resolved)


def load_config(config_path: Path | None = None) -> DnsUpdaterConfig:
    """Load full settings from env (token only) or JSON config file."""
    env_token = os.environ.get(_TOKEN_ENV_VAR)
    path = resolve_config_path(config_path)
    token_from_env = bool(env_token and env_token.strip())

    if token_from_env:
        assert env_token is not None
        api_token = env_token.strip()
        if path.is_file():
            with open(path, encoding="UTF-8") as config_file:
                data = json.load(config_file)
            config = _parse_config_data(data, path)
            _log_config_source(path, token_from_env=True, config_file_used=True)
            return DnsUpdaterConfig(
                cloudflare_api_token=api_token,
                zone=config.zone,
                dns_entries=config.dns_entries,
                ip_discovery=config.ip_discovery,
                record_ttl=config.record_ttl,
                config_path=path,
            )
        _log_config_source(path, token_from_env=True, config_file_used=False)
        return DnsUpdaterConfig(
            cloudflare_api_token=api_token,
            zone=_DEFAULT_ZONE,
            dns_entries=_DEFAULT_DNS_ENTRIES,
            ip_discovery=IpDiscoverySettings(ipv6_enabled=True, nest_router_url=default_nest_router_url()),
            record_ttl=_DEFAULT_RECORD_TTL,
            config_path=path if path.is_file() else None,
        )

    if not path.is_file():
        msg = f"configuration not found: create {path} from config.example.json or set {_TOKEN_ENV_VAR}"
        raise RuntimeError(msg)

    with open(path, encoding="UTF-8") as config_file:
        data = json.load(config_file)
    _log_config_source(path, token_from_env=False, config_file_used=True)
    return _parse_config_data(data, path)


def load_cloudflare_api_token(config_path: Path | None = None) -> str:
    """Load the Cloudflare API token from env or JSON config."""
    return load_config(config_path).cloudflare_api_token
