#!/usr/bin/env python3
"""Tests for program orchestrator state (program.json)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from program_state import (  # noqa: E402
    default_program,
    load_program,
    save_program,
)


class ProgramStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.session_dir = self.root / "sessions" / "mike"
        self.session_dir.mkdir(parents=True)
        (self.session_dir / "artifacts").mkdir()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_default_round_trip(self) -> None:
        program = default_program("mike")
        save_program(self.session_dir, program)
        loaded = load_program(self.session_dir)
        self.assertEqual(loaded["parent_codename"], "mike")
        self.assertEqual(loaded["version"], 1)
        self.assertFalse(loaded["decomposition_approved"])

    def test_gate_queue_unknown_child_raises(self) -> None:
        program = default_program("mike")
        program["active_children"] = [{"codename": "november", "status": "running"}]
        program["gate_queue"] = [
            {
                "child_codename": "oscar",
                "gate": "brief_review",
                "handled": False,
            }
        ]
        with self.assertRaisesRegex(ValueError, "unknown active child"):
            save_program(self.session_dir, program)

    def test_merge_hints_unknown_child_raises(self) -> None:
        program = default_program("mike")
        program["active_children"] = [{"codename": "november", "status": "running"}]
        program["merge_hints"]["ordered_children"] = ["oscar"]
        with self.assertRaisesRegex(ValueError, "unknown active child"):
            save_program(self.session_dir, program)

    def test_template_file_parses(self) -> None:
        hub_root = Path(__file__).resolve().parent.parent
        template_path = hub_root / "sessions" / "_template" / "program.json"
        raw = json.loads(template_path.read_text())
        self.assertEqual(raw["version"], 1)


if __name__ == "__main__":
    unittest.main()
