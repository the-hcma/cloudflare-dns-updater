# cloudflare-dns-updater

Update Cloudflare DNS **A** and **AAAA** records when your external IP address changes.

Published on [PyPI](https://pypi.org/project/cloudflare-dns-updater/) as **`cloudflare-dns-updater`**.

## Install with pipx (recommended)

[pipx](https://pipx.pypa.io/) installs the CLI in an isolated environment and puts `cloudflare-dns-updater` on your `PATH` (usually `~/.local/bin`).

```bash
# install pipx once (Debian/Ubuntu example)
sudo apt install pipx
pipx ensurepath
# open a new shell, or: source ~/.bashrc

pipx install cloudflare-dns-updater
cloudflare-dns-updater --help
```

Upgrade or reinstall later:

```bash
pipx upgrade cloudflare-dns-updater
# or pin a version:
pipx install cloudflare-dns-updater==1.0.0 --force
```

Other installers:

```bash
uv tool install cloudflare-dns-updater
pip install --user cloudflare-dns-updater   # not isolated; prefer pipx
```

## Quick start

```bash
mkdir -p ~/.config/cloudflare-dns-updater
curl -fsSL https://raw.githubusercontent.com/the-hcma/cloudflare-dns-updater/main/config.example.json \
  -o ~/.config/cloudflare-dns-updater/config.json
# edit config.json — set cloudflare_api_token, zone, and dns_entries
cloudflare-dns-updater -v -d    # dry-run: discover IPs, no Cloudflare writes
cloudflare-dns-updater          # update DNS when IPv4 or IPv6 changed
```

Create a Cloudflare API token at https://dash.cloudflare.com/profile/api-tokens with permission to edit DNS records for your zone.

### Run on a schedule (cron)

After pipx install and config are in place:

```cron
# every 5 minutes
*/5 * * * * /home/you/.local/bin/cloudflare-dns-updater >>/tmp/cloudflare-dns-updater.log 2>&1
```

Use `-f` if you want to recheck Cloudflare even when local state files show no change.

## Configuration

Settings live in **`config.json`**. Search order:

1. `-c` / `--config` path
2. `CLOUDFLARE_DNS_UPDATER_CONFIG` environment variable
3. `./config.json` in the current working directory
4. `~/.config/cloudflare-dns-updater/config.json`

Copy from **`config.example.json`**:

```json
{
  "cloudflare_api_token": "your-cloudflare-api-token",
  "zone": "example.com",
  "dns_entries": ["example.com", "home.example.com"],
  "record_ttl": 120,
  "ipv6_enabled": true
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `cloudflare_api_token` | Yes | Cloudflare API token. |
| `zone` | Yes | Cloudflare zone name. |
| `dns_entries` | Yes | Hostnames to update (A and optional AAAA). |
| `record_ttl` | No | TTL in seconds (default `120`). |
| `ipv6_enabled` | No | Set `false` to skip AAAA updates (default `true`). |
| `nest_router_url` | No | Nest / Google Wifi base URL. Omitted = `http://<LAN>.1` from your default route. Set `null` to skip Nest. |

`CLOUDFLARE_API_TOKEN` in the environment overrides only the token field in the file.

## IP discovery

### IPv4

1. **Google Nest / Wifi** — `GET {nest_router_url}/api/v1/status` → `wan.localIpAddress`
2. **Fallback** — `https://checkip.amazonaws.com`

### IPv6

The Nest status API does not expose WAN IPv6. When `ipv6_enabled` is true:

1. `https://api6.ipify.org` (via `curl -6`)
2. `https://ipv6.icanhazip.com`

## Usage

```bash
cloudflare-dns-updater          # update when IPv4 or IPv6 changed
cloudflare-dns-updater -f       # recheck Cloudflare even if local state is unchanged
cloudflare-dns-updater -d       # dry-run (no Cloudflare calls, no state file writes)
cloudflare-dns-updater -v       # verbose logging and discovery details
cloudflare-dns-updater -c /path/to/config.json
```

Run `cloudflare-dns-updater -h` for full option descriptions.

State is stored under `~/.local/state/cloudflare-dns-updater/` (override with `XDG_STATE_HOME`).

## Run from a git checkout

```bash
./bin/cloudflare-dns-updater -v -d
```

The wrapper runs `uv sync --group dev` when `.venv` is missing or `uv.lock` has changed, then invokes the CLI. You can still use `uv run cloudflare-dns-updater` directly after a manual sync.

## Development

```bash
uv sync --group dev
uv run ruff check .
uv run ruff format .
uv run mypy src/dns_updater
uv run pytest
uv run pytest -m integration   # live network checks
```

## Releases

Versioning and PyPI publish are documented in [RELEASING.md](./RELEASING.md). End users install with `pipx install cloudflare-dns-updater`.

## Repository setup

This repo follows [the-hcma](https://github.com/the-hcma) conventions. Validate with:

```bash
scripts/check-repo-practices --repo the-hcma/cloudflare-dns-updater --suggest
```

See [GRAPHITE.md](./GRAPHITE.md) for stacked PRs and the `merge-it` merge queue.
