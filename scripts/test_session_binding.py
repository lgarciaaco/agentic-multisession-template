#!/usr/bin/env python3
"""Smoke tests for session resolution (no tmux required)."""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from session_binding import (  # noqa: E402
    _read_tty_line,
    bind_session_context,
    codename_from_tmux,
    codename_from_tmux_session,
    default_tmux_window_prefix,
    hub_root,
    resolve_codename,
    resume_session_on_bind,
    sync_index_from_session,
    sync_session_from_canonical,
    tmux_pane_option,
    tmux_window_label,
    tmux_window_prefix,
)


class ResolveSessionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = hub_root()
        self._env = os.environ.copy()

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self._env)

    def test_binding_wins_over_tmux(self) -> None:
        os.environ["WORKSPACE_CONVERSATION_ID"] = "test-binding-wins"
        binding_dir = self.root / "sessions" / "bindings"
        binding_dir.mkdir(parents=True, exist_ok=True)
        binding_file = binding_dir / "test-binding-wins.json"
        binding_file.write_text(
            '{"conversation_id": "test-binding-wins", "codename": "alpha", "bound_at": "2026-01-01T00:00:00+00:00"}\n'
        )
        try:
            with patch("session_binding.get_tmux_window_name", return_value="bravo"):
                with patch("session_binding.is_active_session", return_value=True):
                    codename, source = resolve_codename(self.root)
            self.assertEqual(codename, "alpha")
            self.assertEqual(source, "binding")
        finally:
            binding_file.unlink(missing_ok=True)

    def test_tmux_when_unbound(self) -> None:
        os.environ.pop("WORKSPACE_CONVERSATION_ID", None)
        with patch("session_binding.get_tmux_pane_codename", return_value=None):
            with patch("session_binding.get_tmux_session_bound_codenames", return_value=set()):
                with patch("session_binding.get_tmux_window_name", return_value="bravo"):
                    with patch("session_binding.is_active_session", return_value=True):
                        codename, source = resolve_codename(self.root)
        self.assertEqual(codename, "bravo")
        self.assertEqual(source, "tmux")

    def test_unbound_without_tmux_match(self) -> None:
        os.environ.pop("WORKSPACE_CONVERSATION_ID", None)
        with patch("session_binding.get_tmux_pane_codename", return_value=None):
            with patch("session_binding.get_tmux_session_bound_codenames", return_value=set()):
                with patch("session_binding.get_tmux_window_name", return_value="bash"):
                    codename, source = resolve_codename(self.root)
        self.assertIsNone(codename)
        self.assertEqual(source, "")

    def test_tmux_pane_wins_over_window_name(self) -> None:
        os.environ.pop("WORKSPACE_CONVERSATION_ID", None)
        with patch("session_binding.get_tmux_pane_codename", return_value="bravo"):
            with patch("session_binding.get_tmux_session_bound_codenames", return_value=set()):
                with patch("session_binding.get_tmux_window_name", return_value="node"):
                    with patch("session_binding.is_active_session", return_value=True):
                        codename, source = resolve_codename(self.root)
        self.assertEqual(codename, "bravo")
        self.assertEqual(source, "tmux-pane")

    def test_tmux_session_inherit_single_codename(self) -> None:
        os.environ.pop("WORKSPACE_CONVERSATION_ID", None)
        with patch("session_binding.get_tmux_pane_codename", return_value=None):
            with patch("session_binding.get_tmux_window_name", return_value="bash"):
                with patch(
                    "session_binding.get_tmux_session_bound_codenames",
                    return_value={"alpha"},
                ):
                    codename, source = resolve_codename(self.root)
        self.assertEqual(codename, "alpha")
        self.assertEqual(source, "tmux-session")

    def test_default_tmux_window_prefix_from_slug(self) -> None:
        self.assertEqual(default_tmux_window_prefix("immo-investor"), "immo-")
        self.assertEqual(default_tmux_window_prefix("my-app"), "my-")
        self.assertEqual(default_tmux_window_prefix("agentic-multisession-template"), "agentic-")

    def test_tmux_window_prefix_explicit(self) -> None:
        os.environ["WORKSPACE_TMUX_WINDOW_PREFIX"] = "hub-"
        self.assertEqual(tmux_window_label("alpha"), "hub-alpha")

    def test_tmux_window_prefix_from_hub_slug(self) -> None:
        os.environ.pop("WORKSPACE_TMUX_WINDOW_PREFIX", None)
        with patch("session_binding.hub_slug", return_value="immo-investor"):
            self.assertEqual(tmux_window_prefix(), "immo-")
            self.assertEqual(tmux_window_label("alpha"), "immo-alpha")

    def test_tmux_window_prefix_disabled(self) -> None:
        os.environ["WORKSPACE_TMUX_WINDOW_PREFIX"] = ""
        self.assertEqual(tmux_window_prefix(), "")
        self.assertEqual(tmux_window_label("alpha"), "alpha")

    def test_tmux_pane_option_default(self) -> None:
        os.environ.pop("WORKSPACE_TMUX_PANE_OPTION", None)
        self.assertEqual(tmux_pane_option(), "workspace-codename")

    def test_read_tty_line_ctrl_c_exits_130(self) -> None:
        with patch("session_binding.open", side_effect=KeyboardInterrupt):
            with self.assertRaises(SystemExit) as ctx:
                _read_tty_line("Session> ")
        self.assertEqual(ctx.exception.code, 130)


class SessionSyncTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = hub_root()
        self._tmpdir = tempfile.TemporaryDirectory()
        self.test_root = Path(self._tmpdir.name)
        self.codename = "test-sync-codename"
        session_dir = self.test_root / "sessions" / self.codename
        session_dir.mkdir(parents=True)
        (self.test_root / "sessions" / "bindings").mkdir(parents=True)
        (self.test_root / "sessions" / "context").mkdir(parents=True)
        (self.test_root / "sessions" / "index.json").write_text(
            json.dumps(
                {
                    "sessions": {
                        self.codename: {
                            "title": "old title",
                            "status": "paused",
                            "created": "2026-01-01",
                            "paused_at": "2026-01-02",
                        }
                    }
                },
                indent=2,
            )
            + "\n"
        )
        (session_dir / "session.json").write_text(
            json.dumps(
                {
                    "codename": self.codename,
                    "title": "canonical title",
                    "status": "paused",
                    "created": "2026-01-01",
                    "tasks": [{"id": "task-a", "status": "running"}],
                },
                indent=2,
            )
            + "\n"
        )
        (session_dir / "TASKS.md").write_text("# Session\n\n## Goal\n\nDo the thing.\n")
        (session_dir / "progress.json").write_text(json.dumps({"status": "paused"}) + "\n")
        template = self.root / "sessions" / "_template" / "BOUNDARIES.md"
        if template.exists():
            shutil.copy(template, session_dir / "BOUNDARIES.md")

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_resume_session_on_bind_sets_active_and_syncs_index(self) -> None:
        resume_session_on_bind(self.test_root, self.codename)
        session = json.loads((self.test_root / "sessions" / self.codename / "session.json").read_text())
        index = json.loads((self.test_root / "sessions" / "index.json").read_text())["sessions"][self.codename]
        progress = json.loads((self.test_root / "sessions" / self.codename / "progress.json").read_text())

        self.assertEqual(session["status"], "active")
        self.assertNotIn("paused_at", session)
        self.assertEqual(index["status"], "active")
        self.assertEqual(index["title"], "canonical title")
        self.assertNotIn("paused_at", index)
        self.assertEqual(progress["status"], "active")
        self.assertIn("last_bound_at", progress)

    def test_sync_session_from_canonical_refreshes_context(self) -> None:
        cid = "test-chat-sync"
        binding_dir = self.test_root / "sessions" / "bindings"
        (binding_dir / f"{cid}.json").write_text(
            json.dumps({"conversation_id": cid, "codename": self.codename}) + "\n"
        )

        sync_session_from_canonical(
            self.test_root,
            self.codename,
            resume=False,
            refresh_context=True,
            conversation_id=cid,
        )
        context = (self.test_root / "sessions" / "context" / f"{cid}.md").read_text()
        self.assertIn("canonical title", context)
        self.assertIn("task-a", context)
        self.assertIn("Do the thing.", context)

    def test_bind_session_context_resume_and_binding_timestamps(self) -> None:
        os.environ["WORKSPACE_CONVERSATION_ID"] = "test-bind-resume"
        try:
            with patch("session_binding.set_tmux_pane_codename", return_value=True):
                with patch("session_binding.rename_tmux_for_codename", return_value=True):
                    bind_session_context(self.test_root, self.codename)
            binding = json.loads(
                (self.test_root / "sessions" / "bindings" / "test-bind-resume.json").read_text()
            )
            self.assertEqual(binding["codename"], self.codename)
            self.assertIn("bound_at", binding)
            self.assertIn("last_active_at", binding)
            session = json.loads((self.test_root / "sessions" / self.codename / "session.json").read_text())
            self.assertEqual(session["status"], "active")
        finally:
            os.environ.pop("WORKSPACE_CONVERSATION_ID", None)
            (self.test_root / "sessions" / "bindings" / "test-bind-resume.json").unlink(missing_ok=True)
            (self.test_root / "sessions" / "context" / "test-bind-resume.md").unlink(missing_ok=True)

    def test_sync_index_without_resume(self) -> None:
        sync_index_from_session(self.test_root, self.codename)
        index = json.loads((self.test_root / "sessions" / "index.json").read_text())["sessions"][self.codename]
        session = json.loads((self.test_root / "sessions" / self.codename / "session.json").read_text())
        self.assertEqual(index["title"], "canonical title")
        self.assertEqual(index["status"], session["status"])


if __name__ == "__main__":
    unittest.main()
