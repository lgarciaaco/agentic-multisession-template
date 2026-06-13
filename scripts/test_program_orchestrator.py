#!/usr/bin/env python3
"""Tests for sessions program orchestrator scripts."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from program_monitor import (  # noqa: E402
    child_gate_review,
    cleanup_completed_children,
    monitor_program,
    program_parent_next_action,
    render_program_status_markdown,
    sibling_program_context,
)
from program_route_feedback import route_feedback  # noqa: E402
from workflow_inbox_gate import classify_gate_message, parse_inbox_blocks, pull_inbox_gate  # noqa: E402
from program_state import default_program, save_program  # noqa: E402
from session_binding import write_inbox  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


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
        program["proposed_children"] = [
            {
                "id": "c1",
                "suggested_codename": self.child,
                "title": "Child scope title",
                "goal": "Deliver child feature X",
                "repo": "template",
                "depends_on": [],
            }
        ]
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
            json.dumps(
                {"codename": self.child, "title": "Child session title", "tasks": []},
                indent=2,
            )
            + "\n"
        )
        (child_dir / "TASKS.md").write_text(
            "# Tasks\n\n## Goal\n\nChild session goal line\n"
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _route_feedback(self, **kwargs: object) -> str:
        parent = kwargs.pop("parent", self.parent)
        child = kwargs.pop("child", self.child)
        with mock.patch(
            "program_route_feedback.resolve_codename",
            return_value=(parent, "binding"),
        ):
            with mock.patch(
                "session_binding.resolve_inbox_caller",
                return_value=parent,
            ):
                return route_feedback(
                    self.root,
                    parent=parent,
                    child=child,
                    **kwargs,
                )

    def test_monitor_reports_child_gate(self) -> None:
        report = monitor_program(self.root, self.parent)
        self.assertEqual(report["parent"], self.parent)
        self.assertEqual(len(report["children"]), 1)
        child = report["children"][0]
        self.assertEqual(child["codename"], self.child)
        self.assertEqual(child["pending_gate"], "brief_review")

    def test_monitor_includes_gate_review_and_parent_next_action(self) -> None:
        child_dir = self.root / "sessions" / self.child
        (child_dir / "artifacts" / "problem-brief.md").write_text("# Brief\n")
        report = monitor_program(self.root, self.parent)
        child = report["children"][0]
        review = child["gate_review"]
        self.assertEqual(review["gate"], "brief_review")
        self.assertTrue(review["artifact_present"])
        self.assertIn("problem-brief.md", review["artifact_path"])
        self.assertEqual(review["decomposition_scope"]["goal"], "Deliver child feature X")
        self.assertEqual(review["child_scope"]["title"], "Child session title")
        self.assertIn("Child session goal", review["child_scope"]["goal"] or "")
        self.assertIn("Review child", report["parent_next_action"])
        self.assertIn("sessions/november/", report["parent_next_action"])
        self.assertIn("cross-child", report["parent_next_action"].lower())
        self.assertNotIn("when you've reviewed", report["parent_next_action"].lower())

    def test_child_gate_review_rejects_invalid_codename(self) -> None:
        with self.assertRaises(ValueError):
            child_gate_review(self.root, "../evil", "brief_review")

    def test_program_parent_next_action_multi_child(self) -> None:
        report = {
            "decomposition_approved": True,
            "children": [
                {"codename": "november", "pending_gate": "brief_review"},
                {"codename": "oscar", "pending_gate": "plan_user_review"},
            ],
        }
        action = program_parent_next_action(report)
        self.assertIn("Review gate artifacts for", action)
        self.assertIn("`november`", action)
        self.assertIn("`oscar`", action)

    def test_program_parent_next_action_decomposition_not_approved(self) -> None:
        report = {"decomposition_approved": False, "children": []}
        action = program_parent_next_action(report)
        self.assertIn("approve decomposition", action)

    def test_program_monitor_format_text(self) -> None:
        import importlib.util

        child_dir = self.root / "sessions" / self.child
        (child_dir / "artifacts" / "problem-brief.md").write_text("# Brief\n")
        report = monitor_program(self.root, self.parent)
        cli_path = ROOT / "scripts" / "program-monitor.py"
        spec = importlib.util.spec_from_file_location("program_monitor_cli", cli_path)
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        text = mod.format_text(report)
        self.assertIn("Parent next:", text)
        self.assertIn("| Child | Phase | Gate | Next |", text)
        self.assertIn(f"| `{self.child}` | brief_review | brief |", text)
        self.assertNotIn("review: sessions/", text)
        self.assertNotIn("siblings:", text)

    def test_program_status_report_reviews_json_smoke(self) -> None:
        child_dir = self.root / "sessions" / self.child
        (child_dir / "artifacts" / "problem-brief.md").write_text("# Brief\n")
        reviews_path = self.root / "child-reviews.json"
        reviews_path.write_text(
            json.dumps(
                {
                    self.child: {
                        "next": "Accept brief or send corrections",
                        "parent_assessment": "Aligned with decomposition scope.",
                        "cross_child_check": "No sibling overlap.",
                        "child_agent_action": "Wait for accept brief.",
                    }
                }
            )
            + "\n",
            encoding="utf-8",
        )
        script = ROOT / "scripts" / "program-status-report.sh"
        env = {**os.environ, "WORKSPACE_ROOT": str(self.root)}
        result = subprocess.run(
            [str(script), self.parent, "--reviews-json", str(reviews_path)],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        status_path = self.root / "sessions" / self.parent / "artifacts" / "program-status.md"
        self.assertTrue(status_path.is_file(), result.stdout)
        body = status_path.read_text(encoding="utf-8")
        self.assertIn("Aligned with decomposition scope.", body)
        self.assertIn("**Cross-child check**", body)
        self.assertIn("Accept brief or send corrections", body)

    def test_program_status_report_gate_review_section(self) -> None:
        child_dir = self.root / "sessions" / self.child
        (child_dir / "artifacts" / "problem-brief.md").write_text("# Brief\n")
        lib_path = ROOT / "scripts" / "lib"
        py = f"""
