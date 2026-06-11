#!/usr/bin/env python3
"""Tests for PR creation phase (workflow_pr_creation.py)."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))

from workflow_pr_creation import (  # noqa: E402
    advance_pr_creation,
    begin_pr_creation,
    pr_creation_escalate,
)


class PrCreationPhaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.session_dir = self.root / "sessions" / "test"
        self.session_dir.mkdir(parents=True)
        workflow = {
            "version": 2,
            "phase": "pr_creation",
            "gates": {"brief_accepted": True, "plan_user_accepted": True},
            "loops": {
                "plan": {"iteration": 1, "max": 5, "last_verdict": "APPROVE"},
                "code_review": {"iteration": 1, "max": 5, "last_verdict": "PASS", "task_id": "t1"},
                "implementation": {"active_task": "t1", "ready_for_review": False},
                "pr_creation": {"iteration": 0, "max": 5, "last_verdict": None},
                "ci_observe": {"iteration": 0, "max": 5, "last_verdict": None},
            },
            "artifacts": {},
        }
        (self.session_dir / "workflow.json").write_text(json.dumps(workflow, indent=2) + "\n")
        session = {
            "codename": "test",
            "tasks": [{"id": "t1", "repo": "template", "status": "done"}],
        }
        (self.session_dir / "session.json").write_text(json.dumps(session, indent=2) + "\n")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_begin_pr_creation_resets_loop(self) -> None:
        workflow = begin_pr_creation(self.session_dir)
        pr_loop = workflow["loops"]["pr_creation"]
        self.assertEqual(pr_loop["iteration"], 0)
        self.assertIsNone(pr_loop["last_verdict"])

    def test_advance_success_transitions_to_ci_observe(self) -> None:
        workflow = advance_pr_creation(
            self.session_dir, "SUCCESS", pr_url="https://github.com/org/repo/pull/42"
        )
        self.assertEqual(workflow["phase"], "ci_observe")
        self.assertEqual(workflow["loops"]["pr_creation"]["last_verdict"], "SUCCESS")
        session = json.loads((self.session_dir / "session.json").read_text())
        self.assertEqual(session["tasks"][0]["pr"], "https://github.com/org/repo/pull/42")

    def test_advance_retry_stays_in_pr_creation(self) -> None:
        workflow = advance_pr_creation(self.session_dir, "RETRY")
        self.assertEqual(workflow["phase"], "pr_creation")
        self.assertEqual(workflow["loops"]["pr_creation"]["iteration"], 1)

    def test_advance_fail_stays_in_pr_creation(self) -> None:
        workflow = advance_pr_creation(self.session_dir, "FAIL")
        self.assertEqual(workflow["phase"], "pr_creation")

    def test_escalate_at_max_iterations(self) -> None:
        self.assertTrue(pr_creation_escalate("RETRY", 5, 5))
        self.assertFalse(pr_creation_escalate("RETRY", 3, 5))
        self.assertTrue(pr_creation_escalate("FAIL", 1, 5))

    def test_pr_url_recorded_on_task(self) -> None:
        advance_pr_creation(
            self.session_dir, "SUCCESS", pr_url="https://github.com/org/repo/pull/99"
        )
        session = json.loads((self.session_dir / "session.json").read_text())
        self.assertEqual(session["tasks"][0]["pr"], "https://github.com/org/repo/pull/99")

    def test_success_without_pr_url_raises(self) -> None:
        with self.assertRaises(ValueError):
            advance_pr_creation(self.session_dir, "SUCCESS")

    def test_unknown_verdict_raises(self) -> None:
        with self.assertRaises(ValueError):
            advance_pr_creation(self.session_dir, "BOGUS")

    def test_success_resets_ci_observe_counters(self) -> None:
        wf = json.loads((self.session_dir / "workflow.json").read_text())
        wf["loops"]["ci_observe"]["iteration"] = 3
        wf["loops"]["ci_observe"]["last_verdict"] = "CONFLICT"
        (self.session_dir / "workflow.json").write_text(json.dumps(wf, indent=2) + "\n")
        workflow = advance_pr_creation(
            self.session_dir, "SUCCESS", pr_url="https://github.com/org/repo/pull/1"
        )
        self.assertEqual(workflow["loops"]["ci_observe"]["iteration"], 0)
        self.assertIsNone(workflow["loops"]["ci_observe"]["last_verdict"])

    def test_pr_target_branch_resolution(self) -> None:
        from repos import pr_target_branch

        cfg = {"default_branch": "main", "pr_target_branch": "release-4.18"}
        self.assertEqual(pr_target_branch(cfg), "release-4.18")

    def test_advance_cli_subprocess(self) -> None:
        script = Path(__file__).resolve().parent / "workflow-advance-pr-creation.py"
        env = {"PYTHONPATH": str(Path(__file__).resolve().parent / "lib")}
        env["WORKSPACE_ROOT"] = str(self.root)
        result = subprocess.run(
            [sys.executable, str(script), "test", "SUCCESS", "https://github.com/x/y/pull/1"],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.strip().splitlines()
        self.assertEqual(lines[1], "SUCCESS")
        self.assertEqual(lines[2], "ci_observe")


if __name__ == "__main__":
    unittest.main()
