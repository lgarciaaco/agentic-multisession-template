#!/usr/bin/env python3
"""Tests for workflow delivery, resume, and reopen (M7)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from session_binding import build_context_markdown, format_workflow_section  # noqa: E402
from workflow_delivery import render_delivery_report, write_delivery_report  # noqa: E402
from workflow_resume import (  # noqa: E402
    reopen_brief,
    reopen_plan,
    workflow_next_action,
)

FIXTURE_WORKFLOW = {
    "version": 1,
    "phase": "plan_loop",
    "gates": {"brief_accepted": True, "plan_user_accepted": False},
    "loops": {
        "plan": {"iteration": 2, "max": 5, "last_verdict": "REVISE"},
        "code_review": {"iteration": 0, "max": 5, "last_verdict": None},
    },
    "artifacts": {
        "brief": "artifacts/problem-brief.md",
        "plan": "artifacts/action-plan.md",
        "delivery": "artifacts/delivery-report.md",
    },
}


class WorkflowResumeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.codename = "alpha"
        self.session_dir = self.root / "sessions" / self.codename
        self.session_dir.mkdir(parents=True)
        (self.session_dir / "workflow.json").write_text(
            json.dumps(FIXTURE_WORKFLOW, indent=2) + "\n"
        )
        (self.session_dir / "session.json").write_text(
            json.dumps(
                {
                    "codename": self.codename,
                    "title": "Checkout fix",
                    "tasks": [
                        {"id": "t1", "status": "done", "note": "Expired token UI"},
                        {"id": "t2", "status": "pending", "note": "Regression"},
                    ],
                    "next": "Open PR and deploy",
                }
            )
            + "\n"
        )
        (self.session_dir / "TASKS.md").write_text("# alpha\n\n## Goal\n\nFix checkout.\n")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_workflow_next_action_plan_loop_resume(self) -> None:
        action = workflow_next_action(FIXTURE_WORKFLOW)
        self.assertIn("plan loop", action.lower())
        self.assertIn("iteration 2/5", action)
        self.assertIn("REVISE", action)
        self.assertIn("workflow-plan-synthesize.py", action)

    def test_workflow_next_action_code_review_loop(self) -> None:
        action = workflow_next_action(
            {
                "phase": "code_review_loop",
                "gates": {"brief_accepted": True, "plan_user_accepted": True},
                "loops": {"code_review": {"iteration": 1, "max": 5, "last_verdict": "INCOMPLETE"}},
            }
        )
        self.assertIn("AUTO", action)
        self.assertIn("code review loop", action.lower())
        self.assertIn("code-reviewer SKILL", action)
        self.assertIn("1/5", action)

    def test_reopen_brief_resets_code_review_loop(self) -> None:
        wf_path = self.session_dir / "workflow.json"
        wf = json.loads(wf_path.read_text())
        wf["loops"]["code_review"] = {"iteration": 3, "max": 5, "last_verdict": "FAIL", "task_id": "t1"}
        wf_path.write_text(json.dumps(wf, indent=2) + "\n")
        workflow = reopen_brief(self.session_dir)
        code_loop = workflow["loops"]["code_review"]
        self.assertEqual(code_loop["iteration"], 0)
        self.assertIsNone(code_loop["last_verdict"])
        self.assertIsNone(code_loop["task_id"])

    def test_workflow_next_action_plan_user_review(self) -> None:
        action = workflow_next_action({"phase": "plan_user_review", "gates": {}, "loops": {}})
        self.assertIn("refused dispositions", action)
        self.assertIn("accept plan", action)
        self.assertIn("plan-feedback", action)

    def test_format_workflow_section_includes_resume_hint(self) -> None:
        section = format_workflow_section(self.root, self.codename)
        self.assertIn("**Resume:**", section)
        self.assertIn("plan loop", section.lower())

    def test_build_context_resume_mid_plan_loop(self) -> None:
        ctx = build_context_markdown(self.root, self.codename, "chat-resume")
        self.assertIn("**Phase:** `plan_loop`", ctx)
        self.assertIn("**Resume:**", ctx)
        self.assertIn("workflow-plan-synthesize.py", ctx)

    def test_reopen_brief_resets_gates_and_phase(self) -> None:
        workflow = reopen_brief(self.session_dir)
        self.assertEqual(workflow["phase"], "intake")
        self.assertFalse(workflow["gates"]["brief_accepted"])
        self.assertFalse(workflow["gates"]["plan_user_accepted"])
        self.assertEqual(workflow["loops"]["plan"]["iteration"], 0)

    def test_reopen_plan_keeps_brief_gate(self) -> None:
        workflow_path = self.session_dir / "workflow.json"
        workflow = json.loads(workflow_path.read_text())
        workflow["gates"]["plan_user_accepted"] = True
        workflow["phase"] = "implementation"
        workflow_path.write_text(json.dumps(workflow, indent=2) + "\n")

        workflow = reopen_plan(self.session_dir)
        self.assertEqual(workflow["phase"], "plan_loop")
        self.assertTrue(workflow["gates"]["brief_accepted"])
        self.assertFalse(workflow["gates"]["plan_user_accepted"])

    def test_reopen_plan_requires_brief_accepted(self) -> None:
        workflow_path = self.session_dir / "workflow.json"
        workflow = json.loads(workflow_path.read_text())
        workflow["gates"]["brief_accepted"] = False
        workflow_path.write_text(json.dumps(workflow, indent=2) + "\n")
        with self.assertRaises(ValueError):
            reopen_plan(self.session_dir)

    def test_render_delivery_report(self) -> None:
        reviews = self.session_dir / "reviews"
        reviews.mkdir()
        (reviews / "r-001.json").write_text(
            json.dumps(
                {
                    "id": "r-001",
                    "verdict": "PASS_WITH_NITS",
                    "findings_count": {"required": 0, "suggestion": 1, "nit": 2},
                }
            )
            + "\n"
        )
        plan_review = self.session_dir / "artifacts" / "plan-review"
        plan_review.mkdir(parents=True)
        (plan_review / "pr-001.json").write_text(
            json.dumps({"id": "pr-001", "verdict": "APPROVE"}) + "\n"
        )
        workflow_path = self.session_dir / "workflow.json"
        workflow = json.loads(workflow_path.read_text())
        workflow["phase"] = "delivery"
        workflow["loops"]["plan"]["last_verdict"] = "APPROVE"
        workflow["loops"]["code_review"]["last_verdict"] = "PASS_WITH_NITS"
        workflow_path.write_text(json.dumps(workflow, indent=2) + "\n")

        text = render_delivery_report(self.session_dir, codename=self.codename)
        self.assertIn("# Delivery report — Checkout fix", text)
        self.assertIn("**t1:**", text)
        self.assertIn("PASS_WITH_NITS", text)
        self.assertIn("pr-001", text)
        self.assertIn("r-001", text)
        self.assertIn("Open PR and deploy", text)

    def test_write_delivery_report_sets_completed(self) -> None:
        workflow_path = self.session_dir / "workflow.json"
        workflow = json.loads(workflow_path.read_text())
        workflow["phase"] = "delivery"
        workflow_path.write_text(json.dumps(workflow, indent=2) + "\n")

        path = write_delivery_report(self.session_dir, codename=self.codename)
        self.assertTrue(path.exists())
        workflow = json.loads(workflow_path.read_text())
        self.assertEqual(workflow["phase"], "completed")

    def test_workflow_reopen_brief_cli(self) -> None:
        script = Path(__file__).resolve().parent / "workflow-reopen-brief.py"
        env = {**os.environ, "WORKSPACE_ROOT": str(self.root)}
        result = subprocess.run(
            [sys.executable, str(script), "alpha"],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.strip().splitlines()
        self.assertEqual(lines[0], "intake")
        workflow = json.loads((self.session_dir / "workflow.json").read_text())
        self.assertEqual(workflow["phase"], "intake")

    def test_workflow_write_delivery_cli(self) -> None:
        workflow_path = self.session_dir / "workflow.json"
        workflow = json.loads(workflow_path.read_text())
        workflow["phase"] = "delivery"
        workflow_path.write_text(json.dumps(workflow, indent=2) + "\n")

        script = Path(__file__).resolve().parent / "workflow-write-delivery-report.py"
        env = {**os.environ, "WORKSPACE_ROOT": str(self.root)}
        result = subprocess.run(
            [sys.executable, str(script), "alpha"],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.strip().splitlines()
        self.assertTrue(lines[-1], "completed")
        self.assertTrue((self.session_dir / "artifacts" / "delivery-report.md").exists())


if __name__ == "__main__":
    unittest.main()
