#!/usr/bin/env python3
"""Tests for workflow inbox gate feedback."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from program_route_feedback import route_feedback  # noqa: E402
from program_state import default_program, save_program  # noqa: E402
from session_binding import sync_session_from_canonical, write_inbox  # noqa: E402
from workflow_inbox_gate import (  # noqa: E402
    INBOX_POLL_SECONDS,
    accept_brief,
    apply_brief_correction,
    apply_plan_feedback,
    classify_gate_message,
    gate_command_sender_authorized,
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
        self.parent = "mike"
        self.child = "november"
        self.sibling = "bravo"
        self.codename = self.child

        parent_dir = self.root / "sessions" / self.parent
        child_dir = self.root / "sessions" / self.child
        sibling_dir = self.root / "sessions" / self.sibling
        for session_dir in (parent_dir, child_dir, sibling_dir):
            session_dir.mkdir(parents=True)
            (session_dir / "session.json").write_text(
                json.dumps({"codename": session_dir.name, "tasks": []}) + "\n"
            )
            (session_dir / "TASKS.md").write_text("# Goal\n")

        program = default_program(self.parent)
        program["active_children"] = [{"codename": self.child, "status": "running"}]
        save_program(parent_dir, program)

        self.session_dir = child_dir
        (self.session_dir / "artifacts").mkdir()
        (self.session_dir / "artifacts" / "problem-brief.md").write_text(FIXTURE_BRIEF)
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

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _route_parent_accept_brief(self) -> None:
        route_feedback(
            self.root,
            parent=self.parent,
            child=self.child,
            gate="brief_review",
            message="accept brief",
        )

    def test_classify_gate_message_brief_accept(self) -> None:
        self.assertEqual(classify_gate_message("brief_review", "accept brief"), "accept_brief")
        self.assertEqual(classify_gate_message("brief_review", "accept"), "accept_brief")
        self.assertEqual(
            classify_gate_message("brief_review", "Please tighten SC-1 wording."),
            "brief_correction",
        )
        self.assertEqual(
            classify_gate_message("brief_review", "brief looks good — proceed to accept brief."),
            "brief_correction",
        )
        self.assertNotEqual(
            classify_gate_message("brief_review", "brief looks good — proceed to accept brief."),
            "accept_brief",
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

    def test_gate_command_sender_authorized(self) -> None:
        routed_body = "accept brief\n\n[program-orchestrator gate=brief_review]\n"
        self.assertFalse(
            gate_command_sender_authorized(self.root, self.child, self.child, routed_body),
        )
        self.assertFalse(
            gate_command_sender_authorized(self.root, self.child, self.sibling, routed_body),
        )
        self.assertFalse(
            gate_command_sender_authorized(self.root, self.child, self.parent, "accept brief"),
        )
        self.assertTrue(
            gate_command_sender_authorized(self.root, self.child, self.parent, routed_body),
        )
        self.assertFalse(
            gate_command_sender_authorized(self.root, self.child, "bad name", routed_body),
        )

    def test_parse_inbox_blocks(self) -> None:
        write_inbox(self.root, self.sibling, self.child, "accept brief")
        content = (self.root / "sessions" / "_inbox" / f"{self.child}.md").read_text()
        blocks = parse_inbox_blocks(content)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]["from"], self.sibling)
        self.assertEqual(blocks[0]["body"], "accept brief")

    def test_pull_inbox_gate_reports_pending(self) -> None:
        write_inbox(self.root, self.sibling, self.child, "accept brief")
        result = pull_inbox_gate(self.root, self.codename, apply=False)
        self.assertTrue(result["gate_phase"])
        self.assertEqual(result["poll_seconds"], INBOX_POLL_SECONDS)
        self.assertEqual(len(result["pending"]), 1)
        self.assertEqual(result["pending"][0]["action"], "accept_brief")

    def test_pull_inbox_gate_apply_accept_brief_from_parent(self) -> None:
        self._route_parent_accept_brief()
        result = pull_inbox_gate(self.root, self.codename, apply=True)
        self.assertEqual(result["applied"][0]["action"], "accept_brief")
        workflow = json.loads((self.session_dir / "workflow.json").read_text())
        self.assertTrue(workflow["gates"]["brief_accepted"])
        self.assertEqual(workflow["phase"], "plan_loop")
        brief = (self.session_dir / "artifacts" / "problem-brief.md").read_text()
        self.assertIn("**Status:** accepted", brief)

        second = pull_inbox_gate(self.root, self.codename, apply=True)
        self.assertEqual(second["pending"], [])

    def test_pull_inbox_gate_rejects_self_write(self) -> None:
        write_inbox(self.root, self.child, self.child, "accept brief")
        result = pull_inbox_gate(self.root, self.codename, apply=True)
        self.assertEqual(result["applied"], [])
        self.assertEqual(result["rejected"][0]["reason"], "unauthorized_gate_sender")
        workflow = json.loads((self.session_dir / "workflow.json").read_text())
        self.assertFalse(workflow["gates"]["brief_accepted"])
        self.assertEqual(workflow["phase"], "brief_review")
        marker = result["rejected"][0]["marker"]
        self.assertIn(marker, workflow["gates"]["inbox"]["processed_markers"])

        second = pull_inbox_gate(self.root, self.codename, apply=False)
        self.assertEqual(second["pending"], [])

    def test_pull_inbox_gate_rejects_unauthorized_sibling(self) -> None:
        write_inbox(self.root, self.sibling, self.child, "accept brief")
        result = pull_inbox_gate(self.root, self.codename, apply=True)
        self.assertEqual(result["applied"], [])
        self.assertEqual(result["rejected"][0]["reason"], "unauthorized_gate_sender")
        workflow = json.loads((self.session_dir / "workflow.json").read_text())
        self.assertFalse(workflow["gates"]["brief_accepted"])
        self.assertEqual(workflow["phase"], "brief_review")

        second = pull_inbox_gate(self.root, self.codename, apply=False)
        self.assertEqual(second["pending"], [])

    def test_pull_inbox_gate_rejects_forged_parent_without_route_marker(self) -> None:
        write_inbox(self.root, self.parent, self.child, "accept brief")
        result = pull_inbox_gate(self.root, self.codename, apply=True)
        self.assertEqual(result["applied"], [])
        self.assertEqual(result["rejected"][0]["reason"], "unauthorized_gate_sender")
        workflow = json.loads((self.session_dir / "workflow.json").read_text())
        self.assertFalse(workflow["gates"]["brief_accepted"])

    def test_pull_inbox_gate_rejects_invalid_from_codename(self) -> None:
        inbox_path = self.root / "sessions" / "_inbox" / f"{self.child}.md"
        inbox_path.parent.mkdir(parents=True, exist_ok=True)
        inbox_path.write_text(
            "\n\n---\n\n**From `bad name`** (2026-06-12)\n\naccept brief\n"
        )
        result = pull_inbox_gate(self.root, self.codename, apply=True)
        self.assertEqual(result["applied"], [])
        self.assertEqual(result["rejected"][0]["reason"], "unauthorized_gate_sender")
        workflow = json.loads((self.session_dir / "workflow.json").read_text())
        self.assertEqual(workflow["phase"], "brief_review")
        (self.session_dir / "artifacts" / "problem-brief.md").unlink()
        with self.assertRaisesRegex(ValueError, "missing brief artifact"):
            accept_brief(self.root, self.codename)
        workflow = json.loads((self.session_dir / "workflow.json").read_text())
        self.assertFalse(workflow["gates"]["brief_accepted"])
        self.assertEqual(workflow["phase"], "brief_review")

    def test_accept_brief_rejects_wrong_phase(self) -> None:
        workflow_path = self.session_dir / "workflow.json"
        workflow = json.loads(workflow_path.read_text())
        workflow["phase"] = "intake"
        workflow_path.write_text(json.dumps(workflow) + "\n")
        with self.assertRaises(ValueError):
            accept_brief(self.root, self.codename)

    def test_apply_brief_correction_rejects_invalid_sender(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid session codename"):
            apply_brief_correction(
                self.root,
                self.codename,
                "Tighten SC-1 wording.",
                from_session="bad name",
            )

    def test_apply_plan_feedback_rejects_invalid_sender(self) -> None:
        workflow_path = self.session_dir / "workflow.json"
        workflow = json.loads(workflow_path.read_text())
        workflow["phase"] = "plan_user_review"
        workflow_path.write_text(json.dumps(workflow) + "\n")
        with self.assertRaisesRegex(ValueError, "invalid session codename"):
            apply_plan_feedback(
                self.root,
                self.codename,
                "Split t2 into two tasks.",
                from_session="../evil",
            )

    def test_pull_inbox_gate_ignores_non_gate_phase(self) -> None:
        write_inbox(self.root, self.sibling, self.child, "accept brief")
        workflow_path = self.session_dir / "workflow.json"
        workflow = json.loads(workflow_path.read_text())
        workflow["phase"] = "implementation"
        workflow_path.write_text(json.dumps(workflow) + "\n")
        result = pull_inbox_gate(self.root, self.codename, apply=False)
        self.assertFalse(result["gate_phase"])
        self.assertEqual(result["pending"], [])

    def test_pull_inbox_gate_apply_brief_correction(self) -> None:
        write_inbox(self.root, self.sibling, self.child, "Tighten SC-1 wording for clarity.")
        result = pull_inbox_gate(self.root, self.codename, apply=True)
        self.assertEqual(result["applied"][0]["action"], "brief_correction")
        workflow = json.loads((self.session_dir / "workflow.json").read_text())
        self.assertEqual(workflow["phase"], "brief_review")
        brief = (self.session_dir / "artifacts" / "problem-brief.md").read_text()
        self.assertIn(f"Inbox correction from `{self.sibling}`", brief)
        self.assertIn("Tighten SC-1 wording", brief)

    def test_pull_inbox_gate_json_helper(self) -> None:
        payload = pull_inbox_gate_json(self.root, self.codename, apply=False)
        parsed = json.loads(payload)
        self.assertEqual(parsed["codename"], self.codename)

    def test_sync_session_auto_applies_accept_brief_from_parent(self) -> None:
        self._route_parent_accept_brief()
        sync_session_from_canonical(self.root, self.codename, refresh_context=False)
        workflow = json.loads((self.session_dir / "workflow.json").read_text())
        self.assertTrue(workflow["gates"]["brief_accepted"])
        self.assertEqual(workflow["phase"], "plan_loop")

    def test_cli_sync_failure_after_apply_exits_nonzero(self) -> None:
        write_inbox(self.root, "bravo", "alpha", "accept brief")
        scripts = self.root / "scripts"
        scripts.mkdir()
        sync = scripts / "sync-session.sh"
        sync.write_text("#!/usr/bin/env bash\nexit 1\n")
        sync.chmod(0o755)

        script = Path(__file__).resolve().parent / "workflow-pull-inbox-gate.py"
        env = {**os.environ, "WORKSPACE_ROOT": str(self.root)}
        result = subprocess.run(
            [sys.executable, str(script), "alpha", "--apply"],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        workflow = json.loads((self.session_dir / "workflow.json").read_text())
        self.assertTrue(workflow["gates"]["brief_accepted"])
        self.assertEqual(workflow["phase"], "plan_loop")


if __name__ == "__main__":
    unittest.main()
