"""The uv-running CI wrappers re-exec through repository-helpers' with-tmp-layout (repository-helpers#832)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_WRAPPERS = ("mypy", "pytest-hermetic", "python-static", "ruff")


def _run(wrapper: str, tmp_path: Path, **env: str) -> subprocess.CompletedProcess[str]:
    """Run a CI wrapper with a helper-less HOME and the given extra environment."""

    empty = tmp_path / "no-helpers"
    empty.mkdir(exist_ok=True)
    base = {
        "PATH": os.environ["PATH"],
        "HOME": str(empty),
        "REPOSITORY_HELPERS_DIR": str(empty),
        "TMPDIR": str(tmp_path),
    }
    return subprocess.run(
        ["bash", str(_REPO_ROOT / ".github" / "ci" / wrapper)],
        cwd=_REPO_ROOT,
        env={**base, **env},
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )


@pytest.mark.parametrize("wrapper", _WRAPPERS)
def test_ci_without_the_layout_helper_fails_with_a_pointer_to_the_action(wrapper: str, tmp_path: Path) -> None:
    """In GitHub Actions a missing helper is an error naming the setup action."""

    result = _run(wrapper, tmp_path, GITHUB_ACTIONS="true")
    assert result.returncode == 1
    assert "setup-tmp-layout" in result.stderr


@pytest.mark.parametrize("wrapper", _WRAPPERS)
def test_wrapper_re_execs_through_the_layout_helper_when_present(wrapper: str, tmp_path: Path) -> None:
    """A present helper receives the wrapper, with the pytest layer added for hermetic tests."""

    helpers = tmp_path / "helpers"
    (helpers / "scripts" / "dev").mkdir(parents=True)
    stub = helpers / "scripts" / "dev" / "with-tmp-layout"
    stub.write_text('#!/usr/bin/env bash\nprintf "layout:%s\\n" "$*"\nexit 0\n')
    stub.chmod(0o755)
    result = _run(wrapper, tmp_path, REPOSITORY_HELPERS_DIR=str(helpers))
    assert result.returncode == 0
    assert result.stdout.startswith("layout:uv --")
    nested = f"{stub} pytest -- " if wrapper == "pytest-hermetic" else ""
    assert f"layout:uv -- {nested}bash" in result.stdout
