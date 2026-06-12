#!/usr/bin/env python3
"""Tests for program-decompose registry resolution."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))

_SCRIPT_DIR = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "program_decompose", _SCRIPT_DIR / "program-decompose.py"
)
assert _spec and _spec.loader
_program_decompose = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_program_decompose)
_default_repo_alias = _program_decompose._default_repo_alias
decompose_program = _program_decompose.decompose_program


class ProgramDecomposeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.codename = "alpha"
        self.session_dir = self.root / "sessions" / self.codename
        self.session_dir.mkdir(parents=True)
        (self.session_dir / "artifacts").mkdir()
        (self.session_dir / "session.json").write_text(
            json.dumps({"codename": self.codename, "tasks": []}) + "\n"
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _write_repos(self, aliases: list[str]) -> None:
        lines = ["repos:"]
        for alias in aliases:
            lines.append(f"  {alias}:")
            lines.append(f"    path: repos/{alias}")
            lines.append(f"    clone: git@github.com:YOU/{alias}.git")
        (self.root / "repos.yaml").write_text("\n".join(lines) + "\n")

    def test_default_repo_alias_prefers_template(self) -> None:
        self._write_repos(["my-app", "template", "other"])
        self.assertEqual(_default_repo_alias(self.root), "template")

    def test_default_repo_alias_falls_back_to_first_key(self) -> None:
        self._write_repos(["my-app", "other"])
        self.assertEqual(_default_repo_alias(self.root), "my-app")

    def test_default_repo_alias_raises_when_empty(self) -> None:
        (self.root / "repos.yaml").write_text("repos: {}\n")
        with self.assertRaises(ValueError):
            _default_repo_alias(self.root)

    def test_decompose_program_assigns_valid_repo_alias(self) -> None:
        self._write_repos(["my-app", "template"])
        ingest = "## Checkout fix\n\nImprove token expiry messaging.\n"
        program = decompose_program(self.root, self.codename, ingest_text=ingest)
        rows = program["proposed_children"]
        self.assertGreaterEqual(len(rows), 1)
        for row in rows:
            self.assertEqual(row["repo"], "template")


if __name__ == "__main__":
    unittest.main()
