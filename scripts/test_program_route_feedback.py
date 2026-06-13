#!/usr/bin/env python3
"""CLI smoke tests for program-route-feedback.py."""

from __future__ import annotations

import re
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from program_state import GATE_PHASES  # noqa: E402

_SCRIPT = Path(__file__).resolve().parent / "program-route-feedback.py"


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


if __name__ == "__main__":
    unittest.main()
