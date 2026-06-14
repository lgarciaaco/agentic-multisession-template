#!/usr/bin/env python3
"""CLI smoke tests for program-route-feedback.py."""

from __future__ import annotations

import io
import json
import re
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from program_route_feedback import (  # noqa: E402
    evaluate_route_correction,
    evaluate_route_feedback,
)
from program_state import GATE_PHASES, default_program, save_program  # noqa: E402

_SCRIPT = Path(__file__).resolve().parent / "program-route-feedback.py"
_ROOT = Path(__file__).resolve().parent.parent


class ProgramRouteFeedbackHelpTests(unittest.TestCase):
    def test_help_lists_gate_phases_in_choices(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(_SCRIPT), "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        combined = proc.stdout + proc.stderr
        self.assertIn("--gate", combined)
        match = re.search(r"--gate\s*\{([^}]+)\}", combined)
        self.assertIsNotNone(match, msg="--help must show --gate {…} choices line")
        choices = match.group(1)
        for phase in GATE_PHASES:
            self.assertIn(phase, choices, msg=f"--gate choices must include {phase!r}")

    def test_help_lists_force_flag(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(_SCRIPT), "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        combined = proc.stdout + proc.stderr
        self.assertIn("--force", combined)


class ProgramRouteFeedbackCliOutputTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.parent = "mike"
        self.child = "november"
        parent_dir = self.root / "sessions" / self.parent
        child_dir = self.root / "sessions" / self.child
        parent_dir.mkdir(parents=True)
        child_dir.mkdir(parents=True)
        program = default_program(self.parent)
        program["active_children"] = [
            {"codename": self.child, "status": "running", "pane_id": "%1"}
        ]
        save_program(parent_dir, program)
        workflow = {
            "version": 2,
            "phase": "brief_review",
            "gates": {"brief_accepted": True, "plan_user_accepted": False},
            "loops": {},
            "artifacts": {},
        }
        (child_dir / "workflow.json").write_text(json.dumps(workflow, indent=2) + "\n")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _run_main(self, *argv: str) -> tuple[int, str]:
        import importlib.util

        spec = importlib.util.spec_from_file_location("program_route_feedback_cli", _SCRIPT)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        buf = io.StringIO()
        with mock.patch.object(sys, "argv", [str(_SCRIPT), *argv]):
            with mock.patch("hub_paths.hub_root", return_value=self.root):
                with mock.patch("program_route_feedback.in_tmux", return_value=True):
                    with mock.patch(
                        "program_route_feedback.resolve_child_pane",
                        return_value="%1",
                    ):
                        with mock.patch("program_route_feedback.send_to_child_pane"):
                            with mock.patch(
                                "program_route_feedback.resolve_codename",
                                return_value=(self.parent, "binding"),
                            ):
                                with redirect_stdout(buf):
                                    spec.loader.exec_module(module)
                                    code = module.main()
        return code, buf.getvalue()

    def _run_main_with_stderr(self, *argv: str) -> tuple[int, str, str]:
        import importlib.util

        spec = importlib.util.spec_from_file_location("program_route_feedback_cli", _SCRIPT)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        out_buf = io.StringIO()
        err_buf = io.StringIO()
        with mock.patch.object(sys, "argv", [str(_SCRIPT), *argv]):
            with mock.patch("hub_paths.hub_root", return_value=self.root):
                with mock.patch("program_route_feedback.in_tmux", return_value=True):
                    with mock.patch(
                        "program_route_feedback.resolve_child_pane",
                        return_value="%1",
                    ):
                        with mock.patch("program_route_feedback.send_to_child_pane"):
                            with mock.patch(
                                "program_route_feedback.resolve_codename",
                                return_value=(self.parent, "binding"),
                            ):
                                with redirect_stdout(out_buf), redirect_stderr(err_buf):
                                    spec.loader.exec_module(module)
                                    code = module.main()
        return code, out_buf.getvalue(), err_buf.getvalue()

    def test_cli_prints_skipped_when_gate_already_accepted(self) -> None:
        code, out = self._run_main(
            self.parent,
            self.child,
            "--gate",
            "brief_review",
            "--message",
            "accept brief",
        )
        self.assertEqual(code, 0)
        self.assertIn("skipped: brief gate already accepted", out)

    def test_cli_prints_sent_on_successful_route(self) -> None:
        child_dir = self.root / "sessions" / self.child
        workflow = {
            "version": 2,
            "phase": "brief_review",
            "gates": {"brief_accepted": False, "plan_user_accepted": False},
            "loops": {},
            "artifacts": {},
        }
        (child_dir / "workflow.json").write_text(json.dumps(workflow, indent=2) + "\n")
        code, out = self._run_main(
            self.parent,
            self.child,
            "--gate",
            "brief_review",
            "--message",
            "accept brief",
        )
        self.assertEqual(code, 0)
        self.assertIn("sent: accept brief", out)

    def test_cli_prints_skipped_on_dedupe_cooldown(self) -> None:
        child_dir = self.root / "sessions" / self.child
        workflow = {
            "version": 2,
            "phase": "brief_review",
            "gates": {"brief_accepted": False, "plan_user_accepted": False},
            "loops": {},
            "artifacts": {},
        }
        (child_dir / "workflow.json").write_text(json.dumps(workflow, indent=2) + "\n")
        recent = (
            datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )
        parent_dir = self.root / "sessions" / self.parent
        program = default_program(self.parent)
        program["active_children"] = [
            {
                "codename": self.child,
                "status": "running",
                "pane_id": "%1",
                "last_routed_at": recent,
                "last_routed_message": "accept brief",
            }
        ]
        save_program(parent_dir, program)
        code, out = self._run_main(
            self.parent,
            self.child,
            "--gate",
            "brief_review",
            "--message",
            "accept brief",
        )
        self.assertEqual(code, 0)
        self.assertIn("skipped:", out)
        self.assertIn("cooldown", out)

    def test_cli_prints_skipped_on_wrong_phase_correction(self) -> None:
        child_dir = self.root / "sessions" / self.child
        workflow = {
            "version": 2,
            "phase": "plan_loop",
            "gates": {"brief_accepted": True, "plan_user_accepted": False},
            "loops": {},
            "artifacts": {},
        }
        (child_dir / "workflow.json").write_text(json.dumps(workflow, indent=2) + "\n")
        code, out = self._run_main(
            self.parent,
            self.child,
            "--correction",
            "--message",
            "Tighten SC-1 wording.",
        )
        self.assertEqual(code, 0)
        self.assertIn("skipped:", out)
        self.assertIn("plan_loop", out)

    def test_cli_rejects_wrong_phase_gate_route(self) -> None:
        child_dir = self.root / "sessions" / self.child
        workflow = {
            "version": 2,
            "phase": "plan_user_review",
            "gates": {"brief_accepted": True, "plan_user_accepted": False},
            "loops": {},
            "artifacts": {},
        }
        (child_dir / "workflow.json").write_text(json.dumps(workflow, indent=2) + "\n")
        code, out, err = self._run_main_with_stderr(
            self.parent,
            self.child,
            "--gate",
            "brief_review",
            "--message",
            "accept brief",
        )
        self.assertEqual(code, 1)
        self.assertNotIn("skipped:", out)
        self.assertIn("plan_user_review", err)


class ProgramRouteFeedbackEvaluatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.parent = "mike"
        self.child = "november"
        parent_dir = self.root / "sessions" / self.parent
        child_dir = self.root / "sessions" / self.child
        parent_dir.mkdir(parents=True)
        child_dir.mkdir(parents=True)
        program = default_program(self.parent)
        program["active_children"] = [
            {"codename": self.child, "status": "running", "pane_id": "%1"}
        ]
        save_program(parent_dir, program)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _write_child_workflow(self, workflow: dict) -> None:
        child_dir = self.root / "sessions" / self.child
        (child_dir / "workflow.json").write_text(json.dumps(workflow, indent=2) + "\n")

    def test_evaluate_route_feedback_phase_mismatch(self) -> None:
        self._write_child_workflow(
            {
                "version": 2,
                "phase": "plan_loop",
                "gates": {"brief_accepted": True, "plan_user_accepted": False},
                "loops": {},
                "artifacts": {},
            }
        )
        result = evaluate_route_feedback(
            self.root,
            parent=self.parent,
            child=self.child,
            gate="brief_review",
            message="accept brief",
        )
        self.assertFalse(result["routable"])
        self.assertIn("plan_loop", result["skip_reason"] or "")

    def test_evaluate_route_feedback_gate_already_accepted(self) -> None:
        self._write_child_workflow(
            {
                "version": 2,
                "phase": "brief_review",
                "gates": {"brief_accepted": True, "plan_user_accepted": False},
                "loops": {},
                "artifacts": {},
            }
        )
        result = evaluate_route_feedback(
            self.root,
            parent=self.parent,
            child=self.child,
            gate="brief_review",
            message="accept brief",
        )
        self.assertFalse(result["routable"])
        self.assertIn("already accepted", result["skip_reason"] or "")

    def test_evaluate_route_feedback_dedupe_cooldown(self) -> None:
        self._write_child_workflow(
            {
                "version": 2,
                "phase": "brief_review",
                "gates": {"brief_accepted": False, "plan_user_accepted": False},
                "loops": {},
                "artifacts": {},
            }
        )
        parent_dir = self.root / "sessions" / self.parent
        recent = (
            datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )
        program = default_program(self.parent)
        program["active_children"] = [
            {
                "codename": self.child,
                "status": "running",
                "pane_id": "%1",
                "last_routed_at": recent,
                "last_routed_message": "accept brief",
            }
        ]
        save_program(parent_dir, program)
        result = evaluate_route_feedback(
            self.root,
            parent=self.parent,
            child=self.child,
            gate="brief_review",
            message="accept brief",
        )
        self.assertFalse(result["routable"])
        self.assertIn("cooldown", result["skip_reason"] or "")

    def test_evaluate_route_correction_empty_message(self) -> None:
        self._write_child_workflow(
            {
                "version": 2,
                "phase": "brief_review",
                "gates": {"brief_accepted": False, "plan_user_accepted": False},
                "loops": {},
                "artifacts": {},
            }
        )
        result = evaluate_route_correction(
            self.root,
            parent=self.parent,
            child=self.child,
            message="   ",
        )
        self.assertFalse(result["routable"])
        self.assertIn("must not be empty", result["skip_reason"] or "")

    def test_evaluate_route_correction_phase_skip(self) -> None:
        self._write_child_workflow(
            {
                "version": 2,
                "phase": "implementation",
                "gates": {"brief_accepted": True, "plan_user_accepted": True},
                "loops": {},
                "artifacts": {},
            }
        )
        result = evaluate_route_correction(
            self.root,
            parent=self.parent,
            child=self.child,
            message="Adjust acceptance criteria.",
        )
        self.assertFalse(result["routable"])
        self.assertIn("implementation", result["skip_reason"] or "")

    def test_evaluate_route_feedback_reuses_passed_workflow(self) -> None:
        workflow = {
            "version": 2,
            "phase": "brief_review",
            "gates": {"brief_accepted": False, "plan_user_accepted": False},
            "loops": {},
            "artifacts": {},
        }
        with mock.patch(
            "program_route_feedback._load_child_workflow",
        ) as load_mock:
            result = evaluate_route_feedback(
                self.root,
                parent=self.parent,
                child=self.child,
                gate="brief_review",
                message="accept brief",
                workflow=workflow,
            )
        self.assertTrue(result["routable"])
        load_mock.assert_not_called()

    def test_evaluate_route_correction_reuses_passed_workflow(self) -> None:
        workflow = {
            "version": 2,
            "phase": "brief_review",
            "gates": {"brief_accepted": False, "plan_user_accepted": False},
            "loops": {},
            "artifacts": {},
        }
        with mock.patch(
            "program_route_feedback._load_child_workflow",
        ) as load_mock:
            result = evaluate_route_correction(
                self.root,
                parent=self.parent,
                child=self.child,
                message="Adjust SC-1 wording.",
                workflow=workflow,
            )
        self.assertTrue(result["routable"])
        load_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
