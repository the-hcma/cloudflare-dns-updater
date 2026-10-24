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

- At the **start of every agent session**, before acting from assumed conventions, read this `AGENTS.md` in full, then read every `alwaysApply: true` rule under `.agents/rules/*.md` (plus any whose `globs` match files you will touch) — `AGENTS.md` and `.agents/rules/` together are the contract (`.cursor/rules/*.mdc` are Cursor injection shims only). `CLAUDE.md` (a `@AGENTS.md` import), `.github/copilot-instructions.md` and `.github/instructions/agents-rules.instructions.md` are thin shims so Claude Code and Copilot reach the same guidance.
- Markdown files you commit, this one included, use one physical line per paragraph, list item and blockquote, with no hard line breaks (see `.agents/rules/github-content-formatting.md`).

Before creating any branch or writing code, initialize the session from the repository root using [repository-helpers](https://github.com/the-hcma/repository-helpers):

```bash
~/work/ai/repository-helpers/scripts/dev/start-development --refresh
~/work/ai/repository-helpers/scripts/dev/start-development --worktree <stack-name> --no-interactive
```

- **`--refresh`** (first): syncs `main` (`gh stack sync`), prunes merged worktrees and branches, pulls latest `main`, then exits.
- **plain / `--worktree`** (second): repeats sync/cleanup, then creates or resumes a worktree under `.worktrees/<stack-name>-wt`.
- AI agents must always pass **`--no-interactive`** and an explicit **`--worktree`** name.
- Do not manually create worktrees or run `gh stack sync` separately — `start-development` is the single entry point for new work.

---

## Language & Runtime

- **Python ≥ 3.12** (`.python-version`, `requires-python = ">=3.12"`).
- Use **modern typing**: `list[str]`, `str | None`, not `List[str]` / `Optional[str]`.
- Every new module starts with `from __future__ import annotations`.
- Every public function and method has complete type annotations. **mypy** (`strict = true`) enforces this.
- **Only `uv`** for Python dependency management. Never `pip` directly.
- The lock file (`uv.lock`) must always be committed.
- **Remote timeouts and bounded retries:** `.cursor/rules/remote-timeouts-retries.mdc` (`alwaysApply`, org rule — template sync [repository-helpers#570](https://github.com/the-hcma/repository-helpers/issues/570)). Every `requests` call and the `Cloudflare` SDK client sets an explicit finite timeout; the SDK's bounded `max_retries` cap stays in place; any hand-rolled retry is capped/budgeted, backed off, transient-only, and never re-sends a non-idempotent write.

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

> See [`.agents/skills/gh-stack/SKILL.md`](https://github.com/the-hcma/repository-helpers/blob/main/.agents/skills/gh-stack/SKILL.md) in repository-helpers for the full stacking workflow, and `.agents/rules/stacking-tool.md` for the marker contract.

- This project stacks branches with **GitHub Stacked PRs** (`gh stack`), as declared in `.github/stacking-tool`.
- **Worktree-per-stack.** Every new stack is created via `start-development --worktree <name> --no-interactive`.
- Never work directly on `main`. Create stacked branches with `gh stack init <stack>/<description>` / `gh stack add`.
- Keep each branch focused on one logical change.
- Submit with `scripts/dev/submit-stack` (or `gh stack submit --auto --open --remote origin`); PRs are published, not drafts.
- To merge, ask the user first, then enqueue on GitHub's merge queue: `gh pr merge <number> --auto --squash`, or `gh stack merge --yes --squash` with no argument (from the stack's worktree; it merges the whole current stack bottom-up, so confirm that whole set with the user first) for a PR that belongs to a gh stack (`scripts/dev/merge-stack --pr <n>` in repository-helpers picks the right one). Do not use the `merge-it` label.
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
