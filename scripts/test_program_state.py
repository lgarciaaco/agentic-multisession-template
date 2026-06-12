#!/usr/bin/env python3
"""Tests for program orchestrator state (program.json)."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from program_state import (  # noqa: E402
    default_program,
    find_program_parent,
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

    def test_find_program_parent_returns_parent(self) -> None:
        parent_dir = self.root / "sessions" / "alpha"
        child_dir = self.root / "sessions" / "charlie"
        parent_dir.mkdir(parents=True)
        child_dir.mkdir(parents=True)
        (parent_dir / "artifacts").mkdir()
        program = default_program("alpha")
        program["active_children"] = [{"codename": "charlie", "status": "running"}]
        save_program(parent_dir, program)
        self.assertEqual(find_program_parent(self.root, "charlie"), "alpha")

    def test_find_program_parent_none_when_unregistered(self) -> None:
        parent_dir = self.root / "sessions" / "alpha"
        parent_dir.mkdir(parents=True)
        (parent_dir / "artifacts").mkdir()
        save_program(parent_dir, default_program("alpha"))
        self.assertIsNone(find_program_parent(self.root, "charlie"))

    def test_template_file_parses(self) -> None:
        hub_root = Path(__file__).resolve().parent.parent
        template_path = hub_root / "sessions" / "_template" / "program.json"
        raw = json.loads(template_path.read_text())
        self.assertEqual(raw["version"], 1)

    @mock.patch("program_bootstrap._run_script")
    def test_bootstrap_sets_active_children(self, run_script) -> None:
        program = default_program("mike")
        program["proposed_children"] = [
            {
                "id": "pc1",
                "suggested_codename": "november",
                "title": "Child",
                "goal": "Goal",
                "repo": "template",
                "depends_on": [],
            }
        ]
        save_program(self.session_dir, program)
        run_script.side_effect = lambda root, script, *args: "november"

        sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
        from program_bootstrap import bootstrap_children  # noqa: E402

        os.environ.pop("TMUX", None)
        with mock.patch("sys.stdout"):
            bootstrap_children(self.root, "mike", approve=True)

        loaded = load_program(self.session_dir)
        self.assertTrue(loaded["decomposition_approved"])
        self.assertEqual(loaded["active_children"][0]["codename"], "november")

    @mock.patch("program_bootstrap._run_script")
    def test_bootstrap_persists_active_children_incrementally_on_mid_loop_failure(
        self, run_script
    ) -> None:
        program = default_program("mike")
        program["proposed_children"] = [
            {
                "id": "pc1",
                "suggested_codename": "november",
                "title": "First",
                "goal": "Goal one",
                "repo": "template",
                "depends_on": [],
            },
            {
                "id": "pc2",
                "suggested_codename": "oscar",
                "title": "Second",
                "goal": "Goal two",
                "repo": "template",
                "depends_on": [],
            },
        ]
        save_program(self.session_dir, program)

        def side_effect(root, script, *args):
            if args and args[0] == "oscar":
                raise RuntimeError("new-session.sh failed")
            return args[0]

        run_script.side_effect = side_effect

        sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
        from program_bootstrap import bootstrap_children  # noqa: E402

        os.environ.pop("TMUX", None)
        with mock.patch("sys.stdout"):
            with self.assertRaises(RuntimeError):
                bootstrap_children(self.root, "mike", approve=True)

        loaded = load_program(self.session_dir)
        self.assertEqual(len(loaded["active_children"]), 1)
        self.assertEqual(loaded["active_children"][0]["codename"], "november")

    @mock.patch("program_bootstrap._run_script")
    def test_bootstrap_retry_preserves_existing_active_children(self, run_script) -> None:
        program = default_program("mike")
        program["proposed_children"] = [
            {
                "id": "pc1",
                "suggested_codename": "november",
                "title": "First",
                "goal": "Goal one",
                "repo": "template",
                "depends_on": [],
            },
            {
                "id": "pc2",
                "suggested_codename": "oscar",
                "title": "Second",
                "goal": "Goal two",
                "repo": "template",
                "depends_on": [],
            },
        ]
        program["active_children"] = [
            {"codename": "november", "status": "running", "started": "2026-06-12T00:00:00Z"}
        ]
        save_program(self.session_dir, program)

        run_script.return_value = "oscar"

        sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
        from program_bootstrap import bootstrap_children  # noqa: E402

        os.environ.pop("TMUX", None)
        with mock.patch("sys.stdout"):
            result = bootstrap_children(self.root, "mike", approve=True)

        scripts_called = [call[0][1] for call in run_script.call_args_list]
        self.assertEqual(scripts_called.count("new-session.sh"), 1)
        loaded = load_program(self.session_dir)
        self.assertEqual(len(loaded["active_children"]), 2)
        self.assertEqual(
            [child["codename"] for child in loaded["active_children"]],
            ["november", "oscar"],
        )
        self.assertEqual(len(result["children"]), 2)


if __name__ == "__main__":
    unittest.main()
