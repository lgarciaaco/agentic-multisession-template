#!/usr/bin/env python3
"""Tests for workflow code review loop (M6)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from workflow_code_review import (  # noqa: E402
    advance_code_review_loop,
    begin_code_review_loop,
    code_review_loop_complete,
    code_review_loop_escalate,
    enrich_scope_manifest,
    implementation_ready_for_review,
    implementation_tasks_complete,
    mark_implementation_ready,
    next_code_review_id,
    resolve_code_review_workspace,
    run_code_review_loop,
    synthesize_code_review_verdict,
    workflow_acceptance_criteria,
)

FIXTURE_PLAN = """# Action plan — checkout fix

**Status:** user_approved
**Based on:** problem-brief.md @ accepted
**Version:** 1

## Tasks

| ID | Repo | Summary | Acceptance | Depends |
|----|------|---------|------------|---------|
| t1 | my-app | Show expired token message | UI test passes | — |
| t2 | my-app | Keep valid checkout | Regression test passes | t1 |

## Test plan

pytest tests/
"""


class WorkflowCodeReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.codename = "alpha"
        self.session_dir = self.root / "sessions" / self.codename
        self.session_dir.mkdir(parents=True)
        (self.session_dir / "artifacts").mkdir()
        (self.session_dir / "artifacts" / "action-plan.md").write_text(FIXTURE_PLAN)
        (self.session_dir / "session.json").write_text(
            json.dumps(
                {
                    "codename": self.codename,
                    "mode": "product",
                    "tasks": [
                        {
                            "id": "t1",
                            "title": "Show expired token message",
                            "repo": "my-app",
                            "status": "done",
                            "acceptance": "UI test passes",
                        },
                        {
                            "id": "t2",
                            "title": "Keep valid checkout",
                            "repo": "my-app",
                            "status": "done",
                            "acceptance": "Regression test passes",
                        },
                    ],
                }
            )
            + "\n"
        )
        (self.session_dir / "workflow.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "phase": "implementation",
                    "gates": {"brief_accepted": True, "plan_user_accepted": True},
                    "loops": {
                        "plan": {"iteration": 1, "max": 5, "last_verdict": "APPROVE"},
                        "code_review": {"iteration": 0, "max": 5, "last_verdict": None},
                    },
                    "artifacts": {
                        "brief": "artifacts/problem-brief.md",
                        "plan": "artifacts/action-plan.md",
                    },
                }
            )
            + "\n"
        )
        (self.session_dir / "progress.json").write_text(
            json.dumps({"status": "active", "session": self.codename}) + "\n"
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_workflow_acceptance_criteria_prefers_action_plan(self) -> None:
        criteria = workflow_acceptance_criteria(self.session_dir)
        self.assertEqual(len(criteria), 2)
        by_id = {item["id"]: item for item in criteria}
        self.assertEqual(by_id["t1"]["source"], "action-plan")
        self.assertEqual(by_id["t1"]["acceptance"], "UI test passes")

    def test_enrich_scope_manifest_adds_workflow_block(self) -> None:
        workspace = self.session_dir / "reviews" / "workspace" / "review-test"
        workspace.mkdir(parents=True)
        manifest_path = workspace / "scope_manifest.json"
        manifest_path.write_text(
            json.dumps({"scope": "changeset", "files": [], "triggers": {}}) + "\n"
        )
        enrich_scope_manifest(manifest_path, self.session_dir, codename=self.codename)
        manifest = json.loads(manifest_path.read_text())
        self.assertIn("workflow", manifest)
        self.assertEqual(len(manifest["workflow"]["acceptance_criteria"]), 2)

    def test_code_review_loop_incomplete_then_pass(self) -> None:
        result = run_code_review_loop(
            self.root,
            self.codename,
            ["INCOMPLETE", "PASS"],
            workspace_id="review-fixture",
        )
        self.assertEqual(result["verdicts"][:2], ["INCOMPLETE", "PASS"])
        self.assertEqual(result["workflow"]["phase"], "pr_creation")
        code_loop = result["workflow"]["loops"]["code_review"]
        self.assertEqual(code_loop["iteration"], 2)
        self.assertEqual(code_loop["last_verdict"], "PASS")
        self.assertEqual(result["progress"]["last_review"]["id"], "r-002")
        self.assertEqual(result["progress"]["last_review"]["verdict"], "PASS")

    def test_begin_code_review_requires_ready_slice(self) -> None:
        session_path = self.session_dir / "session.json"
        session = json.loads(session_path.read_text())
        for task in session["tasks"]:
            task["status"] = "in_progress"
        session_path.write_text(json.dumps(session, indent=2) + "\n")
        self.assertFalse(implementation_ready_for_review(self.session_dir)[0])
        with self.assertRaises(ValueError):
            begin_code_review_loop(self.session_dir)

    def test_mark_implementation_ready_begins_review_for_task(self) -> None:
        session_path = self.session_dir / "session.json"
        session = json.loads(session_path.read_text())
        session["tasks"][0]["status"] = "done"
        session["tasks"][1]["status"] = "pending"
        session_path.write_text(json.dumps(session, indent=2) + "\n")
        mark_implementation_ready(self.session_dir, "t1")
        workflow = begin_code_review_loop(self.session_dir)
        self.assertEqual(workflow["phase"], "code_review_loop")
        self.assertEqual(workflow["loops"]["code_review"]["task_id"], "t1")

    def test_synthesize_incomplete_on_open_suggestion(self) -> None:
        docs = [
            {
                "agent": "code-python",
                "findings": [{"severity": "SUGGESTION", "issue": "refactor"}],
            }
        ]
        self.assertEqual(synthesize_code_review_verdict(docs), "INCOMPLETE")

    def test_synthesize_pass_when_clean(self) -> None:
        docs = [{"agent": "code-python", "findings": []}]
        self.assertEqual(synthesize_code_review_verdict(docs), "PASS")

    def test_code_review_loop_escalate_on_fail(self) -> None:
        self.assertTrue(code_review_loop_escalate("FAIL", 1, 5))
        self.assertFalse(code_review_loop_escalate("INCOMPLETE", 1, 5))
        self.assertTrue(code_review_loop_escalate("INCOMPLETE", 5, 5))
        self.assertTrue(code_review_loop_complete("PASS_WITH_NITS"))

    def test_next_code_review_id(self) -> None:
        reviews = self.session_dir / "reviews"
        reviews.mkdir()
        (reviews / "r-001.json").write_text("{}\n")
        self.assertEqual(next_code_review_id(reviews), "r-002")

    def test_resolve_code_review_workspace_rejects_traversal(self) -> None:
        with self.assertRaises(ValueError):
            resolve_code_review_workspace(
                self.root,
                self.codename,
                "sessions/alpha/reviews/workspace/../session.json",
            )

    def test_workflow_code_review_advance_cli_subprocess(self) -> None:
        reviews = self.session_dir / "reviews"
        reviews.mkdir()
        (reviews / "r-001.json").write_text(
            json.dumps(
                {
                    "id": "r-001",
                    "verdict": "PASS_WITH_NITS",
                    "workspace": "sessions/alpha/reviews/workspace/review-cli",
                    "scope": "changeset",
                }
            )
            + "\n"
        )
        workflow_path = self.session_dir / "workflow.json"
        workflow = json.loads(workflow_path.read_text())
        workflow["phase"] = "code_review_loop"
        workflow_path.write_text(json.dumps(workflow, indent=2) + "\n")

        script = Path(__file__).resolve().parent / "workflow-code-review-advance.py"
        env = {**os.environ, "WORKSPACE_ROOT": str(self.root)}
        result = subprocess.run(
            [sys.executable, str(script), "alpha", "r-001"],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.strip().splitlines()
        self.assertEqual(lines[0], "r-001")
        self.assertEqual(lines[1], "PASS_WITH_NITS")
        self.assertEqual(lines[2], "pr_creation")
        workflow = json.loads(workflow_path.read_text())
        self.assertEqual(workflow["phase"], "pr_creation")

    def test_workflow_code_review_enrich_scope_cli(self) -> None:
        workspace = self.session_dir / "reviews" / "workspace" / "review-enrich"
        workspace.mkdir(parents=True)
        (workspace / "scope_manifest.json").write_text(
            json.dumps({"scope": "changeset", "files": []}) + "\n"
        )
        script = Path(__file__).resolve().parent / "workflow-code-review-enrich-scope.py"
        env = {**os.environ, "WORKSPACE_ROOT": str(self.root)}
        rel = "sessions/alpha/reviews/workspace/review-enrich"
        result = subprocess.run(
            [sys.executable, str(script), "alpha", rel],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads((workspace / "scope_manifest.json").read_text())
        self.assertIn("workflow", manifest)

    def test_workflow_begin_code_review_cli_subprocess(self) -> None:
        script = Path(__file__).resolve().parent / "workflow-begin-code-review.py"
        env = {**os.environ, "WORKSPACE_ROOT": str(self.root)}
        result = subprocess.run(
            [sys.executable, str(script), "alpha"],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "code_review_loop")
        workflow = json.loads((self.session_dir / "workflow.json").read_text())
        self.assertEqual(workflow["phase"], "code_review_loop")

    def test_code_review_loop_fail_escalates_without_delivery(self) -> None:
        result = run_code_review_loop(self.root, self.codename, ["FAIL"], workspace_id="review-fail")
        self.assertEqual(result["verdicts"], ["FAIL"])
        self.assertEqual(result["workflow"]["phase"], "code_review_loop")
        self.assertTrue(code_review_loop_escalate("FAIL", 1, 5))

    def test_code_review_loop_max_incomplete_escalates(self) -> None:
        workflow_path = self.session_dir / "workflow.json"
        workflow = json.loads(workflow_path.read_text())
        workflow["loops"]["code_review"]["max"] = 2
        workflow_path.write_text(json.dumps(workflow, indent=2) + "\n")

        result = run_code_review_loop(
            self.root,
            self.codename,
            ["INCOMPLETE", "INCOMPLETE"],
            workspace_id="review-maxed",
        )
        self.assertEqual(result["verdicts"], ["INCOMPLETE", "INCOMPLETE"])
        self.assertEqual(result["workflow"]["phase"], "code_review_loop")
        self.assertNotEqual(result["workflow"]["phase"], "delivery")

    def test_advance_without_review_id_uses_latest(self) -> None:
        reviews = self.session_dir / "reviews"
        reviews.mkdir()
        (reviews / "r-001.json").write_text(
            json.dumps({"id": "r-001", "verdict": "INCOMPLETE", "workspace": "w1"}) + "\n"
        )
        (reviews / "r-002.json").write_text(
            json.dumps({"id": "r-002", "verdict": "PASS", "workspace": "w2"}) + "\n"
        )
        workflow_path = self.session_dir / "workflow.json"
        workflow = json.loads(workflow_path.read_text())
        workflow["phase"] = "code_review_loop"
        workflow_path.write_text(json.dumps(workflow, indent=2) + "\n")

        workflow = advance_code_review_loop(self.session_dir, "PASS")
        self.assertEqual(workflow["phase"], "pr_creation")
        progress = json.loads((self.session_dir / "progress.json").read_text())
        self.assertEqual(progress["last_review"]["id"], "r-002")


if __name__ == "__main__":
    unittest.main()
