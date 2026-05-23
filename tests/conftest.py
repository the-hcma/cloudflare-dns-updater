"""Shared pytest fixtures."""

from __future__ import annotations

import pytest
from helpers import MockExternalIps


@pytest.fixture
def mock_external_ips() -> MockExternalIps:
    """Default mocked external IPv4/IPv6 values with a changed prior state."""
    return MockExternalIps()
