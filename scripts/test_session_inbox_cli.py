#!/usr/bin/env python3
"""CLI smoke tests for session inbox write caller binding."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from session_binding import write_binding  # noqa: E402

SCRIPTS_DIR = Path(__file__).resolve().parent


class SessionInboxCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.from_session = "bravo"
        self.to_session = "alpha"
        self.conversation_id = "inbox-cli-test-conv"
        for name in (self.from_session, self.to_session):
            session_dir = self.root / "sessions" / name
            session_dir.mkdir(parents=True)
            (session_dir / "session.json").write_text(
                json.dumps({"codename": name, "status": "active", "tasks": []}) + "\n"
            )
            (session_dir / "TASKS.md").write_text("# Goal\n")
        (self.root / "sessions" / "bindings").mkdir(parents=True)
        self._install_scripts()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _install_scripts(self) -> None:
        scripts = self.root / "scripts"
        shutil.copytree(SCRIPTS_DIR / "lib", scripts / "lib")
        for name in ("session-inbox.sh",):
            dest = scripts / name
            shutil.copy2(SCRIPTS_DIR / name, dest)
            dest.chmod(0o755)

    def _env(self, **overrides: str) -> dict[str, str]:
        env = {**os.environ, "WORKSPACE_ROOT": str(self.root)}
        env.update(overrides)
        return env

    def _run_cli(self, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        cli = SCRIPTS_DIR / "lib" / "session_cli.py"
        return subprocess.run(
            [sys.executable, str(cli), *args],
            capture_output=True,
            text=True,
            env=env or self._env(),
            cwd=self.root,
            check=False,
        )

    def _run_session_inbox_sh(self, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        script = self.root / "scripts" / "session-inbox.sh"
        return subprocess.run(
            [str(script), *args],
            capture_output=True,
            text=True,
            env=env or self._env(),
            cwd=self.root,
            check=False,
        )

    def test_cli_unbound_write_exits_nonzero(self) -> None:
        result = self._run_cli(
            "inbox",
            "write",
            self.from_session,
            self.to_session,
            "Status update",
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("binding", result.stderr.lower())
        self.assertFalse((self.root / "sessions" / "_inbox" / f"{self.to_session}.md").exists())

    def test_cli_as_matching_from_succeeds(self) -> None:
        result = self._run_cli(
            "inbox",
            "write",
            "--as",
            self.from_session,
            self.from_session,
            self.to_session,
            "Bound via --as",
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        content = (self.root / "sessions" / "_inbox" / f"{self.to_session}.md").read_text()
        self.assertIn("Bound via --as", content)

    def test_cli_as_mismatch_bound_session_fails(self) -> None:
        write_binding(self.root, self.conversation_id, self.from_session)
        result = self._run_cli(
            "inbox",
            "write",
            "--as",
            self.to_session,
            self.to_session,
            self.from_session,
            "Impersonation attempt",
            env=self._env(WORKSPACE_CONVERSATION_ID=self.conversation_id),
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("does not match", result.stderr)
        self.assertFalse((self.root / "sessions" / "_inbox" / f"{self.from_session}.md").exists())

    def test_session_inbox_sh_unbound_write_exits_nonzero(self) -> None:
        result = self._run_session_inbox_sh(
            "write",
            self.from_session,
            self.to_session,
            "Shell path unbound",
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("binding", result.stderr.lower())

    def test_session_inbox_sh_as_matching_from_succeeds(self) -> None:
        result = self._run_session_inbox_sh(
            "write",
            "--as",
            self.from_session,
            self.from_session,
            self.to_session,
            "Shell path --as",
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        content = (self.root / "sessions" / "_inbox" / f"{self.to_session}.md").read_text()
        self.assertIn("Shell path --as", content)

    def test_session_inbox_sh_as_mismatch_bound_session_fails(self) -> None:
        write_binding(self.root, self.conversation_id, self.from_session)
        result = self._run_session_inbox_sh(
            "write",
            "--as",
            self.to_session,
            self.to_session,
            self.from_session,
            "Shell impersonation",
            env=self._env(WORKSPACE_CONVERSATION_ID=self.conversation_id),
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("does not match", result.stderr)
        self.assertFalse((self.root / "sessions" / "_inbox" / f"{self.from_session}.md").exists())


if __name__ == "__main__":
    unittest.main()
