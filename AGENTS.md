# AGENTS.md

## Project

Python CLI (`cloudflare-dns-updater`) that discovers external IPv4/IPv6 addresses and upserts Cloudflare A/AAAA records.

## Development

```bash
uv sync --group dev
uv run ruff check .
uv run ruff format .
uv run mypy src/dns_updater
uv run pytest
```

## Conventions

- Package import path: `dns_updater` under `src/` (repo name is `cloudflare-dns-updater`).
- Console command: `cloudflare-dns-updater` (hyphens).
- Config env: `CLOUDFLARE_DNS_UPDATER_CONFIG`; token env: `CLOUDFLARE_API_TOKEN`.
- Do not commit `config.json` or API tokens.

## Repository practices

Run from [repository-helpers](https://github.com/the-hcma/repository-helpers):

```bash
scripts/check-repo-practices --repo the-hcma/cloudflare-dns-updater --suggest
```