import sys
from pathlib import Path
import os
root = Path({str(self.root)!r})
sys.path.insert(0, {str(lib_path)!r})
os.environ["WORKSPACE_ROOT"] = str(root)
from hub_paths import resolve_session_artifact
from program_monitor import monitor_program
from program_state import load_program
from session_binding import validate_codename

codename = validate_codename({self.parent!r})
session_dir = root / "sessions" / codename
report = monitor_program(root, codename)
program = load_program(session_dir)
status_path = resolve_session_artifact(session_dir, program.get("status_path") or "artifacts/program-status.md")
lines = [
    "## Gate review (parent)",
    report.get("parent_next_action") or "",
]
pending = [c for c in report.get("children") or [] if c.get("pending_gate")]
for child in pending:
    review = child.get("gate_review") or {{}}
    lines.append(review.get("artifact_path") or "")
    decomp = review.get("decomposition_scope") or {{}}
    lines.append(decomp.get("goal") or "")
status_path.parent.mkdir(parents=True, exist_ok=True)
status_path.write_text("\\n".join(lines) + "\\n")
print(status_path)
"""
        result = subprocess.run(
            [sys.executable, "-c", py],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        status_path = self.root / "sessions" / self.parent / "artifacts" / "program-status.md"
        body = status_path.read_text()
        self.assertIn("## Gate review (parent)", body)
        self.assertIn("problem-brief.md", body)
        self.assertIn("Deliver child feature X", body)
        self.assertIn("Review child", body)

    def test_program_parent_next_action_no_pending_gate(self) -> None:
        report = {
            "decomposition_approved": True,
            "children": [{"codename": self.child, "pending_gate": None}],
        }
        action = program_parent_next_action(report)
        self.assertIn("no gate review pending", action)

    def test_child_gate_review_plan_user_review(self) -> None:
        child_dir = self.root / "sessions" / self.child
        (child_dir / "artifacts" / "action-plan.md").write_text("# Plan\n")
        program = default_program(self.parent)
        program["proposed_children"] = [
            {
                "id": "c1",
                "suggested_codename": self.child,
                "title": "Plan child",
                "goal": "Plan goal",
                "repo": "template",
                "depends_on": [],
            }
        ]
        review = child_gate_review(
            self.root, self.child, "plan_user_review", program=program
        )
        self.assertEqual(review["gate"], "plan_user_review")
        self.assertIn("action-plan.md", review["artifact_path"])
        self.assertTrue(review["artifact_present"])
        self.assertEqual(review["decomposition_scope"]["title"], "Plan child")
        self.assertEqual(review["child_scope"]["title"], "Child session title")

    def test_route_feedback_writes_inbox(self) -> None:
        self._route_feedback(
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
        self._route_feedback(
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

    def _write_child_plan_gate_workflow(self) -> None:
        child_dir = self.root / "sessions" / self.child
        (self.root / "repos.yaml").write_text(
            "repos:\n  template:\n    path: repos/template\n"
            "    clone: git@github.com:example/template.git\n"
            "    default_branch: main\n"
        )
        workflow = {
            "version": 2,
            "phase": "plan_user_review",
            "gates": {
                "brief_accepted": True,
                "plan_user_accepted": False,
                "inbox": {"processed_markers": [], "last_pull_at": None},
            },
            "loops": {},
            "artifacts": {
                "brief": "artifacts/problem-brief.md",
                "plan": "artifacts/action-plan.md",
                "plan_feedback": "artifacts/plan-feedback.md",
            },
        }
        (child_dir / "workflow.json").write_text(json.dumps(workflow, indent=2) + "\n")
        (child_dir / "artifacts" / "action-plan.md").write_text(
            """# Action plan — child

