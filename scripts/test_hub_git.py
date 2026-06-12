#!/usr/bin/env python3
"""Tests for hub_git worktree helpers."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HUB_ROOT = ROOT.parent
sys.path.insert(0, str(ROOT / "lib"))

from hub_git import _validate_branch, resolve_worktree_start_ref  # noqa: E402


class HubGitTests(unittest.TestCase):
    def test_validate_branch_rejects_traversal(self) -> None:
        with self.assertRaises(ValueError):
            _validate_branch("../evil")

    def test_validate_branch_rejects_leading_hyphen(self) -> None:
        with self.assertRaises(ValueError):
            _validate_branch("-evil")

    def test_validate_branch_accepts_feature_branch(self) -> None:
        self.assertEqual(_validate_branch("alpha/fix-review"), "alpha/fix-review")

    def test_clone_repos_rejects_invalid_default_branch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scripts = root / "scripts"
            scripts.mkdir()
            shutil.copytree(ROOT / "lib", scripts / "lib")
            shutil.copy(ROOT / "clone-repos.sh", scripts / "clone-repos.sh")
            (root / "repos.yaml").write_text(
                "repos:\n"
                "  evil:\n"
                "    path: repos/evil\n"
                "    clone: git@github.com:example/evil.git\n"
                "    default_branch: ../evil\n"
            )
            env = os.environ.copy()
            env["WORKSPACE_ROOT"] = str(root)
            result = subprocess.run(
                [str(scripts / "clone-repos.sh")],
                cwd=root,
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("invalid git branch", result.stderr)

    def test_resolve_worktree_start_ref_after_fetch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            env = {
                "GIT_AUTHOR_NAME": "t",
                "GIT_AUTHOR_EMAIL": "t@e",
                "GIT_COMMITTER_NAME": "t",
                "GIT_COMMITTER_EMAIL": "t@e",
            }
            subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, capture_output=True)
            subprocess.run(
                ["git", "-C", str(repo), "commit", "--allow-empty", "-m", "init"],
                check=True,
                capture_output=True,
                env=env,
            )
            subprocess.run(
                ["git", "-C", str(repo), "remote", "add", "origin", str(repo)],
                check=True,
                capture_output=True,
            )
            ref, sha = resolve_worktree_start_ref(repo, "main")
            self.assertEqual(ref, "origin/main")
            self.assertTrue(sha)


if __name__ == "__main__":
    unittest.main()
