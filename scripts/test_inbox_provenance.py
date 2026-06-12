#!/usr/bin/env python3
"""Tests for inbox provenance sidecar helpers."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from inbox_provenance import (  # noqa: E402
    get_inbox_block_provenance,
    inbox_block_marker,
    inbox_provenance_dir,
    inbox_provenance_path,
    load_inbox_provenance,
    record_inbox_block_provenance,
    save_inbox_provenance,
)
from session_binding import validate_codename  # noqa: E402

_LIB_DIR = Path(__file__).resolve().parent / "lib"
_CONSUMER_FILES = (
    _LIB_DIR / "session_binding.py",
    _LIB_DIR / "workflow_inbox_gate.py",
)
_FORBIDDEN_INLINE_DEFS = (
    "def inbox_provenance_dir",
    "def inbox_block_marker",
    "def _load_inbox_provenance",
    "def load_inbox_provenance",
    "_PROGRAM_GATE_MARKER",
)


class InboxProvenanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_inbox_block_marker_deterministic(self) -> None:
        marker = inbox_block_marker("alpha", "2026-06-12", "hello")
        self.assertEqual(marker, inbox_block_marker("alpha", "2026-06-12", "hello"))
        self.assertTrue(marker.startswith("alpha:2026-06-12:"))

    def test_path_helpers(self) -> None:
        self.assertEqual(
            inbox_provenance_path(self.root, "bravo"),
            inbox_provenance_dir(self.root) / "bravo.json",
        )

    def test_record_load_get_roundtrip(self) -> None:
        marker = inbox_block_marker("parent", "2026-06-12", "accept brief")
        record_inbox_block_provenance(
            self.root,
            "child",
            marker,
            kind="program_route",
            verified_from="parent",
            caller="program-route-feedback",
        )
        loaded = load_inbox_provenance(self.root, "child")
        self.assertIn(marker, loaded)
        entry = get_inbox_block_provenance(self.root, "child", marker)
        self.assertEqual(entry["kind"], "program_route")
        self.assertEqual(entry["verified_from"], "parent")
        self.assertEqual(entry["caller"], "program-route-feedback")

    def test_load_missing_file_returns_empty(self) -> None:
        self.assertEqual(load_inbox_provenance(self.root, "delta"), {})

    def test_load_corrupt_json_returns_empty(self) -> None:
        path = inbox_provenance_path(self.root, "echo")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{not json")
        self.assertEqual(load_inbox_provenance(self.root, "echo"), {})

    def test_load_non_dict_root_returns_empty(self) -> None:
        path = inbox_provenance_path(self.root, "foxtrot")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(["list"]))
        self.assertEqual(load_inbox_provenance(self.root, "foxtrot"), {})

    def test_get_non_dict_entry_returns_none(self) -> None:
        path = inbox_provenance_path(self.root, "golf")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"m1": "string-not-dict"}))
        self.assertIsNone(get_inbox_block_provenance(self.root, "golf", "m1"))

    def test_save_overwrites_sidecar(self) -> None:
        save_inbox_provenance(self.root, "hotel", {"a": {"kind": "cli"}})
        data = load_inbox_provenance(self.root, "hotel")
        self.assertEqual(data["a"]["kind"], "cli")

    def test_validate_codename_matches_session_binding(self) -> None:
        samples = ("alpha", "a1", "test-sync-codename")
        for name in samples:
            self.assertEqual(inbox_provenance_path(self.root, name).name, f"{name}.json")
            self.assertEqual(validate_codename(name), name)
        with self.assertRaises(ValueError):
            inbox_provenance_path(self.root, "../evil")
        with self.assertRaises(ValueError):
            validate_codename("../evil")

    def test_single_source_provenance_helpers(self) -> None:
        for path in _CONSUMER_FILES:
            text = path.read_text()
            for pattern in _FORBIDDEN_INLINE_DEFS:
                self.assertNotIn(
                    pattern,
                    text,
                    msg=f"{path.name} must not redefine provenance helper {pattern!r}",
                )


if __name__ == "__main__":
    unittest.main()