**Status:** draft
**Based on:** problem-brief.md @ accepted
**Version:** 1

## Approach
Child plan.

## Traceability
| Brief | Plan tasks |
| SC-1 | t1 |

## Tasks

| ID | Repo | Summary | Acceptance | Depends |
|----|------|---------|------------|---------|
| t1 | template | Deliver | Done when shipped | — |

## Test plan
none

## Risks
| Risk | Mitigation |
| — | — |
"""
        )
        (child_dir / "TASKS.md").write_text(
            "# Tasks\n\n## Goal\n\nChild session goal line\n\n## Tasks\n\n| ID | Status | Notes |\n| --- | --- | --- |\n"
        )

    def test_route_feedback_accept_plan_applies_via_inbox_pull(self) -> None:
        self._write_child_plan_gate_workflow()
        self._route_feedback(
            gate="plan_user_review",
            message="accept plan",
        )
        result = pull_inbox_gate(self.root, self.child, apply=True)
        self.assertEqual(result["applied"][0]["action"], "accept_plan")
        workflow = json.loads(
            (self.root / "sessions" / self.child / "workflow.json").read_text()
        )
        self.assertEqual(workflow["phase"], "implementation")

    def test_route_feedback_reopen_brief_applies_via_inbox_pull(self) -> None:
        self._route_feedback(
            gate="brief_review",
            message="reopen brief",
        )
        result = pull_inbox_gate(self.root, self.child, apply=True)
        self.assertEqual(result["applied"][0]["action"], "reopen_brief")
        workflow = json.loads(
            (self.root / "sessions" / self.child / "workflow.json").read_text()
        )
        self.assertEqual(workflow["phase"], "intake")

    def test_route_feedback_reopen_plan_applies_via_inbox_pull(self) -> None:
        self._write_child_plan_gate_workflow()
        self._route_feedback(
            gate="plan_user_review",
            message="reopen plan",
        )
        result = pull_inbox_gate(self.root, self.child, apply=True)
        self.assertEqual(result["applied"][0]["action"], "reopen_plan")
        workflow = json.loads(
            (self.root / "sessions" / self.child / "workflow.json").read_text()
        )
        self.assertEqual(workflow["phase"], "plan_loop")

    def _write_completed_child_workflow(self) -> None:
        child_dir = self.root / "sessions" / self.child
        workflow = {
            "version": 2,
            "phase": "completed",
            "gates": {"brief_accepted": True, "plan_user_accepted": True},
            "loops": {},
            "artifacts": {},
        }
        (child_dir / "workflow.json").write_text(json.dumps(workflow, indent=2) + "\n")

    @patch("program_monitor.close_child_window", return_value=True)
    @patch("program_monitor.resolve_child_window", return_value="%9")
    @patch("program_monitor.is_safe_child_close_target", return_value=True)
    @patch("program_monitor.in_tmux", return_value=True)
    def test_cleanup_completed_children_updates_status_and_closes_tab(
        self,
        _in_tmux,
        _safe,
        resolve,
        close,
    ) -> None:
        self._write_completed_child_workflow()
        parent_dir = self.root / "sessions" / self.parent
        program = json.loads((parent_dir / "program.json").read_text())
        cleanup_completed_children(self.root, self.parent, program)
        program = json.loads((parent_dir / "program.json").read_text())
        self.assertEqual(program["active_children"][0]["status"], "completed")
        resolve.assert_called_once()
        close.assert_called_once_with("%9")

    @patch("program_monitor.close_child_window", return_value=False)
    @patch("program_monitor.resolve_child_window", return_value="%9")
    @patch("program_monitor.is_safe_child_close_target", return_value=True)
    @patch("program_monitor.in_tmux", return_value=True)
    def test_cleanup_persists_status_when_kill_fails(
        self,
        _in_tmux,
        _safe,
        _resolve,
        _close,
    ) -> None:
        self._write_completed_child_workflow()
        parent_dir = self.root / "sessions" / self.parent
        program = json.loads((parent_dir / "program.json").read_text())
        cleanup_completed_children(self.root, self.parent, program)
        program = json.loads((parent_dir / "program.json").read_text())
        self.assertEqual(program["active_children"][0]["status"], "completed")

    @patch("program_monitor.close_child_window")
    @patch("program_monitor.resolve_child_window", return_value=None)
    @patch("program_monitor.in_tmux", return_value=True)
    def test_cleanup_idempotent_when_window_absent(
        self,
        _in_tmux,
        _resolve,
        close,
    ) -> None:
        self._write_completed_child_workflow()
        parent_dir = self.root / "sessions" / self.parent
        program = json.loads((parent_dir / "program.json").read_text())
        cleanup_completed_children(self.root, self.parent, program)
        cleanup_completed_children(self.root, self.parent, program)
        program = json.loads((parent_dir / "program.json").read_text())
        self.assertEqual(program["active_children"][0]["status"], "completed")
        close.assert_not_called()

    @patch("program_monitor.close_child_window")
    @patch("program_monitor.resolve_child_window", return_value="%9")
    @patch("program_monitor.is_safe_child_close_target", return_value=False)
    @patch("program_monitor.in_tmux", return_value=True)
    def test_cleanup_skips_parent_window_target(
        self,
        _in_tmux,
        _safe,
        _resolve,
        close,
    ) -> None:
        self._write_completed_child_workflow()
        parent_dir = self.root / "sessions" / self.parent
        program = json.loads((parent_dir / "program.json").read_text())
        cleanup_completed_children(self.root, self.parent, program)
        close.assert_not_called()
        program = json.loads((parent_dir / "program.json").read_text())
        self.assertEqual(program["active_children"][0]["status"], "completed")

    @patch("program_monitor.close_child_window", return_value=True)
    @patch("program_monitor.resolve_child_window", return_value="%9")
    @patch("program_monitor.is_safe_child_close_target", return_value=True)
    @patch("program_monitor.in_tmux", return_value=True)
    def test_cleanup_passes_window_label_for_label_only_resolution(
        self,
        _in_tmux,
        _safe,
        resolve,
        _close,
    ) -> None:
        self._write_completed_child_workflow()
        parent_dir = self.root / "sessions" / self.parent
        program = json.loads((parent_dir / "program.json").read_text())
        program["active_children"][0]["window_label"] = "hub-november"
        save_program(parent_dir, program)
        program = json.loads((parent_dir / "program.json").read_text())
        cleanup_completed_children(self.root, self.parent, program)
        resolve.assert_called_once_with(
            self.root,
            self.child,
            pane_id=None,
            window_label="hub-november",
        )

    @patch("program_monitor.close_child_window")
    @patch("program_monitor.resolve_child_window")
    @patch("program_monitor.in_tmux", return_value=True)
    def test_cleanup_skips_non_completed_workflow_phase(
        self,
        _in_tmux,
        resolve,
        close,
    ) -> None:
        parent_dir = self.root / "sessions" / self.parent
        program = json.loads((parent_dir / "program.json").read_text())
        cleanup_completed_children(self.root, self.parent, program)
        resolve.assert_not_called()
        close.assert_not_called()
        program = json.loads((parent_dir / "program.json").read_text())
        self.assertEqual(program["active_children"][0]["status"], "running")

    @patch("program_monitor.close_child_window")
    @patch("program_monitor.resolve_child_window")
    @patch.dict(os.environ, {}, clear=True)
    def test_cleanup_without_tmux_updates_status_only(
        self,
        resolve,
        close,
    ) -> None:
        os.environ.pop("TMUX", None)
        self._write_completed_child_workflow()
        parent_dir = self.root / "sessions" / self.parent
        program = json.loads((parent_dir / "program.json").read_text())
        cleanup_completed_children(self.root, self.parent, program)
        program = json.loads((parent_dir / "program.json").read_text())
        self.assertEqual(program["active_children"][0]["status"], "completed")
        resolve.assert_not_called()
        close.assert_not_called()

    @patch("program_monitor.close_child_window", return_value=True)
    @patch("program_monitor.resolve_child_window", return_value="%9")
    @patch("program_monitor.is_safe_child_close_target", return_value=True)
    @patch("program_monitor.in_tmux", return_value=True)
    def test_monitor_program_runs_cleanup(
        self,
        _in_tmux,
        _safe,
        resolve,
        close,
    ) -> None:
        self._write_completed_child_workflow()
        monitor_program(self.root, self.parent)
        resolve.assert_called()
        close.assert_called()
        program = json.loads(
            (self.root / "sessions" / self.parent / "program.json").read_text()
        )
        self.assertEqual(program["active_children"][0]["status"], "completed")


    def _add_second_child(self, codename: str = "oscar") -> None:
        child_dir = self.root / "sessions" / codename
        child_dir.mkdir(parents=True)
        (child_dir / "artifacts").mkdir()
        (child_dir / "workflow.json").write_text(
            json.dumps(
                {
                    "version": 2,
                    "phase": "implementation",
                    "gates": {"brief_accepted": True, "plan_user_accepted": True},
                    "loops": {},
                    "artifacts": {},
                },
                indent=2,
            )
            + "\n"
        )
        (child_dir / "session.json").write_text(
            json.dumps({"codename": codename, "title": f"{codename} title", "tasks": []})
            + "\n"
        )
        (child_dir / "TASKS.md").write_text(f"# Tasks\n\n## Goal\n\n{codename} goal\n")
        parent_dir = self.root / "sessions" / self.parent
        program = default_program(self.parent)
        program["proposed_children"] = [
            {
                "id": "c1",
                "suggested_codename": self.child,
                "title": "Child scope title",
                "goal": "Deliver child feature X",
                "repo": "template",
                "depends_on": [],
            },
            {
                "id": "c2",
                "suggested_codename": codename,
                "title": "Second child title",
                "goal": "Deliver second feature Y",
                "repo": "template",
                "depends_on": [],
            },
        ]
        program["active_children"] = [
            {"codename": self.child, "status": "running"},
            {"codename": codename, "status": "running"},
        ]
        save_program(parent_dir, program)

    def test_sibling_program_context_excludes_self(self) -> None:
        self._add_second_child("oscar")
        parent_dir = self.root / "sessions" / self.parent
        program = default_program(self.parent)
        from program_state import load_program

        program = load_program(parent_dir)
        siblings = sibling_program_context(
            self.root, program, self.child, pending_gate="brief_review"
        )
        self.assertEqual(len(siblings), 1)
        self.assertEqual(siblings[0]["codename"], "oscar")
        self.assertEqual(siblings[0]["decomposition_scope"]["goal"], "Deliver second feature Y")

    def test_monitor_gate_review_includes_sibling_context(self) -> None:
        self._add_second_child("oscar")
        child_dir = self.root / "sessions" / self.child
        (child_dir / "artifacts" / "problem-brief.md").write_text("# Brief\n")
        report = monitor_program(self.root, self.parent)
        child = next(c for c in report["children"] if c["codename"] == self.child)
        review = child["gate_review"]
        self.assertIn("sibling_program_context", review)
        siblings = review["sibling_program_context"]
        self.assertEqual(len(siblings), 1)
        self.assertEqual(siblings[0]["codename"], "oscar")

    def test_sibling_plan_summary_at_plan_gate(self) -> None:
        self._add_second_child("oscar")
        oscar_dir = self.root / "sessions" / "oscar"
        (oscar_dir / "artifacts" / "action-plan.md").write_text(
            """# Plan

