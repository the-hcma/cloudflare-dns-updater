"""Create or update Cloudflare DNS records."""

from __future__ import annotations

import logging
from pathlib import Path

import requests
from cloudflare import Cloudflare

from dns_updater.config import DnsUpdaterConfig, load_config

_LOGGER = logging.getLogger(__name__)

# Cloudflare API calls are more reliable over IPv4 on this host.
requests.packages.urllib3.util.connection.HAS_IPV6 = False  # type: ignore[attr-defined]


def _cloudflare_client(config: DnsUpdaterConfig) -> Cloudflare:
    return Cloudflare(api_token=config.cloudflare_api_token)


def _get_zone(client: Cloudflare, zone_name: str) -> object:
    zones = client.zones.list(name=zone_name)
    if not zones.result:
        msg = f"Cloudflare zone not found: {zone_name}"
        raise RuntimeError(msg)
    return zones.result[0]


def _get_dns_record(client: Cloudflare, zone_id: str, name: str, record_type: str) -> object | None:
    records = client.dns.records.list(zone_id=zone_id, name=name, type=record_type)  # type: ignore[arg-type]
    if not records.result:
        return None
    return records.result[0]


def _upsert_a_record(
    client: Cloudflare,
    zone_id: str,
    name: str,
    content: str,
    record_ttl: int,
) -> bool:
    record = _get_dns_record(client, zone_id, name, "A")
    if record is None:
        client.dns.records.create(
            zone_id=zone_id,
            content=content,
            name=name,
            ttl=record_ttl,
            type="A",
        )
        _LOGGER.warning("registered A %s -> %s", name, content)
        return True
    record_content = getattr(record, "content", None)
    record_id = getattr(record, "id", None)
    if not isinstance(record_id, str):
        msg = f"missing DNS record id for A {name}"
        raise RuntimeError(msg)
    if record_content == content:
        _LOGGER.info("Cloudflare A %s already set to %s", name, content)
        return False
    client.dns.records.update(
        dns_record_id=record_id,
        zone_id=zone_id,
        content=content,
        name=name,
        ttl=record_ttl,
        type="A",
    )
    _LOGGER.warning("updated A %s -> %s (was %s)", name, content, record_content)
    return True


def _upsert_aaaa_record(
    client: Cloudflare,
    zone_id: str,
    name: str,
    content: str,
    record_ttl: int,
) -> bool:
    record = _get_dns_record(client, zone_id, name, "AAAA")
    if record is None:
        client.dns.records.create(
            zone_id=zone_id,
            content=content,
            name=name,
            ttl=record_ttl,
            type="AAAA",
        )
        _LOGGER.warning("registered AAAA %s -> %s", name, content)
        return True
    record_content = getattr(record, "content", None)
    record_id = getattr(record, "id", None)
    if not isinstance(record_id, str):
        msg = f"missing DNS record id for AAAA {name}"
        raise RuntimeError(msg)
    if record_content == content:
        _LOGGER.info("Cloudflare AAAA %s already set to %s", name, content)
        return False
    client.dns.records.update(
        dns_record_id=record_id,
        zone_id=zone_id,
        content=content,
        name=name,
        ttl=record_ttl,
        type="AAAA",
    )
    _LOGGER.warning("updated AAAA %s -> %s (was %s)", name, content, record_content)
    return True


def upsert_dns_record(
    client: Cloudflare,
    zone_id: str,
    name: str,
    record_type: str,
    content: str,
    record_ttl: int,
) -> bool:
    """Create or update a DNS record. Returns True if the record changed."""
    if record_type == "A":
        return _upsert_a_record(client, zone_id, name, content, record_ttl)
    if record_type == "AAAA":
        return _upsert_aaaa_record(client, zone_id, name, content, record_ttl)
    msg = f"unsupported record type: {record_type}"
    raise ValueError(msg)


def _log_planned_dns_updates(
    settings: DnsUpdaterConfig,
    ipv4_address: str,
    ipv6_address: str | None,
) -> None:
    for entry in settings.dns_entries:
        _LOGGER.warning(
            "[dry-run] would set A %s -> %s (ttl %s, zone %s)",
            entry,
            ipv4_address,
            settings.record_ttl,
            settings.zone,
        )
        if ipv6_address is not None:
            _LOGGER.warning(
                "[dry-run] would set AAAA %s -> %s (ttl %s, zone %s)",
                entry,
                ipv6_address,
                settings.record_ttl,
                settings.zone,
            )


def update_dns_entries(
    ipv4_address: str,
    ipv6_address: str | None,
    *,
    config: DnsUpdaterConfig | None = None,
    config_path: Path | None = None,
    dry_run: bool = False,
) -> None:
    """Update A and optional AAAA records for configured hostnames."""
    settings = config or load_config(config_path)
    if dry_run:
        _log_planned_dns_updates(settings, ipv4_address, ipv6_address)
        return

    client = _cloudflare_client(settings)
    zone = _get_zone(client, settings.zone)
    zone_id_value = getattr(zone, "id", None)
    if not isinstance(zone_id_value, str):
        msg = f"invalid Cloudflare zone id for {settings.zone}"
        raise RuntimeError(msg)
    zone_id = zone_id_value
    zone_label = getattr(zone, "name", settings.zone)
    _LOGGER.debug("using zone %s (%s)", zone_label, zone_id)

    records_checked = 0
    records_changed = 0
    for entry in settings.dns_entries:
        try:
            if _upsert_a_record(client, zone_id, entry, ipv4_address, settings.record_ttl):
                records_changed += 1
            records_checked += 1
            if ipv6_address is not None:
                if _upsert_aaaa_record(client, zone_id, entry, ipv6_address, settings.record_ttl):
                    records_changed += 1
                records_checked += 1
        except Exception as error:
            msg = f"failed to update DNS for {entry}"
            raise RuntimeError(msg) from error

    if records_changed == 0:
        _LOGGER.warning(
            "Cloudflare: all %d record(s) already match discovered addresses",
            records_checked,
        )
    else:
        _LOGGER.warning(
            "Cloudflare: updated %d of %d record(s)",
            records_changed,
            records_checked,
        )
