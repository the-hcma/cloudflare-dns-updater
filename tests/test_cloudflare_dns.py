"""Tests for Cloudflare DNS updates."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from helpers import MOCK_DNS_ENTRIES, sample_config

from dns_updater.cloudflare_dns import update_dns_entries, upsert_dns_record


@pytest.fixture
def mock_client() -> MagicMock:
    client = MagicMock()
    zone = MagicMock()
    zone.id = "zone-123"
    zone.name = "hcma.info"
    client.zones.list.return_value.result = [zone]
    return client


def test_upsert_dns_record_creates_when_missing(mock_client: MagicMock) -> None:
    mock_client.dns.records.list.return_value.result = []
    changed = upsert_dns_record(mock_client, "zone-123", "hcma.info", "A", "203.0.113.1", 120)
    assert changed is True
    mock_client.dns.records.create.assert_called_once()


def test_upsert_dns_record_skips_unchanged(mock_client: MagicMock) -> None:
    record = MagicMock()
    record.id = "rec-1"
    record.content = "203.0.113.1"
    mock_client.dns.records.list.return_value.result = [record]
    changed = upsert_dns_record(mock_client, "zone-123", "hcma.info", "A", "203.0.113.1", 120)
    assert changed is False
    mock_client.dns.records.update.assert_not_called()


def test_upsert_dns_record_updates_when_changed(mock_client: MagicMock) -> None:
    record = MagicMock()
    record.id = "rec-1"
    record.content = "203.0.113.1"
    record.type = "A"
    mock_client.dns.records.list.return_value.result = [record]
    changed = upsert_dns_record(mock_client, "zone-123", "hcma.info", "A", "198.51.100.2", 120)
    assert changed is True
    mock_client.dns.records.update.assert_called_once()


@patch("dns_updater.cloudflare_dns._cloudflare_client")
def test_update_dns_entries_ipv4_and_ipv6(mock_factory: MagicMock, mock_client: MagicMock) -> None:
    mock_factory.return_value = mock_client
    mock_client.dns.records.list.return_value.result = []
    config = sample_config(dns_entries=list(MOCK_DNS_ENTRIES))

    update_dns_entries("203.0.113.2", "2001:db8::2", config=config)

    assert mock_client.dns.records.create.call_count == 4
    mock_client.zones.list.assert_called_once_with(name=config.zone)


@patch("dns_updater.cloudflare_dns._cloudflare_client")
def test_update_dns_entries_custom_dns_entries(mock_factory: MagicMock, mock_client: MagicMock) -> None:
    mock_factory.return_value = mock_client
    mock_client.dns.records.list.return_value.result = []
    config = sample_config(dns_entries=["only.example.com"])

    update_dns_entries("203.0.113.2", None, config=config)

    assert mock_client.dns.records.create.call_count == 1
    mock_client.dns.records.create.assert_called_with(
        zone_id="zone-123",
        content="203.0.113.2",
        name="only.example.com",
        ttl=120,
        type="A",
    )


def test_upsert_aaaa_record_create_passes_integer_ttl(mock_client: MagicMock) -> None:
    mock_client.dns.records.list.return_value.result = []
    upsert_dns_record(mock_client, "zone-123", "hcma.info", "AAAA", "2001:db8::1", 120)
    mock_client.dns.records.create.assert_called_once_with(
        zone_id="zone-123",
        content="2001:db8::1",
        name="hcma.info",
        ttl=120,
        type="AAAA",
    )


@patch("dns_updater.cloudflare_dns._cloudflare_client")
def test_update_dns_entries_logs_when_cloudflare_already_correct(
    mock_factory: MagicMock,
    mock_client: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    mock_factory.return_value = mock_client
    record = MagicMock()
    record.id = "rec-1"
    record.content = "203.0.113.2"
    mock_client.dns.records.list.return_value.result = [record]
    config = sample_config(dns_entries=["hcma.info"])

    with caplog.at_level("INFO", logger="dns_updater.cloudflare_dns"):
        update_dns_entries("203.0.113.2", None, config=config)

    assert "already set to" in caplog.text
    assert "all 1 record(s) already match" in caplog.text


@patch("dns_updater.cloudflare_dns._cloudflare_client")
def test_update_dns_entries_ipv4_only(mock_factory: MagicMock, mock_client: MagicMock) -> None:
    mock_factory.return_value = mock_client
    mock_client.dns.records.list.return_value.result = []

    update_dns_entries("203.0.113.2", None, config=sample_config())

    assert mock_client.dns.records.create.call_count == 2


@patch.dict("os.environ", {}, clear=True)
def test_cloudflare_client_requires_token(tmp_path: Path) -> None:
    missing_config = tmp_path / "no-config.json"
    from dns_updater.config import ConfigNotFoundError

    with pytest.raises(ConfigNotFoundError, match="configuration not found"):
        update_dns_entries("203.0.113.1", None, config_path=missing_config)


@patch("dns_updater.cloudflare_dns._cloudflare_client")
def test_update_dns_entries_dry_run_skips_cloudflare(mock_factory: MagicMock) -> None:
    config = sample_config(dns_entries=["host.example.com"])
    update_dns_entries("203.0.113.2", "2001:db8::2", config=config, dry_run=True)
    mock_factory.assert_not_called()


@patch("dns_updater.cloudflare_dns.load_config")
def test_update_dns_entries_reads_zone_from_config(
    mock_load_config: MagicMock,
    mock_client: MagicMock,
) -> None:
    config = sample_config(zone="other.zone", dns_entries=["host.other.zone"])
    mock_load_config.return_value = config
    with patch("dns_updater.cloudflare_dns._cloudflare_client", return_value=mock_client):
        mock_client.dns.records.list.return_value.result = []
        update_dns_entries("10.0.0.1", None, config_path=Path("/tmp/config.json"))
    mock_load_config.assert_called_once()
    mock_client.zones.list.assert_called_once_with(name="other.zone")
