#!/usr/bin/env python3
"""Tests for workflow delivery report generation."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "lib"))

from workflow_delivery import render_delivery_report, write_delivery_report  # noqa: E402


class WorkflowDeliveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tmpdir.name)
        self.codename = "alpha"
        self.session_dir = self.root / "sessions" / self.codename
        self.session_dir.mkdir(parents=True)
        (self.session_dir / "session.json").write_text(
            json.dumps(
                {
                    "codename": self.codename,
                    "title": "Test session",
                    "tasks": [
                        {"id": "t1", "status": "done", "note": "Shipped"},
                        {"id": "t2", "status": "pending"},
                    ],
                }
            )
            + "\n"
        )
        (self.session_dir / "workflow.json").write_text(
            json.dumps(
                {
                    "phase": "delivery",
                    "artifacts": {"delivery": "artifacts/delivery-report.md"},
                    "loops": {
                        "plan": {"last_verdict": "APPROVE"},
                        "code_review": {"last_verdict": "PASS"},
                    },
                }
            )
            + "\n"
        )
        (self.session_dir / "artifacts").mkdir()

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_render_delivery_report_lists_done_and_pending(self) -> None:
        text = render_delivery_report(self.session_dir, codename=self.codename)
        self.assertIn("t1", text)
        self.assertIn("t2", text)
        self.assertIn("PASS", text)

    def test_write_delivery_report_sets_completed_phase(self) -> None:
        path = write_delivery_report(self.session_dir, codename=self.codename)
        self.assertTrue(path.exists())
        workflow = json.loads((self.session_dir / "workflow.json").read_text())
        self.assertEqual(workflow.get("phase"), "completed")

    def test_write_delivery_report_rejects_traversal_artifact(self) -> None:
        workflow_path = self.session_dir / "workflow.json"
        workflow = json.loads(workflow_path.read_text())
        workflow["artifacts"]["delivery"] = "../../../escape.md"
        workflow_path.write_text(json.dumps(workflow, indent=2) + "\n")
        with self.assertRaises(ValueError):
            write_delivery_report(self.session_dir, codename=self.codename)


if __name__ == "__main__":
    unittest.main()
