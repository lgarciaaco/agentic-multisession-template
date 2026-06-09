#!/usr/bin/env python3
"""Smoke tests for workflow plan-reviewer rubric (M8)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from workflow_plan import synthesize_plan_verdict  # noqa: E402

HUB_ROOT = Path(__file__).resolve().parent.parent
PLAN_REVIEWER_RULES = (
    HUB_ROOT / ".cursor/skills/workflow-orchestrator/rules/plan-reviewer.md"
)
FINDINGS_SCHEMA = (
    HUB_ROOT / ".cursor/skills/workflow-orchestrator/references/findings-schema.md"
)


class PlanReviewerRulesSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rules_text = PLAN_REVIEWER_RULES.read_text()
        cls.schema_text = FINDINGS_SCHEMA.read_text()

    def test_plan_reviewer_rules_file_exists(self) -> None:
        self.assertTrue(PLAN_REVIEWER_RULES.is_file())

    def test_verdict_table_documents_three_outcomes(self) -> None:
        for verdict in ("APPROVE", "REVISE", "REJECT"):
            self.assertIn(verdict, self.rules_text)

    def test_blocker_never_used_for_plan_review(self) -> None:
        self.assertIn("BLOCKER", self.rules_text)
        self.assertIn("Never", self.rules_text)

    def test_required_rubric_sections_present(self) -> None:
        for section in (
            "Completeness vs brief",
            "Task quality",
            "Test and verification",
            "Traceability matrix",
            "Acceptance testability",
        ):
            self.assertIn(section, self.rules_text)

    def test_findings_schema_documents_plan_agent(self) -> None:
        self.assertIn("plan.json", self.schema_text)
        self.assertIn("criteria", self.schema_text)

    def test_synthesize_plan_verdict_approve_clean(self) -> None:
        doc = {
            "agent": "plan",
            "criteria": [{"id": "SC-1", "met": True}],
            "findings": [],
            "verdict": "APPROVE",
        }
        self.assertEqual(synthesize_plan_verdict(doc), "APPROVE")

    def test_synthesize_plan_verdict_revise_on_required(self) -> None:
        doc = {
            "agent": "plan",
            "criteria": [{"id": "SC-1", "met": True}],
            "findings": [{"severity": "REQUIRED", "issue": "missing test plan"}],
            "verdict": "APPROVE",
        }
        self.assertEqual(synthesize_plan_verdict(doc), "REVISE")

    def test_synthesize_plan_verdict_reject_honored(self) -> None:
        doc = {
            "agent": "plan",
            "criteria": [],
            "findings": [],
            "verdict": "REJECT",
        }
        self.assertEqual(synthesize_plan_verdict(doc), "REJECT")


if __name__ == "__main__":
    unittest.main()
