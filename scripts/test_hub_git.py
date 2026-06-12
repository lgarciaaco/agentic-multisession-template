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
from unittest import mock

ROOT = Path(__file__).resolve().parent
HUB_ROOT = ROOT.parent
sys.path.insert(0, str(ROOT / "lib"))

from hub_git import (  # noqa: E402
    _validate_branch,
    resolve_worktree_start_ref,
    sync_local_branch_to_upstream,
)
import hub_git  # noqa: E402


def _git_env() -> dict[str, str]:
    return {
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@e",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@e",
    }


def _init_bare_and_clone(tmp: Path) -> tuple[Path, Path, Path]:
    """Return (bare origin, upstream clone, local clone). Both clones track bare/main."""
    env = _git_env()
    bare = tmp / "origin.git"
    subprocess.run(["git", "init", "--bare", "-b", "main", str(bare)], check=True, capture_output=True)
    upstream = tmp / "upstream"
    subprocess.run(["git", "clone", str(bare), str(upstream)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(upstream), "commit", "--allow-empty", "-m", "init"],
        check=True,
        capture_output=True,
        env=env,
    )
    subprocess.run(
        ["git", "-C", str(upstream), "push", "origin", "main"],
        check=True,
        capture_output=True,
        env=env,
    )
    local = tmp / "local"
    subprocess.run(["git", "clone", str(bare), str(local)], check=True, capture_output=True)
    return bare, upstream, local


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
            env = _git_env()
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

    def test_sync_fast_forwards_when_behind(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bare, upstream, local = _init_bare_and_clone(Path(tmp))
            env = _git_env()
            subprocess.run(
                ["git", "-C", str(upstream), "commit", "--allow-empty", "-m", "ahead"],
                check=True,
                capture_output=True,
                env=env,
            )
            subprocess.run(
                ["git", "-C", str(upstream), "push", "origin", "main"],
                check=True,
                capture_output=True,
                env=env,
            )
            upstream_sha = subprocess.run(
                ["git", "-C", str(upstream), "rev-parse", "--short", "main"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            synced = sync_local_branch_to_upstream(local, "main")
            self.assertEqual(synced, upstream_sha)

    def test_sync_noop_when_up_to_date(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _, _, local = _init_bare_and_clone(Path(tmp))
            first = sync_local_branch_to_upstream(local, "main")
            second = sync_local_branch_to_upstream(local, "main")
            self.assertEqual(first, second)

    def test_sync_raises_on_diverged_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bare, upstream, local = _init_bare_and_clone(Path(tmp))
            env = _git_env()
            subprocess.run(
                ["git", "-C", str(local), "commit", "--allow-empty", "-m", "local-only"],
                check=True,
                capture_output=True,
                env=env,
            )
            subprocess.run(
                ["git", "-C", str(upstream), "commit", "--allow-empty", "-m", "upstream-only"],
                check=True,
                capture_output=True,
                env=env,
            )
            subprocess.run(
                ["git", "-C", str(upstream), "push", "origin", "main"],
                check=True,
                capture_output=True,
                env=env,
            )
            with self.assertRaises(RuntimeError) as ctx:
                sync_local_branch_to_upstream(local, "main")
            self.assertIn("could not fast-forward", str(ctx.exception))

    def test_sync_checks_out_default_branch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _, _, local = _init_bare_and_clone(Path(tmp))
            subprocess.run(
                ["git", "-C", str(local), "checkout", "-b", "feature"],
                check=True,
                capture_output=True,
            )
            sync_local_branch_to_upstream(local, "main")
            current = subprocess.run(
                ["git", "-C", str(local), "branch", "--show-current"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            self.assertEqual(current, "main")

    def test_sync_checkout_failure_raises_runtime_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _, _, local = _init_bare_and_clone(Path(tmp))
            subprocess.run(
                ["git", "-C", str(local), "checkout", "-b", "feature"],
                check=True,
                capture_output=True,
            )
            failed = subprocess.CompletedProcess(
                args=[],
                returncode=1,
                stdout="",
                stderr="fatal: unable to checkout main",
            )

            real_run = hub_git._run

            def fake_run(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
                if args and args[0] == "checkout":
                    return failed
                return real_run(repo, *args, check=check)

            with mock.patch.object(hub_git, "_run", side_effect=fake_run):
                with self.assertRaises(RuntimeError) as ctx:
                    sync_local_branch_to_upstream(local, "main")
            self.assertIn("could not checkout main", str(ctx.exception))
            self.assertIn("unable to checkout main", str(ctx.exception))

    def test_clone_repos_existing_clone_no_pathspec_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scripts = root / "scripts"
            scripts.mkdir()
            shutil.copytree(ROOT / "lib", scripts / "lib")
            shutil.copy(ROOT / "clone-repos.sh", scripts / "clone-repos.sh")
            repo_dir = root / "repos" / "fixture"
            repo_dir.parent.mkdir(parents=True)
            bare = root / "origin.git"
            subprocess.run(["git", "init", "--bare", "-b", "main", str(bare)], check=True, capture_output=True)
            subprocess.run(
                ["git", "clone", str(bare), str(repo_dir)],
                check=True,
                capture_output=True,
            )
            env = _git_env()
            subprocess.run(
                ["git", "-C", str(repo_dir), "commit", "--allow-empty", "-m", "init"],
                check=True,
                capture_output=True,
                env=env,
            )
            subprocess.run(
                ["git", "-C", str(repo_dir), "push", "origin", "main"],
                check=True,
                capture_output=True,
                env=env,
            )
            (root / "repos.yaml").write_text(
                "repos:\n"
                "  fixture:\n"
                f"    path: repos/fixture\n"
                f"    clone: {bare.as_uri()}\n"
                "    default_branch: main\n"
            )
            env = os.environ.copy()
            env["WORKSPACE_ROOT"] = str(root)
            env["WORKSPACE_ALLOW_FILE_CLONES"] = "1"
            result = subprocess.run(
                [str(scripts / "clone-repos.sh")],
                cwd=root,
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("pathspec", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
