# AGENTS.md — Ground Rules for cloudflare-dns-updater

This file defines the standards for all contributors (human or AI) working on this codebase. Every change must comply with these rules before it is considered complete.

---

## Project

Python CLI (`cloudflare-dns-updater`) that discovers external IPv4/IPv6 addresses and upserts Cloudflare A/AAAA records.

- Package import path: `dns_updater` under `src/` (repo name is `cloudflare-dns-updater`).
- Console command: `cloudflare-dns-updater` (hyphens).
- Config env: `CLOUDFLARE_DNS_UPDATER_CONFIG`; token env: `CLOUDFLARE_API_TOKEN`.
- Do not commit `config.json` or API tokens.

---

## Session Startup

Before creating any branch or writing code, initialize the session from the repository root using [repository-helpers](https://github.com/the-hcma/repository-helpers):

```bash
~/work/ai/repository-helpers/scripts/dev/start-development --refresh
~/work/ai/repository-helpers/scripts/dev/start-development --worktree <stack-name> --no-interactive
```

- **`--refresh`** (first): syncs `main` with Graphite (`gt sync`), prunes merged worktrees and branches, pulls latest `main`, then exits.
- **plain / `--worktree`** (second): repeats sync/cleanup, then creates or resumes a worktree under `.worktrees/<stack-name>-wt`.
- AI agents must always pass **`--no-interactive`** and an explicit **`--worktree`** name.
- Do not manually create worktrees or run `gt sync` separately — `start-development` is the single entry point for new work.

---

## Language & Runtime

- **Python ≥ 3.12** (`.python-version`, `requires-python = ">=3.12"`).
- Use **modern typing**: `list[str]`, `str | None`, not `List[str]` / `Optional[str]`.
- Every new module starts with `from __future__ import annotations`.
- Every public function and method has complete type annotations. **mypy** (`strict = true`) enforces this.
- **Only `uv`** for Python dependency management. Never `pip` directly.
- The lock file (`uv.lock`) must always be committed.

---

## Development

```bash
uv sync --group dev
uv run ruff check .
uv run ruff format .
uv run mypy src/dns_updater
uv run pytest
```

Hermetic tests (CI default):

```bash
uv run pytest -m "not integration"
```

---

## Commits, Stacking & Pull Requests

> See [GRAPHITE.md](./GRAPHITE.md) for the full Graphite workflow reference.

- This project uses **Graphite (`gt`)** for branch stacking.
- **Worktree-per-stack.** Every new stack is created via `start-development --worktree <name> --no-interactive`.
- Never work directly on `main`. Create stacked branches with `gt create <stack>/<description> -m "feat: ..."`.
- Keep each branch focused on one logical change.
- Submit with `gt submit --no-interactive --publish`.
- To merge, add the `merge-it` label: `gh pr edit <number> --add-label merge-it`. Never use `gh pr merge` directly.
- Follow **Conventional Commits**: `feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`.
- PR descriptions must include **Summary** and **Test plan** at minimum.

---

## Repository Practices

Run from [repository-helpers](https://github.com/the-hcma/repository-helpers):

```bash
scripts/check-repo-practices --repo the-hcma/cloudflare-dns-updater --suggest
```

---

## CI Checks (all must pass)

CI lives in `.github/workflows/ci.yml`:

```
uv run ruff check .
uv run ruff format --check .
uv run mypy src/dns_updater
uv run pytest -m "not integration"
```

No PR may be merged with a failing CI check.

---

## Pre-Commit Checklist

- [ ] `uv run ruff check .` and `uv run ruff format .`
- [ ] `uv run mypy src/dns_updater`
- [ ] `uv run pytest -m "not integration"`
- [ ] No secrets or `config.json` in the diff
- [ ] Commit message follows Conventional Commits
