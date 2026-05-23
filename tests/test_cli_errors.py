"""Tests for CLI error reporting."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from dns_updater.cli import main
from dns_updater.exit_codes import EXIT_FAILURE


def test_missing_config_no_traceback(tmp_path: Path) -> None:
    config_home = tmp_path / "config"
    missing = config_home / "cloudflare-dns-updater" / "config.json"
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in ("CLOUDFLARE_API_TOKEN", "CLOUDFLARE_DNS_UPDATER_CONFIG")
    }
    env["NO_COLOR"] = "1"
    env["XDG_CONFIG_HOME"] = str(config_home)

    result = subprocess.run(
        [sys.executable, "-m", "dns_updater.cli", "-c", str(missing), "-d"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env=env,
    )

    assert result.returncode == EXIT_FAILURE
    combined = result.stderr + result.stdout
    assert "Traceback" not in combined
    assert "created starter config" in combined
    assert missing.is_file()


@patch("sys.argv", ["cloudflare-dns-updater", "-f"])
@patch("dns_updater.cli.update_dns_entries")
@patch("dns_updater.cli.persist_external_addresses")
@patch("dns_updater.cli.load_external_addresses")
def test_execution_failure_exits_hard(
    mock_load: MagicMock,
    mock_persist: MagicMock,
    mock_update: MagicMock,
) -> None:
    mock_load.return_value = MagicMock(changed=True, ipv4="1.2.3.4", ipv6=None)
    mock_update.side_effect = RuntimeError("Cloudflare API error")

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == EXIT_FAILURE
