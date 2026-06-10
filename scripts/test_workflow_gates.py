#!/usr/bin/env python3
"""Tests for workflow accept-plan and implementation gates (M5)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from session_binding import (  # noqa: E402
    guard_path_decision,
    workflow_gate_denies_worktree,
)
from workflow_plan import (  # noqa: E402
    accept_action_plan,
    parse_action_plan_tasks,
    sync_action_plan_tasks,
)

FIXTURE_PLAN = """# Action plan — checkout fix

**Status:** reviewer_approved
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


class WorkflowGatesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.codename = "alpha"
        self.session_dir = self.root / "sessions" / self.codename
        self.session_dir.mkdir(parents=True)
        (self.session_dir / "artifacts").mkdir()
        (self.session_dir / "artifacts" / "action-plan.md").write_text(FIXTURE_PLAN)
        (self.session_dir / "TASKS.md").write_text(
            "# Session alpha\n\n## Goal\n\nFix checkout.\n\n## Tasks\n\n| ID | Status | Notes |\n"
            "|----|--------|-------|\n| old | done | legacy |\n\n## Notes\n\n"
        )
        (self.session_dir / "session.json").write_text(
            json.dumps({"codename": self.codename, "mode": "product", "tasks": []}) + "\n"
        )
        (self.session_dir / "workflow.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "phase": "plan_user_review",
                    "gates": {"brief_accepted": True, "plan_user_accepted": False},
                    "loops": {"plan": {"iteration": 1, "max": 5, "last_verdict": "APPROVE"}},
                    "artifacts": {
                        "brief": "artifacts/problem-brief.md",
                        "plan": "artifacts/action-plan.md",
                    },
                }
            )
            + "\n"
        )
        (self.root / "repos.yaml").write_text(
            "repos:\n  my-app:\n    path: repos/my-app\n    clone: git@github.com:YOU/my-app.git\n"
        )
        (self.root / "repos" / "my-app").mkdir(parents=True)
        (self.root / "repos" / "my-app" / ".git").mkdir()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_parse_action_plan_tasks(self) -> None:
        tasks = parse_action_plan_tasks(FIXTURE_PLAN)
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0]["id"], "t1")
        self.assertEqual(tasks[0]["repo"], "my-app")
        self.assertEqual(tasks[1]["depends"], "t1")

    def test_parse_action_plan_tasks_pipe_in_acceptance(self) -> None:
        plan = """## Tasks

| ID | Repo | Summary | Acceptance | Depends |
|----|------|---------|------------|---------|
| t1 | hub | Doc sweep | `rg -i 'foo|bar'` returns clean | — |
| t2 | hub | Depends t1 | Done when t1 merged | t1 |
"""
        tasks = parse_action_plan_tasks(plan)
        self.assertEqual(len(tasks), 2)
        self.assertIn("foo|bar", tasks[0]["acceptance"])
        self.assertEqual(tasks[1]["depends"], "t1")

    def test_accept_plan_syncs_session_and_tasks_md(self) -> None:
        result = accept_action_plan(self.root, self.codename)
        self.assertEqual(result["phase"], "implementation")
        session = json.loads((self.session_dir / "session.json").read_text())
        self.assertEqual(len(session["tasks"]), 2)
        self.assertEqual(session["tasks"][0]["repo"], "my-app")
        self.assertEqual(session["tasks"][0]["acceptance"], "UI test passes")
        tasks_md = (self.session_dir / "TASKS.md").read_text()
        self.assertIn("| t1 | pending |", tasks_md)
        self.assertIn("repo: my-app", tasks_md)
        workflow = json.loads((self.session_dir / "workflow.json").read_text())
        self.assertTrue(workflow["gates"]["plan_user_accepted"])
        plan = (self.session_dir / "artifacts" / "action-plan.md").read_text()
        self.assertIn("**Status:** user_approved", plan)

    def test_sync_action_plan_tasks_validates_repo(self) -> None:
        bad_plan = FIXTURE_PLAN.replace("my-app", "unknown-repo")
        (self.session_dir / "artifacts" / "action-plan.md").write_text(bad_plan)
        with self.assertRaises(ValueError):
            sync_action_plan_tasks(self.root, self.codename)

    def test_guard_denies_worktree_without_plan_accept(self) -> None:
        gate = workflow_gate_denies_worktree(self.root, self.codename)
        self.assertIsNotNone(gate)
        self.assertEqual(gate["permission"], "deny")
        path = str(self.session_dir / "worktrees" / "my-app" / "src" / "main.py")
        decision = guard_path_decision(self.root, self.codename, path)
        self.assertEqual(decision["permission"], "deny")

    def test_guard_allows_worktree_after_plan_accept(self) -> None:
        accept_action_plan(self.root, self.codename)
        path = str(self.session_dir / "worktrees" / "my-app" / "src" / "main.py")
        decision = guard_path_decision(self.root, self.codename, path)
        self.assertEqual(decision["permission"], "allow")

    def test_accept_plan_rejects_when_brief_not_accepted(self) -> None:
        workflow_path = self.session_dir / "workflow.json"
        workflow = json.loads(workflow_path.read_text())
        workflow["gates"]["brief_accepted"] = False
        workflow_path.write_text(json.dumps(workflow, indent=2) + "\n")
        with self.assertRaises(ValueError):
            accept_action_plan(self.root, self.codename)

    def test_accept_plan_rejects_wrong_phase(self) -> None:
        workflow_path = self.session_dir / "workflow.json"
        workflow = json.loads(workflow_path.read_text())
        workflow["phase"] = "intake"
        workflow_path.write_text(json.dumps(workflow, indent=2) + "\n")
        with self.assertRaises(ValueError):
            accept_action_plan(self.root, self.codename)

    def test_guard_denies_hub_root_even_after_plan_accept(self) -> None:
        """Self-hosted model: bound sessions edit worktrees only, not hub root."""
        accept_action_plan(self.root, self.codename)
        path = str(self.root / "scripts" / "test_session_binding.py")
        decision = guard_path_decision(self.root, self.codename, path)
        self.assertEqual(decision["permission"], "deny")

    def test_sync_action_plan_rejects_traversal_artifact_path(self) -> None:
        workflow_path = self.session_dir / "workflow.json"
        workflow = json.loads(workflow_path.read_text())
        workflow["artifacts"]["plan"] = "../../../repos/evil.md"
        workflow_path.write_text(json.dumps(workflow, indent=2) + "\n")
        with self.assertRaises(ValueError):
            sync_action_plan_tasks(self.root, self.codename)


if __name__ == "__main__":
    unittest.main()
