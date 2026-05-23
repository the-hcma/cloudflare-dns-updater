# Releasing cloudflare-dns-updater

PyPI publishing is automated from `main` via [Release Please](https://github.com/googleapis/release-please). Install for end users: `pipx install cloudflare-dns-updater`.

## One-time PyPI trusted publishing

Before the first workflow publish succeeds, configure [trusted publishing](https://docs.pypi.org/trusted-publishers/) on [PyPI](https://pypi.org/manage/project/cloudflare-dns-updater/settings/publishing/) (the project is created on first upload if it does not exist yet):

| Field | Value |
| --- | --- |
| Owner | `the-hcma` |
| Repository | `cloudflare-dns-updater` |
| Workflow name | `release-please.yml` |
| Environment | `pypi` |

Create the matching GitHub environment (no required reviewers needed for publish):

```bash
gh api --method PUT "repos/the-hcma/cloudflare-dns-updater/environments/pypi"
```

## Merge strategy

Use **squash merge only** on `main` (`squash_merge_commit_message: BLANK`). Merge commits duplicate lines in `CHANGELOG.md` ([release-please#2476](https://github.com/googleapis/release-please/issues/2476)).

## Normal release flow

1. Land changes on `main` with [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, …).
2. Release Please opens or updates a release PR (`chore(main): release X.Y.Z`) bumping `pyproject.toml` and `CHANGELOG.md`.
3. Merge the release PR (add **`merge-it`** when using Graphite merge queue).
4. GitHub tags the release and **Release Please** runs **Publish to PyPI**.

## Manual publish (fallback)

When OIDC publish fails or you need a one-off release:

```bash
uv sync --group dev
uv run ruff check .
uv run mypy src/dns_updater
uv run pytest -m "not integration"
# set version in pyproject.toml, update CHANGELOG.md
uv build
uv publish   # or: gh workflow run release-please.yml -f version=1.0.0
```

Trusted publishing via workflow dispatch: set `version` to match `[project].version` in `pyproject.toml` on `main`.

## After publish

```bash
pipx install cloudflare-dns-updater
pipx upgrade cloudflare-dns-updater   # later updates
cloudflare-dns-updater --help
```

See [README.md](./README.md) for configuration and cron examples.
