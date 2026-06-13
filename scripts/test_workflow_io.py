#!/usr/bin/env python3
"""Tests for workflow I/O helpers."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from workflow_io import read_summary_json  # noqa: E402


class ReadSummaryJsonTests(unittest.TestCase):
    def test_missing_raise(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "missing.json"
            with self.assertRaises(FileNotFoundError):
                read_summary_json(path, missing="raise")

    def test_missing_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "missing.json"
            self.assertIsNone(read_summary_json(path, missing="none"))

    def test_invalid_json_raises_value_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text("{not json")
            with self.assertRaises(ValueError) as ctx:
                read_summary_json(path)
            self.assertIn("invalid JSON", str(ctx.exception))

    def test_valid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ok.json"
            path.write_text('{"verdict": "PASS"}\n')
            self.assertEqual(read_summary_json(path), {"verdict": "PASS"})


if __name__ == "__main__":
    unittest.main()
