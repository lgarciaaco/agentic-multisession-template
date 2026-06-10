#!/usr/bin/env python3
"""Smoke tests for scripts/lib/session_cli.py subcommands."""

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


class SessionCliSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "sessions" / "alpha").mkdir(parents=True)
        (self.root / "sessions" / "alpha" / "session.json").write_text(
            json.dumps({"codename": "alpha", "title": "Alpha", "status": "active", "tasks": []})
            + "\n"
        )
        lib_src = Path(__file__).resolve().parent / "lib"
        shutil.copytree(lib_src, self.root / "scripts" / "lib", dirs_exist_ok=True)
        self.cli = self.root / "scripts" / "lib" / "session_cli.py"
        self.env = os.environ.copy()
        self.env["WORKSPACE_ROOT"] = str(self.root)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(self.cli), *args],
            capture_output=True,
            text=True,
            env=self.env,
        )

    def test_list_active_sessions(self) -> None:
        result = self._run("list")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("alpha", result.stdout)

    def test_inbox_read_empty(self) -> None:
        result = self._run("inbox", "read", "alpha")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_bind_invalid_codename(self) -> None:
        result = self._run("bind", "../evil")
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
