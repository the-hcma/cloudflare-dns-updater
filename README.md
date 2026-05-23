# cloudflare-dns-updater

Update Cloudflare DNS **A** and **AAAA** records when your external IP address changes.

## Install

```bash
pipx install cloudflare-dns-updater
# or: uv tool install cloudflare-dns-updater
```

From a git checkout:

```bash
uv sync --group dev
uv pip install -e .
```

## Quick start

```bash
mkdir -p ~/.config/cloudflare-dns-updater
cp config.example.json ~/.config/cloudflare-dns-updater/config.json
# edit config.json — set cloudflare_api_token, zone, and dns_entries
cloudflare-dns-updater -v -d
cloudflare-dns-updater
```

Create a Cloudflare API token at https://dash.cloudflare.com/profile/api-tokens with permission to edit DNS records for your zone.

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

## Development

```bash
uv sync --group dev
uv run ruff check .
uv run ruff format .
uv run mypy src
uv run pytest
uv run pytest -m integration   # live network checks
```

## Repository setup

This repo follows [the-hcma](https://github.com/the-hcma) conventions. After creating the GitHub repository:

```bash
/a_star/home/hcma/work/ai/repository-helpers/scripts/check-repo-practices \
  --new-repo --repo the-hcma/cloudflare-dns-updater --suggest
```

See [GRAPHITE.md](./GRAPHITE.md) for stacked PRs and the `merge-it` merge queue.
