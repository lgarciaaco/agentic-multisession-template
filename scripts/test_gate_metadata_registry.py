#!/usr/bin/env python3
"""Tests for shared gate metadata registry."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from gate_metadata_registry import (  # noqa: E402
    GATE_METADATA,
    gate_artifact_path,
    gate_column_short_label,
    gate_display_label,
    gate_feedback_kind,
)
from program_state import GATE_PHASES  # noqa: E402

_LIB_DIR = Path(__file__).resolve().parent / "lib"
_CONSUMER_FILES = (
    _LIB_DIR / "program_monitor.py",
    _LIB_DIR / "workflow_inbox_gate.py",
)
_FORBIDDEN_LOCAL_DICTS = ("GATE_ARTIFACT", "_PHASE_FEEDBACK")


class GateMetadataRegistryTests(unittest.TestCase):
    def test_keys_match_gate_phases(self) -> None:
        self.assertEqual(frozenset(GATE_METADATA), GATE_PHASES)

    def test_each_phase_has_required_fields(self) -> None:
        for phase in sorted(GATE_PHASES):
            entry = GATE_METADATA[phase]
            for field in ("artifact_path", "feedback_kind", "display_label", "column_short"):
                self.assertTrue(entry[field].strip(), msg=f"{phase}.{field} must be non-empty")

    def test_artifact_paths_match_prior_gate_artifact(self) -> None:
        self.assertEqual(gate_artifact_path("brief_review"), "artifacts/problem-brief.md")
        self.assertEqual(gate_artifact_path("plan_user_review"), "artifacts/action-plan.md")

    def test_feedback_kinds(self) -> None:
        self.assertEqual(gate_feedback_kind("brief_review"), "brief_correction")
        self.assertEqual(gate_feedback_kind("plan_user_review"), "plan_feedback")

    def test_column_short_labels(self) -> None:
        self.assertEqual(gate_column_short_label("brief_review"), "brief")
        self.assertEqual(gate_column_short_label("plan_user_review"), "plan")
        self.assertEqual(gate_column_short_label(None), "—")
        self.assertEqual(gate_column_short_label("implementation"), "—")

    def test_display_labels(self) -> None:
        self.assertEqual(gate_display_label("brief_review"), "Brief review")
        self.assertEqual(gate_display_label("plan_user_review"), "Plan review")

    def test_consumers_use_registry_not_local_dicts(self) -> None:
        for path in _CONSUMER_FILES:
            text = path.read_text()
            for name in _FORBIDDEN_LOCAL_DICTS:
                self.assertNotIn(
                    f"{name} =",
                    text,
                    msg=f"{path.name} must not define local gate metadata dict {name}",
                )


if __name__ == "__main__":
    unittest.main()