## Tasks

| ID | Repo | Summary | Acceptance | Depends |
|----|------|---------|------------|---------|
| t1 | template | Edit monitor | Done when shipped | — |

## Files / areas

- `scripts/lib/program_monitor.py`
"""
        )
        child_dir = self.root / "sessions" / self.child
        (child_dir / "artifacts" / "action-plan.md").write_text("# Plan\n")
        (child_dir / "workflow.json").write_text(
            json.dumps(
                {
                    "version": 2,
                    "phase": "plan_user_review",
                    "gates": {"brief_accepted": True, "plan_user_accepted": False},
                    "loops": {},
                    "artifacts": {},
                },
                indent=2,
            )
            + "\n"
        )
        report = monitor_program(self.root, self.parent)
        child = next(c for c in report["children"] if c["codename"] == self.child)
        review = child["gate_review"]
        oscar_entry = next(
            s for s in review["sibling_program_context"] if s["codename"] == "oscar"
        )
        self.assertIn("plan_summary", oscar_entry)
        self.assertEqual(oscar_entry["plan_summary"]["tasks"][0]["id"], "t1")
        self.assertIn("program_monitor.py", oscar_entry["plan_summary"]["files_areas"][0])

    def test_render_program_status_with_child_reviews(self) -> None:
        self._add_second_child("oscar")
        child_dir = self.root / "sessions" / self.child
        (child_dir / "artifacts" / "problem-brief.md").write_text("# Brief\n")
        report = monitor_program(self.root, self.parent)
        body = render_program_status_markdown(
            report,
            child_reviews={
                self.child: {
                    "next": "Accept brief or send corrections",
                    "parent_assessment": "Aligned with pc6 scope.",
                    "cross_child_check": "No overlap with oscar.",
                    "child_agent_action": "Wait for accept brief.",
                }
            },
        )
        self.assertIn("Sibling context", body)
        self.assertIn("**Parent assessment**", body)
        self.assertIn("Aligned with pc6 scope.", body)
        self.assertIn("**Cross-child check**", body)
        self.assertIn("Accept brief or send corrections", body)


if __name__ == "__main__":
    unittest.main()
