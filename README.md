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

## Repository setup

This repo follows [the-hcma](https://github.com/the-hcma) conventions.

```bash
# from a clone of https://github.com/the-hcma/repository-helpers
scripts/check-repo-practices --repo the-hcma/cloudflare-dns-updater --suggest
```

After the **`merge-it`** label exists, the checker enforces Graphite merge-queue wiring, `protect-main`, and classic `main` protection (see [repository-helpers AGENTS.md](https://github.com/the-hcma/repository-helpers/blob/main/AGENTS.md)). Until onboarding is complete, expect a non-zero exit.

| Step | Status |
| --- | --- |
| Workflows (`ci.yml`, cleanup, `merged-pr-closer`, dependabot auto-merge) | in repo |
| **`merge-it`** label | created |
| Squash-only merge settings | applied |
| **`protect-main`** ruleset + classic `main` protection | **pending** — GitHub API returns 403 on private repos without Pro ([enable rulesets](https://github.com/the-hcma/cloudflare-dns-updater/settings/rules) / [branch protection](https://github.com/the-hcma/cloudflare-dns-updater/settings/branches) in the UI, or run `check-repo-practices --apply` once available) |
| Graphite merge queue on `main` (squash, label `merge-it`) | **manual** in [Graphite settings](https://app.graphite.com/settings/merge-queue) |

`check-repo-practices --new-repo` currently passes before `merge-it` exists; see [repository-helpers#144](https://github.com/the-hcma/repository-helpers/issues/144).

See [GRAPHITE.md](./GRAPHITE.md) for stacked PRs and the `merge-it` merge queue.
