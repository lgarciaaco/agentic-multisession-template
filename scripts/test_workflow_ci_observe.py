#!/usr/bin/env python3
"""Tests for CI observe loop (workflow_ci_observe.py)."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))

from workflow_ci_observe import (  # noqa: E402
    advance_ci_observe,
    begin_ci_observe,
    ci_observe_complete,
    ci_observe_escalate,
    ci_observe_needs_fix,
    ci_observe_needs_rebase,
)


class CiObserveLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.session_dir = self.root / "sessions" / "test"
        self.session_dir.mkdir(parents=True)
        workflow = {
            "version": 2,
            "phase": "ci_observe",
            "gates": {"brief_accepted": True, "plan_user_accepted": True},
            "loops": {
                "plan": {"iteration": 1, "max": 5, "last_verdict": "APPROVE"},
                "code_review": {"iteration": 1, "max": 5, "last_verdict": "PASS", "task_id": "t1"},
                "implementation": {"active_task": "t1", "ready_for_review": False},
                "pr_creation": {"iteration": 1, "max": 5, "last_verdict": "SUCCESS"},
                "ci_observe": {"iteration": 0, "max": 5, "last_verdict": None},
            },
            "artifacts": {},
        }
        (self.session_dir / "workflow.json").write_text(json.dumps(workflow, indent=2) + "\n")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_begin_ci_observe_resets_loop(self) -> None:
        workflow = begin_ci_observe(self.session_dir)
        ci_loop = workflow["loops"]["ci_observe"]
        self.assertEqual(ci_loop["iteration"], 0)
        self.assertIsNone(ci_loop["last_verdict"])

    def test_green_transitions_to_delivery(self) -> None:
        workflow = advance_ci_observe(self.session_dir, "GREEN")
        self.assertEqual(workflow["phase"], "delivery")
        self.assertEqual(workflow["loops"]["ci_observe"]["last_verdict"], "GREEN")

    def test_conflict_stays_in_ci_observe(self) -> None:
        workflow = advance_ci_observe(self.session_dir, "CONFLICT")
        self.assertEqual(workflow["phase"], "ci_observe")
        self.assertEqual(workflow["loops"]["ci_observe"]["iteration"], 1)

    def test_test_failure_stays_in_ci_observe(self) -> None:
        workflow = advance_ci_observe(self.session_dir, "TEST_FAILURE")
        self.assertEqual(workflow["phase"], "ci_observe")

    def test_timeout_escalates(self) -> None:
        self.assertTrue(ci_observe_escalate("TIMEOUT", 1, 5))

    def test_fail_escalates(self) -> None:
        self.assertTrue(ci_observe_escalate("FAIL", 1, 5))

    def test_escalate_at_max_iterations(self) -> None:
        self.assertTrue(ci_observe_escalate("CONFLICT", 5, 5))
        self.assertFalse(ci_observe_escalate("CONFLICT", 3, 5))

    def test_needs_rebase(self) -> None:
        self.assertTrue(ci_observe_needs_rebase("CONFLICT"))
        self.assertFalse(ci_observe_needs_rebase("TEST_FAILURE"))

    def test_needs_fix(self) -> None:
        self.assertTrue(ci_observe_needs_fix("TEST_FAILURE"))
        self.assertFalse(ci_observe_needs_fix("CONFLICT"))

    def test_complete(self) -> None:
        self.assertTrue(ci_observe_complete("GREEN"))
        self.assertFalse(ci_observe_complete("CONFLICT"))

    def test_multi_iteration_conflict_then_green(self) -> None:
        advance_ci_observe(self.session_dir, "CONFLICT")
        workflow = advance_ci_observe(self.session_dir, "GREEN")
        self.assertEqual(workflow["phase"], "delivery")
        self.assertEqual(workflow["loops"]["ci_observe"]["iteration"], 2)

    def test_advance_cli_subprocess(self) -> None:
        script = Path(__file__).resolve().parent / "workflow-ci-observe-advance.py"
        env = {"PYTHONPATH": str(Path(__file__).resolve().parent / "lib")}
        env["WORKSPACE_ROOT"] = str(self.root)
        result = subprocess.run(
            [sys.executable, str(script), "test", "GREEN"],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.strip().splitlines()
        self.assertEqual(lines[1], "GREEN")
        self.assertEqual(lines[2], "delivery")


class SkillSanitizationTests(unittest.TestCase):
    """Smoke tests: grep skills for forbidden domain tokens."""

    FORBIDDEN_EXACT = ["OCP_REPO", "ART_REPO", "AOS_CD_JOBS", "rh-pre-commit", "ocp-build-data"]
    FORBIDDEN_WORD_BOUNDARY = ["OCP", "AOS"]

    def _skill_content(self, rel_path: str) -> str:
        skill_dir = Path(__file__).resolve().parent.parent / ".cursor" / "skills"
        path = skill_dir / rel_path
        if not path.exists():
            self.skipTest(f"{path} not found")
        return path.read_text()

    def _assert_no_forbidden(self, content: str, label: str) -> None:
        import re

        for token in self.FORBIDDEN_EXACT:
            self.assertNotIn(token, content, f"{label} contains forbidden token: {token}")
        for token in self.FORBIDDEN_WORD_BOUNDARY:
            pattern = rf"\b{re.escape(token)}\b"
            self.assertIsNone(
                re.search(pattern, content),
                f"{label} contains forbidden word: {token}",
            )

    def test_git_commit_no_domain_tokens(self) -> None:
        content = self._skill_content("git-commit/SKILL.md")
        self._assert_no_forbidden(content, "git-commit skill")

    def test_pr_create_no_domain_tokens(self) -> None:
        content = self._skill_content("pr-create/SKILL.md")
        self._assert_no_forbidden(content, "pr-create skill")

    def test_pr_create_template_no_domain_tokens(self) -> None:
        content = self._skill_content("pr-create/templates/generic.md")
        self._assert_no_forbidden(content, "pr-create template")


if __name__ == "__main__":
    unittest.main()
