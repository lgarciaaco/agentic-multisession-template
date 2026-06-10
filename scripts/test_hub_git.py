#!/usr/bin/env python3
"""Unit tests for scripts/lib/hub_git.py."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from hub_git import (  # noqa: E402
    _validate_branch,
    resolve_worktree_start_ref,
    upstream_ref,
)


class HubGitBranchValidationTests(unittest.TestCase):
    def test_accepts_valid_branch(self) -> None:
        self.assertEqual(_validate_branch("feature/foo"), "feature/foo")

    def test_rejects_traversal(self) -> None:
        with self.assertRaises(ValueError):
            _validate_branch("../evil")


class HubGitRepoTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.bare = self.root / "origin.git"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-b", "main", str(self.bare), "--bare"], check=True, capture_output=True)
        subprocess.run(["git", "init", "-b", "main", str(self.repo)], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(self.repo), "config", "user.email", "t@test"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "config", "user.name", "t"], check=True)
        (self.repo / "README").write_text("x\n")
        subprocess.run(["git", "-C", str(self.repo), "add", "README"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "commit", "-m", "init"], check=True)
        subprocess.run(
            ["git", "-C", str(self.repo), "remote", "add", "origin", str(self.bare)],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(self.repo), "push", "-u", "origin", "main"],
            check=True,
            capture_output=True,
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_upstream_ref(self) -> None:
        ref = upstream_ref(self.repo, "main")
        self.assertEqual(ref, "origin/main")

    @patch("hub_git.fetch_upstream")
    def test_resolve_worktree_start_ref(self, _fetch: unittest.mock.MagicMock) -> None:
        start_ref, sha = resolve_worktree_start_ref(self.repo, "main")
        self.assertEqual(start_ref, "origin/main")
        self.assertTrue(len(sha) >= 4)


if __name__ == "__main__":
    unittest.main()
