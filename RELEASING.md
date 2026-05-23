# Releasing cloudflare-dns-updater

PyPI publishing is automated from `main` via [Release Please](https://github.com/googleapis/release-please). Install for end users: `pipx install cloudflare-dns-updater`.

## One-time PyPI trusted publishing

The GitHub **`pypi`** environment already exists. Before CI can publish, add a [trusted publisher](https://docs.pypi.org/trusted-publishers/) on PyPI:

1. Sign in at [pypi.org](https://pypi.org/) (account must own the `cloudflare-dns-updater` project name).
2. Open **Your projects** → **Add new project** → register **`cloudflare-dns-updater`** (if not created yet), or open the project → **Publishing** → **Add a new pending publisher**.
3. Choose **GitHub** and set:

| Field | Value |
| --- | --- |
| Owner | `the-hcma` |
| Repository | `cloudflare-dns-updater` |
| Workflow name | `release-please.yml` |
| Environment | `pypi` |

4. Re-run the failed publish job after a release tag exists:

```bash
gh run list --repo the-hcma/cloudflare-dns-updater --workflow release-please.yml --limit 1
gh run rerun <run-id> --failed --repo the-hcma/cloudflare-dns-updater
```

Or dispatch manually when `pyproject.toml` on `main` matches the version you want:

```bash
gh workflow run release-please.yml --repo the-hcma/cloudflare-dns-updater -f version=0.1.0
```

## Merge strategy

Use **squash merge only** on `main` (`squash_merge_commit_message: BLANK`). Merge commits duplicate lines in `CHANGELOG.md` ([release-please#2476](https://github.com/googleapis/release-please/issues/2476)).

## Normal release flow

1. Land changes on `main` with [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, …).
2. Release Please opens or updates a release PR (`chore(main): release X.Y.Z`) bumping `pyproject.toml` and `CHANGELOG.md`.
   The **Release Please** workflow publishes **Ruff**, **Mypy**, and **Pytest (hermetic)** checks on that PR (bot pushes do not trigger `ci.yml`).
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
