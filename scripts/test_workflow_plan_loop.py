#!/usr/bin/env python3
"""Smoke tests for workflow plan loop (M4)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from workflow_plan import (  # noqa: E402
    dedupe_findings,
    make_workflow_id,
    next_plan_review_id,
    persist_plan_review,
    plan_loop_escalate,
    resolve_plan_workspace,
    run_plan_loop,
    synthesize_plan_verdict,
    write_plan_scope_manifest,
)


FIXTURE_BRIEF = """# Problem brief — checkout fix

**Status:** accepted
**Accepted:** 2026-06-09

## Problem
Expired payment tokens show a generic error.

## Context
Support tickets increased after auth refactor.

## Constraints
Must not break valid-token checkout; my-app repo only.

## Success criteria
- SC-1: Expired token shows a clear user-facing message
- SC-2: Valid token checkout unchanged

## Out of scope
Payment provider migration.

## Open questions

"""


class WorkflowPlanLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.codename = "alpha"
        self.session_dir = self.root / "sessions" / self.codename
        self.session_dir.mkdir(parents=True)
        (self.session_dir / "artifacts").mkdir()
        (self.session_dir / "artifacts" / "problem-brief.md").write_text(FIXTURE_BRIEF)
        (self.session_dir / "artifacts" / "action-plan.md").write_text(
            "# Action plan — checkout fix\n\n**Status:** draft\n"
        )
        (self.session_dir / "session.json").write_text(
            json.dumps({"codename": self.codename, "mode": "product"}) + "\n"
        )
        (self.session_dir / "workflow.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "phase": "plan_loop",
                    "gates": {"brief_accepted": True, "plan_user_accepted": False},
                    "loops": {
                        "plan": {"iteration": 0, "max": 5, "last_verdict": None},
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

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_synthesize_revise_on_required(self) -> None:
        doc = {
            "agent": "plan",
            "criteria": [{"id": "SC-1", "criterion": "x", "met": True}],
            "findings": [{"severity": "REQUIRED", "issue": "vague acceptance on t1"}],
        }
        self.assertEqual(synthesize_plan_verdict(doc), "REVISE")

    def test_synthesize_approve_when_clean(self) -> None:
        doc = {
            "agent": "plan",
            "criteria": [
                {"id": "SC-1", "criterion": "x", "met": True},
                {"id": "SC-2", "criterion": "y", "met": True},
            ],
            "findings": [],
        }
        self.assertEqual(synthesize_plan_verdict(doc), "APPROVE")

    def test_dedupe_keeps_higher_severity(self) -> None:
        findings = [
            {"severity": "SUGGESTION", "issue": "same issue"},
            {"severity": "REQUIRED", "issue": "same issue"},
        ]
        out = dedupe_findings(findings)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["severity"], "REQUIRED")

    def test_next_plan_review_id_increments(self) -> None:
        plan_review = self.session_dir / "artifacts" / "plan-review"
        plan_review.mkdir(parents=True)
        (plan_review / "pr-001.json").write_text("{}\n")
        self.assertEqual(next_plan_review_id(plan_review), "pr-002")

    def test_write_plan_scope_manifest(self) -> None:
        workspace = self.session_dir / "reviews" / "workspace" / "wf-test"
        write_plan_scope_manifest(
            workspace,
            codename=self.codename,
            brief_path="sessions/alpha/artifacts/problem-brief.md",
            plan_path="sessions/alpha/artifacts/action-plan.md",
            workflow_id="wf-test",
        )
        manifest = json.loads((workspace / "plan_scope_manifest.json").read_text())
        self.assertEqual(manifest["phase"], "plan_review")
        self.assertTrue((workspace / "findings").is_dir())

    def test_plan_loop_revise_then_approve_without_user(self) -> None:
        revise_doc = {
            "agent": "plan",
            "criteria": [
                {"id": "SC-1", "criterion": "message", "met": False, "evidence": ""},
                {"id": "SC-2", "criterion": "valid", "met": True, "evidence": "t2"},
            ],
            "findings": [
                {
                    "severity": "REQUIRED",
                    "file": "artifacts/action-plan.md",
                    "issue": "SC-1 not covered by any task",
                    "fix": "Add task with testable acceptance",
                }
            ],
            "verdict": "REVISE",
        }
        approve_doc = {
            "agent": "plan",
            "criteria": [
                {"id": "SC-1", "criterion": "message", "met": True, "evidence": "t1"},
                {"id": "SC-2", "criterion": "valid", "met": True, "evidence": "t2"},
            ],
            "findings": [],
            "verdict": "APPROVE",
        }

        result = run_plan_loop(
            self.root,
            self.codename,
            [revise_doc, approve_doc],
            workflow_id="wf-20260609-120000",
        )

        self.assertEqual(result["verdicts"], ["REVISE", "APPROVE"])
        self.assertEqual(result["workflow"]["phase"], "plan_user_review")
        self.assertEqual(result["workflow"]["loops"]["plan"]["iteration"], 2)
        self.assertEqual(result["workflow"]["loops"]["plan"]["last_verdict"], "APPROVE")

        plan_review = self.session_dir / "artifacts" / "plan-review"
        self.assertTrue((plan_review / "pr-001.json").exists())
        self.assertTrue((plan_review / "pr-002.json").exists())
        pr2 = json.loads((plan_review / "pr-002.json").read_text())
        self.assertEqual(pr2["verdict"], "APPROVE")

        plan_text = (self.session_dir / "artifacts" / "action-plan.md").read_text()
        self.assertIn("**Status:** reviewer_approved", plan_text)

    def test_persist_plan_review_writes_report(self) -> None:
        workspace = self.session_dir / "reviews" / "workspace" / "wf-one"
        workspace.mkdir(parents=True)
        (workspace / "findings").mkdir()
        doc = {
            "agent": "plan",
            "criteria": [{"id": "SC-1", "met": True, "evidence": "t1"}],
            "findings": [],
        }
        review_id, verdict, _ = persist_plan_review(
            self.session_dir,
            workspace,
            doc,
            workflow_id="wf-one",
        )
        self.assertEqual(verdict, "APPROVE")
        self.assertEqual(review_id, "pr-001")
        self.assertTrue((workspace / "report.md").exists())

    def test_make_workflow_id_format(self) -> None:
        from datetime import datetime, timezone

        wid = make_workflow_id(datetime(2026, 6, 9, 12, 0, 0, tzinfo=timezone.utc))
        self.assertEqual(wid, "wf-20260609-120000")

    def test_plan_loop_reject_does_not_advance_phase(self) -> None:
        reject_doc = {
            "agent": "plan",
            "criteria": [],
            "findings": [],
            "verdict": "REJECT",
        }
        result = run_plan_loop(self.root, self.codename, [reject_doc], workflow_id="wf-reject")
        self.assertEqual(result["verdicts"], ["REJECT"])
        self.assertEqual(result["workflow"]["phase"], "plan_loop")
        self.assertTrue(plan_loop_escalate("REJECT", 1, 5))

    def test_plan_loop_max_iteration_revise_escalates(self) -> None:
        workflow_path = self.session_dir / "workflow.json"
        workflow = json.loads(workflow_path.read_text())
        workflow["loops"]["plan"]["max"] = 2
        workflow_path.write_text(json.dumps(workflow, indent=2) + "\n")

        revise_doc = {
            "agent": "plan",
            "criteria": [{"id": "SC-1", "met": False}],
            "findings": [{"severity": "REQUIRED", "issue": "gap"}],
            "verdict": "REVISE",
        }
        result = run_plan_loop(
            self.root,
            self.codename,
            [revise_doc, revise_doc],
            workflow_id="wf-maxed",
        )
        self.assertEqual(result["verdicts"], ["REVISE", "REVISE"])
        self.assertEqual(result["workflow"]["phase"], "plan_loop")
        self.assertNotEqual(result["workflow"]["phase"], "plan_user_review")

    def test_resolve_plan_workspace_rejects_traversal(self) -> None:
        with self.assertRaises(ValueError):
            resolve_plan_workspace(
                self.root,
                self.codename,
                "sessions/alpha/reviews/workspace/../session.json",
            )
        with self.assertRaises(ValueError):
            resolve_plan_workspace(self.root, self.codename, "sessions/bravo/reviews/workspace/wf-x")

    def test_workflow_plan_synthesize_cli_subprocess(self) -> None:
        workspace = self.session_dir / "reviews" / "workspace" / "wf-cli"
        workspace.mkdir(parents=True)
        (workspace / "findings").mkdir()
        (workspace / "plan_scope_manifest.json").write_text(
            json.dumps({"workflow_id": "wf-cli"}) + "\n"
        )
        (workspace / "findings" / "plan.json").write_text(
            json.dumps(
                {
                    "agent": "plan",
                    "criteria": [{"id": "SC-1", "met": True, "evidence": "t1"}],
                    "findings": [],
                    "verdict": "APPROVE",
                }
            )
            + "\n"
        )
        script = Path(__file__).resolve().parent / "workflow-plan-synthesize.py"
        env = {**os.environ, "WORKSPACE_ROOT": str(self.root)}
        rel = "sessions/alpha/reviews/workspace/wf-cli"
        result = subprocess.run(
            [sys.executable, str(script), "alpha", rel],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.strip().splitlines()
        self.assertEqual(lines[0], "pr-001")
        self.assertEqual(lines[1], "APPROVE")
        workflow = json.loads((self.session_dir / "workflow.json").read_text())
        self.assertEqual(workflow["phase"], "plan_user_review")

    def test_workflow_plan_synthesize_cli_rejects_bad_path(self) -> None:
        script = Path(__file__).resolve().parent / "workflow-plan-synthesize.py"
        env = {**os.environ, "WORKSPACE_ROOT": str(self.root)}
        result = subprocess.run(
            [sys.executable, str(script), "alpha", "sessions/bravo/reviews/workspace/wf-evil"],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
