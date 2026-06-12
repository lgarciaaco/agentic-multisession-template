#!/usr/bin/env python3
"""Tests for workflow inbox gate feedback."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from session_binding import write_inbox  # noqa: E402
from workflow_inbox_gate import (  # noqa: E402
    INBOX_POLL_SECONDS,
    accept_brief,
    classify_gate_message,
    parse_inbox_blocks,
    pull_inbox_gate,
    pull_inbox_gate_json,
)


FIXTURE_BRIEF = """# Problem brief — checkout fix

**Status:** draft
**Accepted:** —

## Problem
Token expiry is unclear.

## Context
Support tickets.

## Constraints
my-app repo only.

## Success criteria
- SC-1: User sees expired token message

## Out of scope
New payment provider.

## Open questions

- What copy?
"""


class WorkflowInboxGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.codename = "alpha"
        self.session_dir = self.root / "sessions" / self.codename
        self.session_dir.mkdir(parents=True)
        (self.session_dir / "artifacts").mkdir()
        (self.session_dir / "artifacts" / "problem-brief.md").write_text(FIXTURE_BRIEF)
        (self.session_dir / "session.json").write_text(
            json.dumps({"codename": self.codename, "tasks": []}) + "\n"
        )
        (self.session_dir / "workflow.json").write_text(
            json.dumps(
                {
                    "version": 2,
                    "phase": "brief_review",
                    "gates": {
                        "brief_accepted": False,
                        "plan_user_accepted": False,
                        "inbox": {"processed_markers": [], "last_pull_at": None},
                    },
                    "loops": {"plan": {"iteration": 0, "max": 5, "last_verdict": None}},
                    "artifacts": {
                        "brief": "artifacts/problem-brief.md",
                        "plan": "artifacts/action-plan.md",
                        "plan_feedback": "artifacts/plan-feedback.md",
                    },
                }
            )
            + "\n"
        )
        (self.root / "sessions" / "bravo").mkdir(parents=True)
        (self.root / "sessions" / "bravo" / "session.json").write_text(
            json.dumps({"codename": "bravo", "tasks": []}) + "\n"
        )
        (self.root / "sessions" / "bravo" / "TASKS.md").write_text("# Goal\n")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_classify_gate_message_brief_accept(self) -> None:
        self.assertEqual(classify_gate_message("brief_review", "accept brief"), "accept_brief")
        self.assertEqual(classify_gate_message("brief_review", "accept"), "accept_brief")
        self.assertEqual(
            classify_gate_message("brief_review", "Please tighten SC-1 wording."),
            "brief_correction",
        )

    def test_classify_gate_message_plan_accept(self) -> None:
        self.assertEqual(classify_gate_message("plan_user_review", "accept plan"), "accept_plan")
        self.assertEqual(
            classify_gate_message("plan_user_review", "accept"),
            "plan_feedback",
        )
        self.assertEqual(
            classify_gate_message("plan_user_review", "Split t2 into two tasks."),
            "plan_feedback",
        )

    def test_parse_inbox_blocks(self) -> None:
        write_inbox(self.root, "bravo", "alpha", "accept brief")
        content = (self.root / "sessions" / "_inbox" / "alpha.md").read_text()
        blocks = parse_inbox_blocks(content)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]["from"], "bravo")
        self.assertEqual(blocks[0]["body"], "accept brief")

    def test_pull_inbox_gate_reports_pending(self) -> None:
        write_inbox(self.root, "bravo", "alpha", "accept brief")
        result = pull_inbox_gate(self.root, self.codename, apply=False)
        self.assertTrue(result["gate_phase"])
        self.assertEqual(result["poll_seconds"], INBOX_POLL_SECONDS)
        self.assertEqual(len(result["pending"]), 1)
        self.assertEqual(result["pending"][0]["action"], "accept_brief")

    def test_pull_inbox_gate_apply_accept_brief(self) -> None:
        write_inbox(self.root, "bravo", "alpha", "accept brief")
        result = pull_inbox_gate(self.root, self.codename, apply=True)
        self.assertEqual(result["applied"][0]["action"], "accept_brief")
        workflow = json.loads((self.session_dir / "workflow.json").read_text())
        self.assertTrue(workflow["gates"]["brief_accepted"])
        self.assertEqual(workflow["phase"], "plan_loop")
        brief = (self.session_dir / "artifacts" / "problem-brief.md").read_text()
        self.assertIn("**Status:** accepted", brief)

        second = pull_inbox_gate(self.root, self.codename, apply=True)
        self.assertEqual(second["pending"], [])

    def test_accept_brief_rejects_wrong_phase(self) -> None:
        workflow_path = self.session_dir / "workflow.json"
        workflow = json.loads(workflow_path.read_text())
        workflow["phase"] = "intake"
        workflow_path.write_text(json.dumps(workflow) + "\n")
        with self.assertRaises(ValueError):
            accept_brief(self.root, self.codename)

    def test_pull_inbox_gate_ignores_non_gate_phase(self) -> None:
        write_inbox(self.root, "bravo", "alpha", "accept brief")
        workflow_path = self.session_dir / "workflow.json"
        workflow = json.loads(workflow_path.read_text())
        workflow["phase"] = "implementation"
        workflow_path.write_text(json.dumps(workflow) + "\n")
        result = pull_inbox_gate(self.root, self.codename, apply=False)
        self.assertFalse(result["gate_phase"])
        self.assertEqual(result["pending"], [])

    def test_pull_inbox_gate_apply_brief_correction(self) -> None:
        write_inbox(self.root, "bravo", "alpha", "Tighten SC-1 wording for clarity.")
        result = pull_inbox_gate(self.root, self.codename, apply=True)
        self.assertEqual(result["applied"][0]["action"], "brief_correction")
        workflow = json.loads((self.session_dir / "workflow.json").read_text())
        self.assertEqual(workflow["phase"], "brief_review")
        brief = (self.session_dir / "artifacts" / "problem-brief.md").read_text()
        self.assertIn("Inbox correction from `bravo`", brief)
        self.assertIn("Tighten SC-1 wording", brief)

    def test_pull_inbox_gate_json_helper(self) -> None:
        payload = pull_inbox_gate_json(self.root, self.codename, apply=False)
        parsed = json.loads(payload)
        self.assertEqual(parsed["codename"], self.codename)

    def test_sync_session_auto_applies_accept_brief(self) -> None:
        from session_binding import sync_session_from_canonical  # noqa: E402

        write_inbox(self.root, "bravo", "alpha", "accept brief")
        sync_session_from_canonical(self.root, self.codename, refresh_context=False)
        workflow = json.loads((self.session_dir / "workflow.json").read_text())
        self.assertTrue(workflow["gates"]["brief_accepted"])
        self.assertEqual(workflow["phase"], "plan_loop")


if __name__ == "__main__":
    unittest.main()
