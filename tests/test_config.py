"""Tests for JSON configuration loading."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest
from helpers import MOCK_DNS_ENTRIES, MOCK_ZONE, sample_config_dict, write_config_file

from dns_updater.config import (
    ConfigNotFoundError,
    default_config_path,
    example_config_path,
    load_cloudflare_api_token,
    load_config,
    resolve_config_path,
    write_sample_config,
)


def test_load_config_logs_source_at_debug(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CLOUDFLARE_API_TOKEN", raising=False)
    config_file = write_config_file(tmp_path / "config.json")
    with caplog.at_level(logging.DEBUG, logger="dns_updater.config"):
        load_config(config_file)
    assert len(caplog.records) == 1
    assert "loading configuration from" in caplog.records[0].message
    assert str(config_file.resolve()) in caplog.records[0].message
    assert "test-api-token" not in caplog.text


def test_load_config_logs_env_token_source(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_file = write_config_file(tmp_path / "config.json")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "token-from-env")
    with caplog.at_level(logging.DEBUG, logger="dns_updater.config"):
        load_config(config_file)
    assert "loading settings from" in caplog.text
    assert "CLOUDFLARE_API_TOKEN environment variable" in caplog.text
    assert "token-from-env" not in caplog.text
    assert "test-api-token" not in caplog.text


def test_load_config_from_json(tmp_path: Path) -> None:
    config_file = write_config_file(tmp_path / "config.json")
    config = load_config(config_file)
    assert config.cloudflare_api_token == "test-api-token"
    assert config.zone == MOCK_ZONE
    assert config.dns_entries == MOCK_DNS_ENTRIES
    assert config.record_ttl == 120


def test_load_token_from_json(tmp_path: Path) -> None:
    config_file = write_config_file(tmp_path / "config.json")
    assert load_cloudflare_api_token(config_file) == "test-api-token"


def test_env_overrides_token_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_file = write_config_file(
        tmp_path / "config.json",
        zone="custom.zone",
        dns_entries=["a.custom.zone", "b.custom.zone"],
    )
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "token-from-env")
    config = load_config(config_file)
    assert config.cloudflare_api_token == "token-from-env"
    assert config.zone == "custom.zone"
    assert config.dns_entries == ("a.custom.zone", "b.custom.zone")


def test_missing_config_writes_sample(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLOUDFLARE_API_TOKEN", raising=False)
    missing = tmp_path / "cloudflare-dns-updater" / "config.json"
    with pytest.raises(ConfigNotFoundError) as exc_info:
        load_config(missing)
    assert exc_info.value.sample_written is True
    assert missing.is_file()
    assert "your-cloudflare-api-token" in missing.read_text(encoding="utf-8")


def test_write_sample_config_skips_existing(tmp_path: Path) -> None:
    dest = tmp_path / "config.json"
    dest.write_text("{}", encoding="utf-8")
    assert write_sample_config(dest) is False


def test_empty_token_in_json_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLOUDFLARE_API_TOKEN", raising=False)
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"cloudflare_api_token": ""}), encoding="UTF-8")
    with pytest.raises(RuntimeError, match="cloudflare_api_token missing"):
        load_config(config_file)


def test_empty_dns_entries_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLOUDFLARE_API_TOKEN", raising=False)
    config_file = tmp_path / "config.json"
    config_file.write_text(
        json.dumps(sample_config_dict(dns_entries=[])),
        encoding="UTF-8",
    )
    with pytest.raises(RuntimeError, match="dns_entries must be a non-empty array"):
        load_config(config_file)


def test_resolve_config_path_from_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    custom = tmp_path / "custom.json"
    monkeypatch.setenv("CLOUDFLARE_DNS_UPDATER_CONFIG", str(custom))
    assert resolve_config_path() == custom


def test_load_example_config_file() -> None:
    """The committed template must parse with all required fields."""
    path = example_config_path()
    assert path.is_file(), f"missing {path}"
    config = load_config(path)
    assert config.zone == "example.com"
    assert "example.com" in config.dns_entries
    assert config.record_ttl > 0
    assert config.ip_discovery.ipv6_enabled is True
    assert config.ip_discovery.nest_router_url is not None
    assert config.ip_discovery.nest_router_url.endswith(".1")
    assert config.ip_discovery.nest_router_url.startswith("http://")


def test_ipv6_disabled_in_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLOUDFLARE_API_TOKEN", raising=False)
    config_file = write_config_file(tmp_path / "config.json", ipv6_enabled=False)
    config = load_config(config_file)
    assert config.ip_discovery.ipv6_enabled is False


def test_load_project_config_json() -> None:
    """The local config.json (git-ignored) must exist and parse with required fields."""
    path = default_config_path()
    if not path.is_file():
        pytest.skip(f"{path} not present (copy config.example.json)")
    config = load_config(path)
    assert config.zone.strip()
    assert len(config.dns_entries) >= 1
    assert all(entry.strip() for entry in config.dns_entries)
    assert config.cloudflare_api_token.strip()
    assert config.record_ttl > 0
