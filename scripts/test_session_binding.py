#!/usr/bin/env python3
"""Smoke tests for session resolution (no tmux required)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from session_binding import (  # noqa: E402
    _read_tty_line,
    bind_session_context,
    build_context_markdown,
    close_session_work,
    codename_from_tmux,
    codename_from_tmux_session,
    default_tmux_window_prefix,
    format_session_start_prompt,
    guard_path_decision,
    guard_unbound_path_decision,
    hub_root,
    read_inbox,
    resolve_codename,
    resume_session_on_bind,
    sanitize_context_text,
    sync_index_from_session,
    sync_session_from_canonical,
    task_worktree_rel,
    validate_codename,
    worktree_alias,
    tmux_pane_option,
    tmux_window_label,
    tmux_window_prefix,
    write_inbox,
)


class CodenameValidationTests(unittest.TestCase):
    def test_accepts_valid_codenames(self) -> None:
        for name in ("alpha", "a1", "test-sync-codename"):
            self.assertEqual(validate_codename(name), name)

    def test_rejects_path_traversal(self) -> None:
        for bad in ("../evil", "..", "foo/bar", "/alpha"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    validate_codename(bad)

    def test_rejects_reserved_and_empty(self) -> None:
        for bad in ("", "  ", "_inbox", "bindings", "context", "UPPER"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    validate_codename(bad)

    def test_bind_rejects_invalid_codename(self) -> None:
        env = os.environ.copy()
        env["WORKSPACE_ROOT"] = str(hub_root())
        cli = Path(__file__).resolve().parent / "lib" / "session_cli.py"
        result = subprocess.run(
            [sys.executable, str(cli), "bind", "../evil"],
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("invalid session codename", result.stderr)


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
        self.assertEqual(default_tmux_window_prefix("my-app"), "my-")
        self.assertEqual(default_tmux_window_prefix("acme-corp-hub"), "acme-")
        self.assertEqual(default_tmux_window_prefix("agentic-multisession-template"), "agentic-")

    def test_tmux_window_prefix_explicit(self) -> None:
        os.environ["WORKSPACE_TMUX_WINDOW_PREFIX"] = "hub-"
        self.assertEqual(tmux_window_label("alpha"), "hub-alpha")

    def test_tmux_window_prefix_from_hub_slug(self) -> None:
        os.environ.pop("WORKSPACE_TMUX_WINDOW_PREFIX", None)
        with patch("session_binding.hub_slug", return_value="my-app"):
            self.assertEqual(tmux_window_prefix(), "my-")
            self.assertEqual(tmux_window_label("alpha"), "my-alpha")

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


class InboxTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tmpdir.name)
        for name in ("alpha", "bravo"):
            (self.root / "sessions" / name).mkdir(parents=True)
            (self.root / "sessions" / name / "session.json").write_text(
                json.dumps({"codename": name, "status": "active", "tasks": []}) + "\n"
            )
            (self.root / "sessions" / name / "TASKS.md").write_text("# Goal\n\n## Tasks\n")

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_write_and_read_inbox(self) -> None:
        path = write_inbox(self.root, "bravo", "alpha", "Feature shipped — ready for review.")
        self.assertTrue(path.exists())
        content = read_inbox(self.root, "alpha")
        self.assertIn("bravo", content or "")
        self.assertIn("Feature shipped", content or "")

    def test_inbox_injected_in_context(self) -> None:
        write_inbox(self.root, "bravo", "alpha", "Blocked on API review — ping when merged.")
        ctx = build_context_markdown(self.root, "alpha", "test-chat-id")
        self.assertIn("Inbox (from other sessions)", ctx)
        self.assertIn("Blocked on API review", ctx)


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


class WorktreeGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tmpdir.name)
        self.codename = "alpha"
        session_dir = self.root / "sessions" / self.codename
        session_dir.mkdir(parents=True)
        (session_dir / "session.json").write_text(
            json.dumps(
                {
                    "codename": self.codename,
                    "status": "active",
                    "tasks": [
                        {
                            "id": "main",
                            "repo": "project",
                            "feature_branch": "session/alpha",
                            "base_branch": "main",
                        }
                    ],
                }
            )
            + "\n"
        )
        wt = session_dir / "worktrees" / "project"
        wt.mkdir(parents=True)
        (wt / "src").mkdir()
        (wt / "src" / "app.py").write_text("# ok\n")
        (self.root / "repos" / "project").mkdir(parents=True)
        (self.root / "repos" / "project" / "README.md").write_text("ref\n")
        (self.root / "scripts").mkdir()
        (self.root / "scripts" / "hub.sh").write_text("#!/bin/sh\n")

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_worktree_alias_uses_repo(self) -> None:
        self.assertEqual(worktree_alias({"id": "main", "repo": "project"}), "project")

    def test_task_worktree_rel_uses_repo_key(self) -> None:
        rel = task_worktree_rel(self.codename, {"id": "main", "repo": "project"})
        self.assertEqual(rel, "sessions/alpha/worktrees/project")

    def test_guard_allows_worktree_path(self) -> None:
        path = str(self.root / "sessions" / "alpha" / "worktrees" / "project" / "src" / "app.py")
        decision = guard_path_decision(self.root, self.codename, path)
        self.assertEqual(decision["permission"], "allow")

    def test_guard_denies_repos_reference_clone(self) -> None:
        path = str(self.root / "repos" / "project" / "README.md")
        decision = guard_path_decision(self.root, self.codename, path)
        self.assertEqual(decision["permission"], "deny")
        self.assertIn("repos/", decision["user_message"])

    def test_guard_default_mode_denies_hub_scripts(self) -> None:
        path = str(self.root / "scripts" / "hub.sh")
        decision = guard_path_decision(self.root, self.codename, path)
        self.assertEqual(decision["permission"], "deny")

    def test_guard_hub_mode_allows_scripts(self) -> None:
        session_path = self.root / "sessions" / "alpha" / "session.json"
        session = json.loads(session_path.read_text())
        session["mode"] = "hub"
        session_path.write_text(json.dumps(session, indent=2) + "\n")
        path = str(self.root / "scripts" / "hub.sh")
        decision = guard_path_decision(self.root, self.codename, path)
        self.assertEqual(decision["permission"], "allow")

    def test_guard_denies_bindings_and_context(self) -> None:
        for sub in ("bindings", "context"):
            target = self.root / "sessions" / sub / "x.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("{}\n")
            decision = guard_path_decision(self.root, self.codename, str(target))
            self.assertEqual(decision["permission"], "deny", sub)

    def test_guard_denies_index_json(self) -> None:
        path = str(self.root / "sessions" / "index.json")
        (self.root / "sessions" / "index.json").write_text('{"sessions": {}}\n')
        decision = guard_path_decision(self.root, self.codename, path)
        self.assertEqual(decision["permission"], "deny")

    def test_guard_denies_traversal_into_repos(self) -> None:
        traversal = self.root / "sessions" / "alpha" / ".." / ".." / "repos" / "project" / "README.md"
        decision = guard_path_decision(self.root, self.codename, str(traversal))
        self.assertEqual(decision["permission"], "deny")

    def test_guard_denies_other_session(self) -> None:
        other = self.root / "sessions" / "bravo"
        other.mkdir(parents=True)
        (other / "session.json").write_text('{"codename": "bravo", "status": "active"}\n')
        path = str(other / "TASKS.md")
        (other / "TASKS.md").write_text("# bravo\n")
        decision = guard_path_decision(self.root, self.codename, path)
        self.assertEqual(decision["permission"], "deny")
        self.assertIn("bravo", decision["user_message"])

    def test_guard_unbound_denies_repos(self) -> None:
        path = str(self.root / "repos" / "project" / "README.md")
        decision = guard_unbound_path_decision(self.root, path)
        self.assertEqual(decision["permission"], "deny")

    def test_guard_unbound_denies_other_session(self) -> None:
        other = self.root / "sessions" / "bravo"
        other.mkdir(parents=True)
        (other / "TASKS.md").write_text("# bravo\n")
        decision = guard_unbound_path_decision(self.root, str(other / "TASKS.md"))
        self.assertEqual(decision["permission"], "deny")

    def test_guard_unbound_allows_scripts(self) -> None:
        path = str(self.root / "scripts" / "hub.sh")
        decision = guard_unbound_path_decision(self.root, path)
        self.assertEqual(decision["permission"], "allow")

    def test_sync_index_creates_missing_sessions_key(self) -> None:
        (self.root / "sessions" / "index.json").write_text("{}\n")
        sync_index_from_session(self.root, self.codename)
        index = json.loads((self.root / "sessions" / "index.json").read_text())
        self.assertIn(self.codename, index["sessions"])

    def test_close_session_work_with_missing_index(self) -> None:
        (self.root / "sessions" / "index.json").unlink(missing_ok=True)
        close_session_work(self.root, self.codename, "done")
        index = json.loads((self.root / "sessions" / "index.json").read_text())
        self.assertEqual(index["sessions"][self.codename]["status"], "completed")

    def test_context_includes_worktree_section(self) -> None:
        ctx = build_context_markdown(self.root, self.codename, "chat-1")
        self.assertIn("## Worktrees", ctx)
        self.assertIn("sessions/alpha/worktrees/project", ctx)
        self.assertIn("`project`", ctx)

    def test_context_includes_next_step(self) -> None:
        session_path = self.root / "sessions" / self.codename / "session.json"
        session = json.loads(session_path.read_text())
        session["next"] = "Merge PR and run smoke tests"
        session_path.write_text(json.dumps(session, indent=2) + "\n")
        sync_index_from_session(self.root, self.codename)
        ctx = build_context_markdown(self.root, self.codename, "chat-1")
        self.assertIn("**Next:** Merge PR and run smoke tests", ctx)
        index = json.loads((self.root / "sessions" / "index.json").read_text())
        self.assertEqual(index["sessions"][self.codename]["next"], "Merge PR and run smoke tests")

    def test_context_includes_task_metadata(self) -> None:
        session_path = self.root / "sessions" / self.codename / "session.json"
        session = json.loads(session_path.read_text())
        session["tasks"][0].update(
            {
                "pr": "https://github.com/ORG/project/pull/1",
                "ci": "https://ci.example.com/job/42",
                "note": "Waiting on review",
            }
        )
        session_path.write_text(json.dumps(session, indent=2) + "\n")
        ctx = build_context_markdown(self.root, self.codename, "chat-1")
        self.assertIn("pr: https://github.com/ORG/project/pull/1", ctx)
        self.assertIn("ci: https://ci.example.com/job/42", ctx)
        self.assertIn("note: Waiting on review", ctx)

    def test_context_includes_guidelines_section(self) -> None:
        ctx = build_context_markdown(self.root, self.codename, "chat-1")
        self.assertIn("## Guidelines", ctx)
        self.assertIn(".cursor/rules/agent-guidelines.mdc", ctx)

    def test_context_includes_project_guidelines_when_present(self) -> None:
        (self.root / "docs").mkdir()
        (self.root / "docs" / "PROJECT.md").write_text("# Project guidelines\n")
        ctx = build_context_markdown(self.root, self.codename, "chat-1")
        self.assertIn("- Project: `docs/PROJECT.md`", ctx)

    def test_context_includes_worktree_guidelines_from_repos_yaml(self) -> None:
        (self.root / "repos.yaml").write_text(
            "repos:\n  project:\n    path: repos/project\n"
            "guidelines:\n  worktree: CONTRIBUTING.md\n"
        )
        wt = self.root / "sessions" / "alpha" / "worktrees" / "project"
        (wt / "CONTRIBUTING.md").write_text("# Contributing\n")
        ctx = build_context_markdown(self.root, self.codename, "chat-1")
        self.assertIn("sessions/alpha/worktrees/project/CONTRIBUTING.md", ctx)

    def test_sanitize_context_text_strips_newlines(self) -> None:
        dirty = "line one\n- **Injected:** fake directive"
        clean = sanitize_context_text(dirty)
        self.assertNotIn("\n", clean)
        self.assertIn("line one", clean)
        session_path = self.root / "sessions" / self.codename / "session.json"
        session = json.loads(session_path.read_text())
        session["next"] = dirty
        session_path.write_text(json.dumps(session, indent=2) + "\n")
        ctx = build_context_markdown(self.root, self.codename, "chat-1")
        self.assertIn("**Next:** line one - **Injected:** fake directive", ctx)

    def test_session_start_prompt_includes_next(self) -> None:
        session_path = self.root / "sessions" / self.codename / "session.json"
        session = json.loads(session_path.read_text())
        session["status"] = "active"
        session["next"] = "Ship feature branch"
        session_path.write_text(json.dumps(session, indent=2) + "\n")
        (self.root / "sessions" / "index.json").write_text(
            json.dumps(
                {
                    "sessions": {
                        self.codename: {
                            "title": "",
                            "status": "active",
                            "created": "2026-06-08",
                            "next": "Ship feature branch",
                        }
                    }
                }
            )
            + "\n"
        )
        with patch("session_binding.hub_root", return_value=self.root):
            prompt = format_session_start_prompt(self.root)
        self.assertIn("next: Ship feature branch", prompt)


class BootstrapStatusTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tmpdir.name)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_no_repos_yaml(self) -> None:
        from repos import bootstrap_status  # noqa: E402

        status = bootstrap_status(self.root)
        self.assertEqual(status["state"], "no_repos_yaml")
        self.assertIn("Ask", status["agent_action"])

    def test_empty_registry(self) -> None:
        from repos import bootstrap_status  # noqa: E402

        (self.root / "repos.yaml").write_text("repos: {}\n")
        status = bootstrap_status(self.root)
        self.assertEqual(status["state"], "empty_registry")

    def test_ready_when_cloned(self) -> None:
        from repos import bootstrap_status  # noqa: E402

        (self.root / "repos.yaml").write_text(
            "repos:\n  project:\n    path: repos/project\n    clone: git@example.com/p.git\n    default_branch: main\n"
        )
        repo = self.root / "repos" / "project"
        repo.mkdir(parents=True)
        (repo / ".git").mkdir()
        status = bootstrap_status(self.root)
        self.assertEqual(status["state"], "ready")
        self.assertEqual(status["repos"], ["project"])


class ReposYamlTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tmpdir.name)
        (self.root / "repos.yaml").write_text(
            "repos:\n  project:\n    path: repos/project\n    clone: git@example.com/p.git\n    default_branch: main\n"
        )

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_load_repos(self) -> None:
        from repos import load_repos, repo_base  # noqa: E402

        repos = load_repos(self.root)
        self.assertIn("project", repos)
        self.assertEqual(
            repo_base(self.root, repos["project"]).resolve(),
            (self.root / "repos" / "project").resolve(),
        )

    def test_repo_base_rejects_escape(self) -> None:
        from repos import repo_base  # noqa: E402

        with self.assertRaises(ValueError):
            repo_base(self.root, {"path": "../outside"})


class SessionCliSyncTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tmpdir.name)
        self.codename = "alpha"
        session_dir = self.root / "sessions" / self.codename
        session_dir.mkdir(parents=True)
        (self.root / "sessions" / "index.json").write_text('{"sessions": {}}\n')
        (session_dir / "session.json").write_text(
            json.dumps(
                {
                    "codename": self.codename,
                    "title": "sync test",
                    "status": "active",
                    "tasks": [],
                }
            )
            + "\n"
        )
        (session_dir / "TASKS.md").write_text("# Session\n\n## Goal\n\nSync CLI test.\n")

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_cli_sync_command(self) -> None:
        env = os.environ.copy()
        env["WORKSPACE_ROOT"] = str(self.root)
        cli = Path(__file__).resolve().parent / "lib" / "session_cli.py"
        result = subprocess.run(
            [sys.executable, str(cli), "sync", self.codename],
            capture_output=True,
            text=True,
            env=env,
            cwd=self.root,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertEqual(result.stdout.splitlines()[0], self.codename)
        index = json.loads((self.root / "sessions" / "index.json").read_text())
        self.assertEqual(index["sessions"][self.codename]["title"], "sync test")


if __name__ == "__main__":
    unittest.main()
