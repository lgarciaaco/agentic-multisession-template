#!/usr/bin/env python3
"""Tests for git fork remote configuration."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from git_remotes import (  # noqa: E402
    configure_repo_remotes,
    default_fork_user_from_yaml,
    fork_clone_url,
    validate_clone_url,
)


class ForkCloneUrlTests(unittest.TestCase):
    def test_github_derived_fork_url(self) -> None:
        cfg = {"remote": "github", "name": "my-app"}
        self.assertEqual(
            fork_clone_url(cfg, "alice"),
            "git@github.com:alice/my-app.git",
        )

    def test_explicit_fork_url(self) -> None:
        cfg = {
            "remote": "github",
            "name": "my-app",
            "fork": "git@github.com:bob/my-app.git",
        }
        self.assertEqual(fork_clone_url(cfg, "alice"), "git@github.com:bob/my-app.git")

    def test_gitlab_returns_none(self) -> None:
        cfg = {"remote": "gitlab", "name": "service", "clone": "git@gitlab.com:g/s.git"}
        self.assertIsNone(fork_clone_url(cfg, "alice"))

    def test_github_without_fork_user_returns_none(self) -> None:
        cfg = {"remote": "github", "name": "my-app"}
        self.assertIsNone(fork_clone_url(cfg, ""))


class ValidateCloneUrlTests(unittest.TestCase):
    def test_accepts_git_ssh_and_https(self) -> None:
        self.assertEqual(
            validate_clone_url("git@github.com:ORG/repo.git"),
            "git@github.com:ORG/repo.git",
        )
        self.assertEqual(
            validate_clone_url("https://github.com/ORG/repo.git"),
            "https://github.com/ORG/repo.git",
        )

    def test_rejects_dash_prefix(self) -> None:
        with self.assertRaises(ValueError):
            validate_clone_url("-evil")

    def test_rejects_newlines(self) -> None:
        with self.assertRaises(ValueError):
            validate_clone_url("git@github.com:ORG/repo.git\n--upload-pack=sh")

    def test_rejects_file_url_by_default(self) -> None:
        with self.assertRaises(ValueError):
            validate_clone_url("file:///tmp/repo.git")


class ConfigureRepoRemotesTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tmpdir.name)
        self.repo = self.root / "repo"
        subprocess.run(["git", "init", "-b", "main", str(self.repo)], check=True, capture_output=True)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def _remote_url(self, name: str) -> str:
        return subprocess.run(
            ["git", "-C", str(self.repo), "remote", "get-url", name],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def _git_config(self, key: str) -> str:
        return subprocess.run(
            ["git", "-C", str(self.repo), "config", "--get", key],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def test_github_fork_workflow(self) -> None:
        cfg = {
            "clone": "git@github.com:ORG/upstream.git",
            "remote": "github",
            "name": "upstream",
        }
        configure_repo_remotes(self.repo, cfg, default_fork_user="alice")
        self.assertEqual(self._remote_url("origin"), "git@github.com:ORG/upstream.git")
        self.assertEqual(self._remote_url("fork"), "git@github.com:alice/upstream.git")
        self.assertEqual(self._git_config("remote.pushDefault"), "fork")
        self.assertEqual(self._git_config("remote.origin.pushurl"), "no_push_to_upstream")

    def test_gitlab_push_origin_only(self) -> None:
        cfg = {
            "clone": "git@gitlab.com:GROUP/service.git",
            "remote": "gitlab",
        }
        configure_repo_remotes(self.repo, cfg, default_fork_user="alice")
        self.assertEqual(self._remote_url("origin"), "git@gitlab.com:GROUP/service.git")
        missing_fork = subprocess.run(
            ["git", "-C", str(self.repo), "remote", "get-url", "fork"],
            capture_output=True,
        ).returncode
        self.assertNotEqual(missing_fork, 0)


class DefaultForkUserTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tmpdir.name)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_reads_github_fork_user(self) -> None:
        (self.root / "repos.yaml").write_text(
            "github_fork_user: alice\nrepos:\n  app:\n    path: repos/app\n    clone: git@github.com:ORG/app.git\n"
        )
        self.assertEqual(default_fork_user_from_yaml(self.root), "alice")

    def test_missing_repos_yaml_returns_empty(self) -> None:
        self.assertEqual(default_fork_user_from_yaml(self.root), "")


class GenerateWorkspaceSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tmpdir.name)
        scripts = self.root / "scripts"
        lib = scripts / "lib"
        lib.mkdir(parents=True)
        hub_root_path = Path(__file__).resolve().parent
        for rel in ("generate-workspace.sh", "lib/hub-env.sh", "lib/hub_paths.py", "lib/repos.py"):
            src = hub_root_path / rel
            dst = scripts / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(src.read_text())
            if rel.endswith(".sh"):
                dst.chmod(0o755)
        (self.root / ".hub-slug").write_text("test-hub\n")
        (self.root / "repos.yaml").write_text(
            "repos:\n  app:\n    path: repos/app\n    clone: git@github.com:ORG/app.git\n    default_branch: main\n"
        )

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_generate_workspace_writes_json(self) -> None:
        out = self.root / "out.code-workspace"
        env = {**subprocess.os.environ, "WORKSPACE_ROOT": str(self.root), "WORKSPACE_FILE": str(out)}
        result = subprocess.run(
            [str(self.root / "scripts" / "generate-workspace.sh"), str(out)],
            cwd=self.root,
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(out.exists())
        data = __import__("json").loads(out.read_text())
        paths = [f["path"] for f in data["folders"]]
        self.assertIn(".", paths)
        self.assertIn("repos/app", paths)


if __name__ == "__main__":
    unittest.main()
