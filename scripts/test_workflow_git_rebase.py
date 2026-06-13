#!/usr/bin/env python3
"""Tests for non-interactive git editor env and workflow-git-rebase.sh."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from git_noninteractive import NONINTERACTIVE_EDITOR_ENV, noninteractive_editor_env  # noqa: E402


HUB = Path(__file__).resolve().parent.parent
REBASE_SCRIPT = HUB / "scripts" / "workflow-git-rebase.sh"
CI_FIXER = (
    HUB / ".cursor/skills/workflow-orchestrator/rules/ci-fixer.md"
)
CONDUCTOR = (
    HUB / ".cursor/skills/workflow-orchestrator/rules/conductor.md"
)


class GitNoninteractiveTests(unittest.TestCase):
    def test_noninteractive_editor_env(self) -> None:
        env = noninteractive_editor_env()
        self.assertEqual(env, NONINTERACTIVE_EDITOR_ENV)
        self.assertIsNot(env, NONINTERACTIVE_EDITOR_ENV)

    def test_rebase_script_exports_editors(self) -> None:
        text = REBASE_SCRIPT.read_text()
        self.assertIn("export GIT_EDITOR=true", text)
        self.assertIn("export EDITOR=true", text)
        self.assertIn("git fetch origin", text)
        self.assertIn("git rebase", text)

    def test_ci_fixer_and_conductor_reference_wrapper(self) -> None:
        ci_text = CI_FIXER.read_text()
        conductor_text = CONDUCTOR.read_text()
        self.assertIn("workflow-git-rebase.sh", ci_text)
        self.assertIn("workflow-git-rebase.sh", conductor_text)
        for text in (ci_text, conductor_text):
            for line in text.splitlines():
                lower = line.lower()
                if "git rebase" in lower and "workflow-git-rebase" not in lower:
                    self.fail(f"doc has bare git rebase: {line!r}")

    def test_headless_rebase_does_not_hang(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "repo"
            bare = Path(td) / "origin.git"
            repo.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=repo,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test"],
                cwd=repo,
                check=True,
                capture_output=True,
            )
            (repo / "f").write_text("base\n")
            subprocess.run(["git", "add", "f"], cwd=repo, check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-qm", "base"],
                cwd=repo,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "branch", "-M", "main"],
                cwd=repo,
                check=True,
                capture_output=True,
            )
            subprocess.run(["git", "init", "--bare", "-q", str(bare)], check=True, capture_output=True)
            subprocess.run(
                ["git", "remote", "add", "origin", str(bare)],
                cwd=repo,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "push", "-u", "origin", "main"],
                cwd=repo,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "checkout", "-q", "-b", "feature"],
                cwd=repo,
                check=True,
                capture_output=True,
            )
            (repo / "f").write_text("feat\n")
            subprocess.run(["git", "commit", "-am", "feat"], cwd=repo, check=True, capture_output=True)
            subprocess.run(
                ["git", "checkout", "-q", "main"],
                cwd=repo,
                check=True,
                capture_output=True,
            )
            (repo / "f").write_text("main\n")
            subprocess.run(["git", "commit", "-am", "main"], cwd=repo, check=True, capture_output=True)
            subprocess.run(
                ["git", "push", "origin", "main"],
                cwd=repo,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "checkout", "-q", "feature"],
                cwd=repo,
                check=True,
                capture_output=True,
            )

            env = {**os.environ, "GIT_EDITOR": "vim", "EDITOR": "vim"}
            result = subprocess.run(
                ["bash", str(REBASE_SCRIPT), str(repo), "main"],
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            # Expect conflict or success — not hang (TimeoutExpired if blocked on editor).
            self.assertIn(result.returncode, (0, 1), result.stderr)


if __name__ == "__main__":
    unittest.main()
