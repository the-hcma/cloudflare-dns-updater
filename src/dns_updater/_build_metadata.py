"""Optional release-time stamps baked into wheels and sdists.

``scripts/embed_build_metadata.py`` overwrites this file before packaging so
``--help`` and ``--version`` still report version and commit when ``.git`` is
absent (for example after ``pipx install`` from PyPI). Empty strings mean
unset and :mod:`dns_updater.build_info` falls back to ``importlib.metadata``,
then ``pyproject.toml``, then ``git``.
"""

from __future__ import annotations

EMBEDDED_COMMIT: str = ""
EMBEDDED_VERSION: str = ""
