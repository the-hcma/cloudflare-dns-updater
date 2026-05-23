"""Tests for CLI error reporting."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


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

    assert result.returncode == 1
    combined = result.stderr + result.stdout
    assert "Traceback" not in combined
    assert "created starter config" in combined
    assert missing.is_file()
