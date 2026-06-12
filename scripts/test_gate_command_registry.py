#!/usr/bin/env python3
"""Tests for shared gate command registry."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from gate_command_registry import (  # noqa: E402
    ACCEPT_BRIEF,
    ACCEPT_PLAN,
    GATE_COMMAND_ACTIONS,
    REOPEN_BRIEF,
    REOPEN_PLAN,
    allowed_route_messages,
    classify_gate_command,
    command_pattern,
    is_allowed_route_message,
    is_gate_command_action,
    normalize_route_message,
    phase_command_actions,
)
from program_state import GATE_PHASES  # noqa: E402

_LIB_DIR = Path(__file__).resolve().parent / "lib"
_REGISTRY_FILE = _LIB_DIR / "gate_command_registry.py"
_CONSUMER_FILES = (
    _LIB_DIR / "program_route_feedback.py",
    _LIB_DIR / "workflow_inbox_gate.py",
)
_FORBIDDEN_DUPLICATE_NAMES = (
    "ALLOWED_MESSAGES",
    "_COMMAND_PATTERNS",
    "_PHASE_COMMANDS",
    "_GATE_COMMAND_ACTIONS",
)
_GATE_USER_LITERALS = ("accept brief", "accept plan", "reopen brief", "reopen plan")


class GateCommandRegistryTests(unittest.TestCase):
    def test_phases_align_with_program_state(self) -> None:
        for phase in GATE_PHASES:
            self.assertIsNotNone(allowed_route_messages(phase))
        self.assertEqual(len(allowed_route_messages("brief_review")), 3)
        self.assertEqual(len(allowed_route_messages("plan_user_review")), 2)

    def test_gate_command_actions_complete(self) -> None:
        self.assertEqual(
            GATE_COMMAND_ACTIONS,
            frozenset({ACCEPT_BRIEF, ACCEPT_PLAN, REOPEN_BRIEF, REOPEN_PLAN}),
        )
        for action in GATE_COMMAND_ACTIONS:
            self.assertTrue(is_gate_command_action(action))

    def test_route_messages_match_classifier(self) -> None:
        for phase in sorted(GATE_PHASES):
            for msg in sorted(allowed_route_messages(phase)):
                classified = classify_gate_command(phase, msg)
                self.assertIsNotNone(
                    classified,
                    msg=f"{msg!r} at {phase!r} must classify to a gate action",
                )
                self.assertIn(classified, phase_command_actions(phase))
                self.assertTrue(is_allowed_route_message(phase, msg))

    def test_is_allowed_route_message(self) -> None:
        self.assertTrue(is_allowed_route_message("brief_review", "Accept Brief"))
        self.assertTrue(is_allowed_route_message("brief_review", "accept"))
        self.assertFalse(is_allowed_route_message("brief_review", "accept plan"))
        self.assertTrue(is_allowed_route_message("brief_review", "reopen brief"))
        self.assertTrue(is_allowed_route_message("plan_user_review", "reopen plan"))

    def test_classify_reopen_and_workflow_prefix(self) -> None:
        self.assertEqual(classify_gate_command("brief_review", "reopen brief"), REOPEN_BRIEF)
        self.assertEqual(classify_gate_command("plan_user_review", "reopen plan"), REOPEN_PLAN)
        self.assertEqual(
            classify_gate_command("brief_review", "workflow: accept brief"),
            ACCEPT_BRIEF,
        )

    def test_normalize_route_message(self) -> None:
        self.assertEqual(normalize_route_message("  Accept Plan  "), "accept plan")

    def test_phase_command_actions_unknown_phase(self) -> None:
        self.assertEqual(phase_command_actions("implementation"), ())

    def test_command_pattern_lookup(self) -> None:
        self.assertIsNotNone(command_pattern(ACCEPT_BRIEF))
        self.assertIsNone(command_pattern("not_an_action"))

    def test_single_source_gate_vocabulary(self) -> None:
        for path in _CONSUMER_FILES:
            text = path.read_text()
            for name in _FORBIDDEN_DUPLICATE_NAMES:
                self.assertNotIn(
                    name,
                    text,
                    msg=f"{path.name} must not define duplicate gate table {name}",
                )
        for path in _LIB_DIR.glob("*.py"):
            if path == _REGISTRY_FILE:
                continue
            text = path.read_text()
            for literal in _GATE_USER_LITERALS:
                self.assertNotIn(
                    f'"{literal}"',
                    text,
                    msg=f"{path.name} must not hardcode gate user string {literal!r}",
                )

    def test_classify_rejects_prose(self) -> None:
        self.assertIsNone(
            classify_gate_command(
                "brief_review",
                "brief looks good — proceed to accept brief.",
            )
        )


if __name__ == "__main__":
    unittest.main()
