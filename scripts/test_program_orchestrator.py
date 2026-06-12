#!/usr/bin/env python3
"""Tests for sessions program orchestrator scripts."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from program_monitor import monitor_program  # noqa: E402
from program_route_feedback import route_feedback  # noqa: E402
from workflow_inbox_gate import classify_gate_message, parse_inbox_blocks, pull_inbox_gate  # noqa: E402
from program_state import default_program, save_program  # noqa: E402
from session_binding import write_inbox  # noqa: E402


class ProgramOrchestratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.parent = "mike"
        self.child = "november"
        parent_dir = self.root / "sessions" / self.parent
        child_dir = self.root / "sessions" / self.child
        parent_dir.mkdir(parents=True)
        child_dir.mkdir(parents=True)
        (parent_dir / "artifacts").mkdir()
        (child_dir / "artifacts").mkdir()

        program = default_program(self.parent)
        program["active_children"] = [{"codename": self.child, "status": "running"}]
        save_program(parent_dir, program)

        workflow = {
            "version": 2,
            "phase": "brief_review",
            "gates": {"brief_accepted": False, "plan_user_accepted": False},
            "loops": {},
            "artifacts": {},
        }
        (child_dir / "workflow.json").write_text(json.dumps(workflow, indent=2) + "\n")
        (child_dir / "session.json").write_text(
            json.dumps({"codename": self.child, "tasks": []}, indent=2) + "\n"
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_monitor_reports_child_gate(self) -> None:
        report = monitor_program(self.root, self.parent)
        self.assertEqual(report["parent"], self.parent)
        self.assertEqual(len(report["children"]), 1)
        child = report["children"][0]
        self.assertEqual(child["codename"], self.child)
        self.assertEqual(child["pending_gate"], "brief_review")

    def test_route_feedback_writes_inbox(self) -> None:
        route_feedback(
            self.root,
            parent=self.parent,
            child=self.child,
            gate="brief_review",
            message="accept brief",
        )
        inbox = self.root / "sessions" / "_inbox" / f"{self.child}.md"
        self.assertTrue(inbox.exists())
        blocks = parse_inbox_blocks(inbox.read_text())
        self.assertEqual(blocks[0]["body"].splitlines()[0].strip(), "accept brief")
        self.assertEqual(
            classify_gate_message("brief_review", blocks[0]["body"]),
            "accept_brief",
        )

    def test_route_feedback_classifies_as_gate_accept(self) -> None:
        route_feedback(
            self.root,
            parent=self.parent,
            child=self.child,
            gate="brief_review",
            message="accept brief",
        )
        result = pull_inbox_gate(self.root, self.child, apply=False)
        self.assertEqual(result["pending"][0]["action"], "accept_brief")

    def test_route_feedback_unknown_child_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "not registered"):
            route_feedback(
                self.root,
                parent=self.parent,
                child="oscar",
                gate="brief_review",
                message="accept brief",
            )

    def test_route_feedback_rejects_prose(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid message"):
            route_feedback(
                self.root,
                parent=self.parent,
                child=self.child,
                gate="brief_review",
                message="brief looks good — proceed to accept brief.",
            )


if __name__ == "__main__":
    unittest.main()
