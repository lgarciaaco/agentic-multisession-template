#!/usr/bin/env python3
"""Tests for shared workflow review ID helpers."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from workflow_ids import latest_review_id, next_review_id, scan_review_ids  # noqa: E402


class WorkflowIdsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.directory = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_scan_review_ids_pr_and_r(self) -> None:
        (self.directory / "pr-001.json").write_text("{}\n")
        (self.directory / "pr-010.json").write_text("{}\n")
        (self.directory / "r-002.json").write_text("{}\n")
        (self.directory / "ignore.txt").write_text("x\n")
        self.assertEqual(scan_review_ids(self.directory, "pr"), [1, 10])
        self.assertEqual(scan_review_ids(self.directory, "r"), [2])

    def test_next_review_id_increments(self) -> None:
        (self.directory / "pr-001.json").write_text("{}\n")
        self.assertEqual(next_review_id(self.directory, "pr"), "pr-002")
        self.assertEqual(next_review_id(self.directory, "r"), "r-001")

    def test_latest_review_id_returns_highest(self) -> None:
        (self.directory / "r-001.json").write_text("{}\n")
        (self.directory / "r-003.json").write_text("{}\n")
        self.assertEqual(latest_review_id(self.directory, "r"), "r-003")
        self.assertIsNone(latest_review_id(self.directory, "pr"))

    def test_scan_review_ids_ignores_non_json_files(self) -> None:
        (self.directory / "r-001.json").write_text("{}\n")
        (self.directory / "r-005.txt").write_text("x\n")
        self.assertEqual(scan_review_ids(self.directory, "r"), [1])
        self.assertEqual(next_review_id(self.directory, "r"), "r-002")

    def test_scan_review_ids_non_directory_returns_empty(self) -> None:
        self.assertEqual(scan_review_ids(Path("/nonexistent/path"), "r"), [])
        file_path = self.directory / "file.json"
        file_path.write_text("{}\n")
        self.assertEqual(scan_review_ids(file_path, "r"), [])

    def test_next_review_id_creates_directory(self) -> None:
        nested = self.directory / "nested" / "reviews"
        self.assertEqual(next_review_id(nested, "pr"), "pr-001")
        self.assertTrue(nested.is_dir())


if __name__ == "__main__":
    unittest.main()
