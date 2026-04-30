"""Documentation governance tests."""

from __future__ import annotations

import pytest

from scripts.check_readmes import REPO_ROOT, find_missing_readmes


@pytest.mark.docs
def test_maintained_folders_have_readmes():
    """Ensure source folders remain discoverable through local README files."""
    assert find_missing_readmes(REPO_ROOT) == []
