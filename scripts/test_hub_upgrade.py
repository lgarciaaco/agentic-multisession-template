#!/usr/bin/env python3
"""Tests for hub template version check and in-place upgrade."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from hub_upgrade import (  # noqa: E402
    DEFAULT_UPSTREAM,
    UpstreamSnapshot,
    compare_versions,
    ensure_upstream_tree,
    hub_status,
    hub_upgrade,
    parse_changelog,
    parse_version,
    read_installed_version,
    read_version_from_tree,
    releases_between,
    resolve_upstream_url,
    validate_semver,
    validate_upstream_url,
    version_ref,
    _plain_summary,
    _read_upstream_file,
    _session_guidance,
)
from session_binding import guard_path_decision  # noqa: E402


SAMPLE_CHANGELOG = """# Changelog

## [0.4.0] - 2026-06-08

### Added

- In-place hub upgrade scripts

### Hub changes

- Hub status JSON output

### Session notes

**Impact:** none

- Existing sessions keep working

## [0.3.0]

### Added

- Worktrees per session

### Session notes

**Impact:** optional

- Run ensure-worktrees after adding tasks

## [0.2.0] - 2026-06-05

### Added

- Session inbox

### Session notes

**Impact:** required

- Mention inbox in active session docs
"""


class HubUpgradeParsingTests(unittest.TestCase):
    def test_parse_changelog_extracts_releases(self) -> None:
        releases = parse_changelog(SAMPLE_CHANGELOG)
        self.assertEqual([release.version for release in releases], ["0.4.0", "0.3.0", "0.2.0"])
        self.assertEqual(releases[0].session_impact, "none")
        self.assertEqual(releases[1].session_impact, "optional")
        self.assertEqual(releases[2].session_impact, "required")
        self.assertIn("Hub status JSON output", releases[0].hub_bullets)
        self.assertIsNone(releases[1].date)

    def test_compare_versions_and_prefix(self) -> None:
        self.assertEqual(compare_versions("0.2.0", "0.3.0"), -1)
        self.assertEqual(compare_versions("v1.0.0", "1.0.1"), -1)

    def test_parse_version_rejects_invalid(self) -> None:
        for bad in ("1.2", "a.b.c", "", "  "):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    parse_version(bad)

    def test_validate_semver(self) -> None:
        self.assertEqual(validate_semver("v0.4.0"), "0.4.0")
        with self.assertRaises(ValueError):
            validate_semver("bad")

    def test_releases_between(self) -> None:
        releases = parse_changelog(SAMPLE_CHANGELOG)
        pending = releases_between(releases, "0.2.0", "0.4.0")
        self.assertEqual([release.version for release in pending], ["0.3.0", "0.4.0"])

    def test_releases_between_none_current(self) -> None:
        releases = parse_changelog(SAMPLE_CHANGELOG)
        pending = releases_between(releases, None, "0.4.0")
        self.assertEqual(len(pending), 3)

    def test_read_installed_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertIsNone(read_installed_version(root))
            (root / ".hub-version").write_text("0.3.0\n")
            self.assertEqual(read_installed_version(root), "0.3.0")
            (root / ".hub-version").write_text("  \n")
            self.assertIsNone(read_installed_version(root))

    def test_read_version_from_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "CHANGELOG.md").write_text(SAMPLE_CHANGELOG)
            self.assertEqual(read_version_from_tree(root), "0.4.0")
            (root / ".hub-version").write_text("0.3.0\n")
            self.assertEqual(read_version_from_tree(root), "0.3.0")

    def test_plain_summary_and_session_guidance(self) -> None:
        releases = parse_changelog(SAMPLE_CHANGELOG)
        pending = releases_between(releases, "0.2.0", "0.4.0")
        summary = _plain_summary(pending)
        self.assertIn("0.3.0", summary)
        guidance = _session_guidance(pending)
        self.assertEqual(guidance["impact"], "optional")
        self.assertIn("0.3.0", guidance["optional_versions"])


class ResolveUpstreamTests(unittest.TestCase):
    def test_resolve_upstream_url_precedence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(resolve_upstream_url(root), DEFAULT_UPSTREAM)
            (root / ".hub-upstream").write_text("# comment\nhttps://github.com/lgarciaaco/agentic-multisession-template.git\n")
            self.assertTrue(
                resolve_upstream_url(root).endswith("agentic-multisession-template.git")
            )
            (root / ".hub-upstream").write_text("\n")
            self.assertEqual(resolve_upstream_url(root), DEFAULT_UPSTREAM)

        with patch.dict(os.environ, {"WORKSPACE_TEMPLATE_UPSTREAM": "https://github.com/lgarciaaco/agentic-multisession-template.git"}):
            self.assertTrue(resolve_upstream_url().endswith(".git"))

    def test_validate_upstream_url(self) -> None:
        self.assertEqual(
            validate_upstream_url(DEFAULT_UPSTREAM),
            DEFAULT_UPSTREAM,
        )
        with self.assertRaises(ValueError):
            validate_upstream_url("file:///tmp/evil")
        with self.assertRaises(ValueError):
            validate_upstream_url("https://evil.example/agentic-multisession-template")
        with patch.dict(os.environ, {"WORKSPACE_ALLOW_UNTRUSTED_UPSTREAM": "1"}):
            url = validate_upstream_url(
                "https://evil.example/agentic-multisession-template",
                allow_untrusted=True,
            )
            self.assertIn("evil.example", url)

    def test_read_upstream_file_skips_comments(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".hub-upstream").write_text("# only comment\n")
            self.assertIsNone(_read_upstream_file(root))


class HubUpgradeFlowTests(unittest.TestCase):
    def _upstream(self, root: Path, version: str = "0.4.0") -> Path:
        upstream = root / "upstream"
        upstream.mkdir()
        (upstream / ".hub-version").write_text(f"{version}\n")
        (upstream / "CHANGELOG.md").write_text(SAMPLE_CHANGELOG)
        scripts = upstream / "scripts"
        scripts.mkdir()
        (scripts / "hub-status.sh").write_text("#!/bin/sh\n")
        return upstream

    def test_hub_status_ok(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".hub-version").write_text("0.4.0\n")
            upstream = self._upstream(root)
            snapshot = UpstreamSnapshot(tree=upstream, url=DEFAULT_UPSTREAM, ref="main", sha="abc1234")

            with patch("hub_upgrade.ensure_upstream_tree", return_value=snapshot):
                status = hub_status(root)

            self.assertEqual(status["state"], "ok")
            self.assertFalse(status["update_available"])

    def test_hub_status_unreachable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch(
                "hub_upgrade.ensure_upstream_tree",
                side_effect=RuntimeError("network down"),
            ):
                status = hub_status(root)
            self.assertEqual(status["state"], "upstream_unreachable")

    def test_hub_status_invalid_changelog(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            upstream = root / "upstream"
            upstream.mkdir()
            (upstream / ".hub-version").write_text("0.4.0\n")
            snapshot = UpstreamSnapshot(tree=upstream, url=DEFAULT_UPSTREAM, ref="main", sha="abc1234")
            with patch("hub_upgrade.ensure_upstream_tree", return_value=snapshot):
                status = hub_status(root)
            self.assertEqual(status["state"], "upstream_invalid")

    def test_hub_upgrade_apply_writes_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".hub-version").write_text("0.3.0\n")
            upstream = self._upstream(root, "0.4.0")
            snapshot = UpstreamSnapshot(tree=upstream, url=DEFAULT_UPSTREAM, ref="v0.4.0", sha="abc1234")

            ok_status = {
                "state": "ok",
                "current_version": "0.3.0",
                "latest_version": "0.4.0",
                "upstream": DEFAULT_UPSTREAM,
                "upstream_ref": "main",
                "upstream_sha": "abc1234",
                "upstream_trusted": True,
            }

            with patch("hub_upgrade.hub_status", return_value=ok_status), patch(
                "hub_upgrade._resolve_upgrade_snapshot", return_value=snapshot
            ):
                result = hub_upgrade(root, dry_run=False)

            self.assertTrue(result["ok"])
            self.assertTrue(result["changed"])
            self.assertEqual(read_installed_version(root), "0.4.0")
            self.assertTrue((root / "scripts" / "hub-status.sh").exists())

    def test_hub_upgrade_invalid_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ok_status = {
                "state": "ok",
                "current_version": "0.3.0",
                "latest_version": "0.4.0",
                "upstream": DEFAULT_UPSTREAM,
            }
            with patch("hub_upgrade.hub_status", return_value=ok_status):
                result = hub_upgrade(root, target_version="not-a-version")
            self.assertFalse(result["ok"])
            self.assertIn("invalid semver", result["error"])

    def test_hub_upgrade_already_current(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".hub-version").write_text("0.4.0\n")
            ok_status = {
                "state": "ok",
                "current_version": "0.4.0",
                "latest_version": "0.4.0",
                "upstream": DEFAULT_UPSTREAM,
            }
            with patch("hub_upgrade.hub_status", return_value=ok_status):
                result = hub_upgrade(root)
            self.assertTrue(result["ok"])
            self.assertFalse(result["changed"])

    def test_hub_upgrade_version_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".hub-version").write_text("0.3.0\n")
            upstream = self._upstream(root, "0.3.0")
            snapshot = UpstreamSnapshot(tree=upstream, url=DEFAULT_UPSTREAM, ref="v0.4.0", sha="abc1234")
            ok_status = {
                "state": "ok",
                "current_version": "0.3.0",
                "latest_version": "0.4.0",
                "upstream": DEFAULT_UPSTREAM,
            }
            with patch("hub_upgrade.hub_status", return_value=ok_status), patch(
                "hub_upgrade._resolve_upgrade_snapshot", return_value=snapshot
            ):
                result = hub_upgrade(root, target_version="0.4.0")
            self.assertFalse(result["ok"])
            self.assertIn("does not match", result["error"])

    def test_version_ref(self) -> None:
        self.assertEqual(version_ref("0.4.0"), "v0.4.0")


class HubUpgradeShellTests(unittest.TestCase):
    def test_hub_upgrade_help(self) -> None:
        root = Path(__file__).resolve().parent.parent
        result = subprocess.run(
            [str(root / "scripts" / "hub-upgrade.sh"), "--help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("--allow-untrusted-upstream", result.stdout)


class HubGuardTests(unittest.TestCase):
    def test_hub_mode_denies_hub_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            session_dir = root / "sessions" / "alpha"
            session_dir.mkdir(parents=True)
            (session_dir / "session.json").write_text('{"mode":"hub","tasks":[]}\n')
            decision = guard_path_decision(root, "alpha", str(root / ".hub-version"))
            self.assertEqual(decision["permission"], "deny")


if __name__ == "__main__":
    unittest.main()
