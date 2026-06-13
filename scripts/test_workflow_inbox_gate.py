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
from program_route_feedback import route_correction, route_feedback  # noqa: E402
from program_state import default_program, save_program  # noqa: E402
from session_binding import sync_session_from_canonical, write_inbox  # noqa: E402
from workflow_inbox_gate import (  # noqa: E402
    INBOX_GATE_POLL_SECONDS,
    PROGRAM_CHILD_POLL_SKIP_REASON,
    accept_brief,
    apply_brief_correction,
    apply_plan_feedback,
    classify_gate_message,
    feedback_sender_authorized,
    gate_command_sender_authorized,
    inbox_gate_poll_enabled,
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
        self.standalone = "delta"
        self.standalone_dir = self._ensure_standalone_gate_session(self.standalone)

    def _ensure_standalone_gate_session(self, codename: str) -> Path:
        session_dir = self.root / "sessions" / codename
        session_dir.mkdir(parents=True, exist_ok=True)
        (session_dir / "session.json").write_text(
            json.dumps({"codename": codename, "tasks": []}) + "\n"
        )
        (session_dir / "TASKS.md").write_text("# Goal\n")
        (session_dir / "artifacts").mkdir(exist_ok=True)
        (session_dir / "artifacts" / "problem-brief.md").write_text(FIXTURE_BRIEF)
        (session_dir / "workflow.json").write_text(
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
                    "artifacts": {"brief": "artifacts/problem-brief.md"},
                }
            )
            + "\n"
        )
        return session_dir

    def test_inbox_gate_poll_disabled_for_program_child(self) -> None:
        self.assertFalse(inbox_gate_poll_enabled(self.root, self.child))
        result = pull_inbox_gate(self.root, self.child, apply=True)
        self.assertFalse(result["poll_enabled"])
        self.assertEqual(result["poll_skipped_reason"], PROGRAM_CHILD_POLL_SKIP_REASON)
        self.assertEqual(result["pending"], [])
        self.assertEqual(result["applied"], [])
        self.assertEqual(result["rejected"], [])

    def test_inbox_gate_poll_enabled_for_standalone(self) -> None:
        self.assertTrue(inbox_gate_poll_enabled(self.root, self.standalone))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _route_parent(self, gate: str, message: str, *, to: str | None = None) -> None:
        target = to or self.standalone
        payload = (
            f"{message}\n\n"
            f"[program-orchestrator gate={gate}]\n"
            f"Parent `{self.parent}` routed feedback."
        )
        write_inbox(
            self.root,
            self.parent,
            target,
            payload,
            caller_codename=self.parent,
        )

    def _route_parent_accept_brief(self, *, to: str | None = None) -> None:
        self._route_parent("brief_review", "accept brief", to=to)

    def _write_workflow(self, *, codename: str | None = None, **overrides: object) -> None:
        name = codename or self.standalone
        workflow_path = self.root / "sessions" / name / "workflow.json"
        workflow = json.loads(workflow_path.read_text())
        workflow.update(overrides)
        workflow_path.write_text(json.dumps(workflow, indent=2) + "\n")

    def _write_minimal_action_plan(self, *, codename: str | None = None) -> None:
        name = codename or self.standalone
        session_dir = self.root / "sessions" / name
        (self.root / "repos.yaml").write_text(
            "repos:\n  template:\n    path: repos/template\n"
            "    clone: git@github.com:example/template.git\n"
            "    default_branch: main\n"
        )
        (session_dir / "artifacts" / "action-plan.md").write_text(
            """# Action plan — test

**Status:** draft
**Based on:** problem-brief.md @ accepted
**Version:** 1

## Approach
Test plan for inbox gate integration.

## Traceability
| Brief | Plan tasks |
| SC-1 | t1 |

## Tasks

| ID | Repo | Summary | Acceptance | Depends |
|----|------|---------|------------|---------|
| t1 | template | Do thing | Observable done condition | — |

## Test plan
none

## Risks
| Risk | Mitigation |
| — | — |
"""
        )
        (session_dir / "TASKS.md").write_text(
            "# Goal\n\nChild goal\n\n## Tasks\n\n| ID | Status | Notes |\n| --- | --- | --- |\n"
        )

    def _assert_rejected_stays_pending(
        self, result: dict, workflow: dict, *, codename: str | None = None
    ) -> None:
        target = codename or self.standalone
        marker = result["rejected"][0]["marker"]
        self.assertNotIn(marker, workflow["gates"]["inbox"]["processed_markers"])
        second = pull_inbox_gate(self.root, target, apply=False)
        self.assertEqual(len(second["pending"]), 1)
        self.assertEqual(second["pending"][0]["marker"], marker)

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

    def test_feedback_sender_authorized(self) -> None:
        self.assertFalse(
            feedback_sender_authorized(self.root, self.child, self.child),
        )
        self.assertFalse(
            feedback_sender_authorized(self.root, self.child, self.sibling),
        )
        self.assertFalse(
            feedback_sender_authorized(self.root, self.child, self.parent),
        )

    def test_feedback_sender_authorized_standalone_session(self) -> None:
        standalone = "echo"
        self._ensure_standalone_gate_session(standalone)
        self.assertFalse(
            feedback_sender_authorized(self.root, standalone, self.parent),
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
        self.assertFalse(
            gate_command_sender_authorized(
                self.root,
                self.child,
                self.parent,
                routed_body,
                marker="missing:marker",
            ),
        )
        self.assertFalse(
            gate_command_sender_authorized(
                self.root,
                self.child,
                self.parent,
                routed_body,
                marker="any:marker",
            ),
        )

    def test_write_inbox_rejects_caller_mismatch(self) -> None:
        with self.assertRaisesRegex(ValueError, "does not match caller"):
            write_inbox(
                self.root,
                self.parent,
                self.child,
                "accept brief",
                caller_codename=self.sibling,
            )

    def test_write_inbox_allows_non_gate_sibling_message(self) -> None:
        write_inbox(
            self.root,
            self.sibling,
            self.child,
            "Status update for parent review.",
            caller_codename=self.sibling,
        )
        content = (self.root / "sessions" / "_inbox" / f"{self.child}.md").read_text()
        self.assertIn("Status update", content)

    def test_pull_inbox_gate_rejects_sibling_impersonating_parent_with_marker(self) -> None:
        body = "accept brief\n\n[program-orchestrator gate=brief_review]"
        with self.assertRaisesRegex(ValueError, "does not match caller"):
            write_inbox(
                self.root,
                self.parent,
                self.child,
                body,
                caller_codename=self.sibling,
            )
        result = pull_inbox_gate(self.root, self.standalone, apply=True)
        self.assertEqual(result["applied"], [])
        workflow = json.loads((self.session_dir / "workflow.json").read_text())
        self.assertFalse(workflow["gates"]["brief_accepted"])

    def test_route_feedback_rejects_non_parent_caller(self) -> None:
        with mock.patch(
            "program_route_feedback.resolve_codename",
            return_value=(self.sibling, "binding"),
        ):
            with mock.patch("program_route_feedback.load_program") as load_program:
                with self.assertRaisesRegex(ValueError, f"not {self.sibling!r}"):
                    route_feedback(
                        self.root,
                        parent=self.parent,
                        child=self.child,
                        gate="brief_review",
                        message="accept brief",
                    )
                load_program.assert_not_called()

    def test_route_feedback_rejects_unbound_caller(self) -> None:
        with mock.patch(
            "program_route_feedback.resolve_codename",
            return_value=(None, ""),
        ):
            with mock.patch("program_route_feedback.load_program") as load_program:
                with self.assertRaisesRegex(ValueError, "not unbound caller"):
                    route_feedback(
                        self.root,
                        parent=self.parent,
                        child=self.child,
                        gate="brief_review",
                        message="accept brief",
                    )
                load_program.assert_not_called()

    def test_route_correction_rejects_unbound_caller(self) -> None:
        with mock.patch(
            "program_route_feedback.resolve_codename",
            return_value=(None, ""),
        ):
            with mock.patch("program_route_feedback.load_program") as load_program:
                with self.assertRaisesRegex(ValueError, "not unbound caller"):
                    route_correction(
                        self.root,
                        parent=self.parent,
                        child=self.child,
                        message="fix the brief scope",
                    )
                load_program.assert_not_called()

    def test_write_inbox_program_route_is_removed(self) -> None:
        from session_binding import write_inbox_program_route

        payload = (
            "accept brief\n\n"
            "[program-orchestrator gate=brief_review]\n"
            f"Parent `{self.parent}` routed feedback."
        )
        with self.assertRaisesRegex(ValueError, "write_inbox_program_route is removed"):
            write_inbox_program_route(
                self.root,
                self.parent,
                self.child,
                payload,
            )

    def test_parse_inbox_blocks(self) -> None:
        write_inbox(
            self.root,
            self.sibling,
            self.child,
            "accept brief",
            caller_codename=self.sibling,
        )
        content = (self.root / "sessions" / "_inbox" / f"{self.child}.md").read_text()
        blocks = parse_inbox_blocks(content)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]["from"], self.sibling)
        self.assertEqual(blocks[0]["body"], "accept brief")

    def test_pull_inbox_gate_reports_pending(self) -> None:
        write_inbox(
            self.root,
            self.sibling,
            self.standalone,
            "accept brief",
            caller_codename=self.sibling,
        )
        result = pull_inbox_gate(self.root, self.standalone, apply=False)
        self.assertTrue(result["gate_phase"])
        self.assertTrue(result["poll_enabled"])
        self.assertEqual(result["poll_seconds"], INBOX_GATE_POLL_SECONDS)
        self.assertEqual(len(result["pending"]), 1)
        self.assertEqual(result["pending"][0]["action"], "accept_brief")

    def test_pull_inbox_gate_apply_accept_brief_from_parent(self) -> None:
        self._route_parent_accept_brief()
        result = pull_inbox_gate(self.root, self.standalone, apply=True)
        self.assertEqual(result["applied"], [])
        self.assertEqual(result["rejected"][0]["action"], "accept_brief")
        self.assertEqual(result["rejected"][0]["reason"], "unauthorized_gate_sender")
        workflow = json.loads((self.standalone_dir / "workflow.json").read_text())
        self.assertFalse(workflow["gates"]["brief_accepted"])
        self.assertEqual(workflow["phase"], "brief_review")
        marker = result["rejected"][0]["marker"]
        self.assertNotIn(marker, workflow["gates"]["inbox"]["processed_markers"])

        second = pull_inbox_gate(self.root, self.standalone, apply=False)
        self.assertEqual(len(second["pending"]), 1)
        self.assertEqual(second["pending"][0]["marker"], marker)

    def test_pull_inbox_gate_apply_accept_plan_from_parent(self) -> None:
        self._write_workflow(
            phase="plan_user_review",
            gates={
                "brief_accepted": True,
                "plan_user_accepted": False,
                "inbox": {"processed_markers": [], "last_pull_at": None},
            },
        )
        self._write_minimal_action_plan()
        self._route_parent("plan_user_review", "accept plan")
        result = pull_inbox_gate(self.root, self.standalone, apply=True)
        self.assertEqual(result["applied"], [])
        self.assertEqual(result["rejected"][0]["action"], "accept_plan")
        workflow = json.loads((self.standalone_dir / "workflow.json").read_text())
        self.assertFalse(workflow["gates"]["plan_user_accepted"])
        self.assertEqual(workflow["phase"], "plan_user_review")

    def test_pull_inbox_gate_apply_reopen_brief_from_parent(self) -> None:
        self._write_workflow(
            phase="brief_review",
            gates={
                "brief_accepted": True,
                "plan_user_accepted": False,
                "inbox": {"processed_markers": [], "last_pull_at": None},
            },
        )
        self._route_parent("brief_review", "reopen brief")
        result = pull_inbox_gate(self.root, self.standalone, apply=True)
        self.assertEqual(result["applied"], [])
        self.assertEqual(result["rejected"][0]["action"], "reopen_brief")
        workflow = json.loads((self.standalone_dir / "workflow.json").read_text())
        self.assertEqual(workflow["phase"], "brief_review")

    def test_pull_inbox_gate_apply_reopen_plan_from_parent(self) -> None:
        self._write_workflow(
            phase="plan_user_review",
            gates={
                "brief_accepted": True,
                "plan_user_accepted": False,
                "inbox": {"processed_markers": [], "last_pull_at": None},
            },
        )
        self._write_minimal_action_plan()
        self._route_parent("plan_user_review", "reopen plan")
        result = pull_inbox_gate(self.root, self.standalone, apply=True)
        self.assertEqual(result["applied"], [])
        self.assertEqual(result["rejected"][0]["action"], "reopen_plan")
        workflow = json.loads((self.standalone_dir / "workflow.json").read_text())
        self.assertEqual(workflow["phase"], "plan_user_review")

    def test_pull_inbox_gate_rejects_self_write(self) -> None:
        write_inbox(
            self.root,
            self.standalone,
            self.standalone,
            "accept brief",
            caller_codename=self.standalone,
        )
        result = pull_inbox_gate(self.root, self.standalone, apply=True)
        self.assertEqual(result["applied"], [])
        self.assertEqual(result["rejected"][0]["reason"], "unauthorized_gate_sender")
        workflow = json.loads((self.standalone_dir / "workflow.json").read_text())
        self.assertFalse(workflow["gates"]["brief_accepted"])
        self.assertEqual(workflow["phase"], "brief_review")
        marker = result["rejected"][0]["marker"]
        self.assertNotIn(marker, workflow["gates"]["inbox"]["processed_markers"])

        second = pull_inbox_gate(self.root, self.standalone, apply=False)
        self.assertEqual(len(second["pending"]), 1)
        self.assertEqual(second["pending"][0]["marker"], marker)

    def test_pull_inbox_gate_rejects_unauthorized_sibling(self) -> None:
        write_inbox(
            self.root,
            self.sibling,
            self.standalone,
            "accept brief",
            caller_codename=self.sibling,
        )
        result = pull_inbox_gate(self.root, self.standalone, apply=True)
        self.assertEqual(result["applied"], [])
        self.assertEqual(result["rejected"][0]["reason"], "unauthorized_gate_sender")
        workflow = json.loads((self.standalone_dir / "workflow.json").read_text())
        self.assertFalse(workflow["gates"]["brief_accepted"])
        self.assertEqual(workflow["phase"], "brief_review")
        marker = result["rejected"][0]["marker"]
        self.assertNotIn(marker, workflow["gates"]["inbox"]["processed_markers"])

        second = pull_inbox_gate(self.root, self.standalone, apply=False)
        self.assertEqual(len(second["pending"]), 1)
        self.assertEqual(second["pending"][0]["marker"], marker)

    def test_pull_inbox_gate_rejects_forged_parent_without_route_marker(self) -> None:
        write_inbox(
            self.root,
            self.parent,
            self.standalone,
            "accept brief",
            caller_codename=self.parent,
        )
        result = pull_inbox_gate(self.root, self.standalone, apply=True)
        self.assertEqual(result["applied"], [])
        self.assertEqual(result["rejected"][0]["reason"], "unauthorized_gate_sender")
        workflow = json.loads((self.standalone_dir / "workflow.json").read_text())
        self.assertFalse(workflow["gates"]["brief_accepted"])

    def test_pull_inbox_gate_rejects_parent_ordinary_write_with_gate_marker(self) -> None:
        """Parent gate-marker body via ordinary inbox write must not auto-apply."""
        body = "accept brief\n\n[program-orchestrator gate=brief_review]"
        write_inbox(
            self.root,
            self.parent,
            self.standalone,
            body,
            caller_codename=self.parent,
        )
        result = pull_inbox_gate(self.root, self.standalone, apply=True)
        self.assertEqual(result["applied"], [])
        self.assertEqual(result["rejected"][0]["reason"], "unauthorized_gate_sender")
        workflow = json.loads((self.standalone_dir / "workflow.json").read_text())
        self.assertFalse(workflow["gates"]["brief_accepted"])
        self.assertEqual(workflow["phase"], "brief_review")
        marker = result["rejected"][0]["marker"]
        self.assertNotIn(marker, workflow["gates"]["inbox"]["processed_markers"])
        second = pull_inbox_gate(self.root, self.standalone, apply=False)
        self.assertEqual(len(second["pending"]), 1)
        self.assertEqual(second["pending"][0]["marker"], marker)

    def test_pull_inbox_gate_rejects_invalid_from_codename(self) -> None:
        inbox_path = self.root / "sessions" / "_inbox" / f"{self.standalone}.md"
        inbox_path.parent.mkdir(parents=True, exist_ok=True)
        inbox_path.write_text(
            "\n\n---\n\n**From `bad name`** (2026-06-12)\n\naccept brief\n"
        )
        result = pull_inbox_gate(self.root, self.standalone, apply=True)
        self.assertEqual(result["applied"], [])
        self.assertEqual(result["rejected"][0]["reason"], "unauthorized_gate_sender")
        workflow = json.loads((self.standalone_dir / "workflow.json").read_text())
        self.assertEqual(workflow["phase"], "brief_review")
        (self.standalone_dir / "artifacts" / "problem-brief.md").unlink()
        with self.assertRaisesRegex(ValueError, "missing brief artifact"):
            accept_brief(self.root, self.standalone)
        workflow = json.loads((self.standalone_dir / "workflow.json").read_text())
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
        write_inbox(
            self.root,
            self.sibling,
            self.standalone,
            "accept brief",
            caller_codename=self.sibling,
        )
        workflow_path = self.standalone_dir / "workflow.json"
        workflow = json.loads(workflow_path.read_text())
        workflow["phase"] = "implementation"
        workflow_path.write_text(json.dumps(workflow) + "\n")
        result = pull_inbox_gate(self.root, self.standalone, apply=False)
        self.assertFalse(result["gate_phase"])
        self.assertEqual(result["pending"], [])

    def test_pull_inbox_gate_apply_brief_correction(self) -> None:
        write_inbox(
            self.root,
            self.sibling,
            self.standalone,
            "Tighten SC-1 wording for clarity.",
            caller_codename=self.sibling,
        )
        result = pull_inbox_gate(self.root, self.standalone, apply=True)
        self.assertEqual(result["applied"], [])
        self.assertEqual(result["rejected"][0]["action"], "brief_correction")
        self.assertEqual(result["rejected"][0]["reason"], "unauthorized_feedback_sender")
        workflow = json.loads((self.standalone_dir / "workflow.json").read_text())
        self.assertEqual(workflow["phase"], "brief_review")
        brief = (self.standalone_dir / "artifacts" / "problem-brief.md").read_text()
        self.assertNotIn("Tighten SC-1 wording", brief)
        self._assert_rejected_stays_pending(result, workflow)

    def test_pull_inbox_gate_apply_brief_correction_from_parent(self) -> None:
        write_inbox(
            self.root,
            self.parent,
            self.standalone,
            "Tighten SC-1 wording for clarity.",
            caller_codename=self.parent,
        )
        result = pull_inbox_gate(self.root, self.standalone, apply=True)
        self.assertEqual(result["applied"], [])
        self.assertEqual(result["rejected"][0]["action"], "brief_correction")
        workflow = json.loads((self.standalone_dir / "workflow.json").read_text())
        self.assertEqual(workflow["phase"], "brief_review")
        brief = (self.standalone_dir / "artifacts" / "problem-brief.md").read_text()
        self.assertNotIn("Tighten SC-1 wording", brief)
        self._assert_rejected_stays_pending(result, workflow)

    def test_pull_inbox_gate_rejects_sibling_plan_feedback(self) -> None:
        self._write_workflow(phase="plan_user_review")
        self._write_minimal_action_plan()
        write_inbox(
            self.root,
            self.sibling,
            self.standalone,
            "Split t2 into two tasks.",
            caller_codename=self.sibling,
        )
        result = pull_inbox_gate(self.root, self.standalone, apply=True)
        self.assertEqual(result["applied"], [])
        self.assertEqual(result["rejected"][0]["action"], "plan_feedback")
        self.assertEqual(result["rejected"][0]["reason"], "unauthorized_feedback_sender")
        workflow = json.loads((self.standalone_dir / "workflow.json").read_text())
        self.assertEqual(workflow["phase"], "plan_user_review")
        self._assert_rejected_stays_pending(result, workflow)

    def test_pull_inbox_gate_apply_plan_feedback_from_parent(self) -> None:
        self._write_workflow(phase="plan_user_review")
        self._write_minimal_action_plan()
        write_inbox(
            self.root,
            self.parent,
            self.standalone,
            "Split t2 into two tasks.",
            caller_codename=self.parent,
        )
        result = pull_inbox_gate(self.root, self.standalone, apply=True)
        self.assertEqual(result["applied"], [])
        self.assertEqual(result["rejected"][0]["action"], "plan_feedback")
        workflow = json.loads((self.standalone_dir / "workflow.json").read_text())
        self.assertEqual(workflow["phase"], "plan_user_review")
        feedback_path = self.standalone_dir / "artifacts" / "plan-feedback.md"
        self.assertFalse(feedback_path.exists())
        self._assert_rejected_stays_pending(result, workflow)

    def test_pull_inbox_gate_rejects_feedback_when_no_program_parent(self) -> None:
        standalone = "lima"
        standalone_dir = self._ensure_standalone_gate_session(standalone)
        write_inbox(
            self.root,
            self.parent,
            standalone,
            "Fix wording.",
            caller_codename=self.parent,
        )
        result = pull_inbox_gate(self.root, standalone, apply=True)
        self.assertEqual(result["applied"], [])
        self.assertEqual(result["rejected"][0]["reason"], "unauthorized_feedback_sender")
        workflow = json.loads((standalone_dir / "workflow.json").read_text())
        self._assert_rejected_stays_pending(result, workflow, codename=standalone)
        brief = (standalone_dir / "artifacts" / "problem-brief.md").read_text()
        self.assertNotIn("Fix wording", brief)

    def test_pull_inbox_gate_json_helper(self) -> None:
        payload = pull_inbox_gate_json(self.root, self.standalone, apply=False)
        parsed = json.loads(payload)
        self.assertEqual(parsed["codename"], self.standalone)

    def test_sync_skips_inbox_poll_for_program_child(self) -> None:
        self._route_parent_accept_brief(to=self.child)
        before = json.loads((self.session_dir / "workflow.json").read_text())
        before_pull = before["gates"]["inbox"]["last_pull_at"]
        sync_session_from_canonical(self.root, self.child, refresh_context=False)
        workflow = json.loads((self.session_dir / "workflow.json").read_text())
        self.assertFalse(workflow["gates"]["brief_accepted"])
        self.assertEqual(workflow["phase"], "brief_review")
        self.assertEqual(workflow["gates"]["inbox"]["last_pull_at"], before_pull)

    def test_cli_pull_skips_for_program_child(self) -> None:
        script = Path(__file__).resolve().parent / "workflow-pull-inbox-gate.py"
        env = {**os.environ, "WORKSPACE_ROOT": str(self.root)}
        result = subprocess.run(
            [sys.executable, str(script), self.child, "--apply"],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["poll_enabled"])
        self.assertEqual(payload["poll_skipped_reason"], PROGRAM_CHILD_POLL_SKIP_REASON)


if __name__ == "__main__":
    unittest.main()
