#!/usr/bin/env python3
"""Smoke tests for program child tmux tab bootstrap."""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from program_bootstrap import bootstrap_children  # noqa: E402
from program_child_tabs import (  # noqa: E402
    ChildWindow,
    format_manual_child_steps,
    launch_child_agents,
    open_child_windows,
)
from program_state import default_program, save_program  # noqa: E402


class ProgramChildTabsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.parent = "mike"
        self.session_dir = self.root / "sessions" / self.parent
        self.session_dir.mkdir(parents=True)
        (self.session_dir / "artifacts").mkdir()
        (self.root / "scripts").mkdir()
        (self.root / "scripts" / "lib").mkdir()
        (self.root / ".hub-launcher").write_text("test-agent\n")

        program = default_program(self.parent)
        program["proposed_children"] = [
            {
                "id": "pc1",
                "suggested_codename": "november",
                "title": "Child one",
                "goal": "Deliver child one",
                "repo": "template",
                "depends_on": [],
            },
            {
                "id": "pc2",
                "suggested_codename": "oscar",
                "title": "Child two",
                "goal": "Deliver child two",
                "repo": "template",
                "depends_on": [],
            },
        ]
        save_program(self.session_dir, program)

        self.tmux_calls: list[list[str]] = []

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _fake_run_tmux(self, *args: str):
        self.tmux_calls.append(list(args))
        if args[:3] == ("display-message", "-p", "#{window_index}"):
            return subprocess.CompletedProcess(args, 0, "0", "")
        if args[:5] == ("new-window", "-d", "-P", "-F", "#{pane_id}"):
            index = sum(1 for call in self.tmux_calls if call[:5] == list(args[:5]))
            return subprocess.CompletedProcess(args, 0, f"%{index}", "")
        return subprocess.CompletedProcess(args, 0, "", "")

    @patch("program_child_tabs._run_tmux")
    @patch.dict(os.environ, {"TMUX": "/tmp/tmux"}, clear=False)
    def test_open_child_windows_detached_with_labels(self, run_tmux) -> None:
        run_tmux.side_effect = self._fake_run_tmux
        with patch("program_child_tabs.tmux_window_label", side_effect=lambda c: f"hub-{c}"):
            with patch("program_child_tabs.tmux_pane_option", return_value="workspace-codename"):
                windows = open_child_windows(self.root, ["november", "oscar"])

        self.assertEqual(len(windows), 2)
        self.assertEqual(windows[0].codename, "november")
        self.assertEqual(windows[0].window_label, "hub-november")
        new_window_calls = [c for c in self.tmux_calls if c[:2] == ["new-window", "-d"]]
        self.assertEqual(len(new_window_calls), 2)
        pane_sets = [c for c in self.tmux_calls if c[:3] == ["set-option", "-p", "-t"]]
        self.assertEqual(len(pane_sets), 2)
        self.assertEqual(self.tmux_calls[-1], ["select-window", "-t", "0"])

    @patch("program_child_tabs._run_tmux")
    @patch.dict(os.environ, {"TMUX": "/tmp/tmux"}, clear=False)
    def test_launch_child_agents_sends_workflow_prompt(self, run_tmux) -> None:
        run_tmux.side_effect = self._fake_run_tmux
        with patch("program_child_tabs.agent_launcher_name", return_value="test-agent"):
            launch_child_agents(
                self.root,
                [ChildWindow("november", "%1", "hub-november")],
            )
        send_calls = [c for c in self.tmux_calls if c[0] == "send-keys"]
        self.assertEqual(len(send_calls), 1)
        self.assertEqual(send_calls[0][1:3], ["-t", "%1"])
        self.assertIn("test-agent", send_calls[0][3])
        self.assertIn("--reuse", send_calls[0][3])
        self.assertIn("--workflow", send_calls[0][3])

    def test_format_manual_child_steps(self) -> None:
        text = format_manual_child_steps(
            [{"codename": "november", "title": "Child one", "goal": "Goal"}],
            launcher="test-agent",
        )
        self.assertIn("child sessions were created", text)
        self.assertIn("test-agent --reuse --workflow", text)
        self.assertNotIn("new-session.sh", text)

    @patch("program_bootstrap._run_script")
    @patch("program_bootstrap.launch_child_agents")
    @patch("program_bootstrap.open_child_windows")
    @patch("program_bootstrap.in_tmux", return_value=True)
    def test_bootstrap_updates_program_and_opens_tabs(
        self,
        _in_tmux,
        open_windows,
        launch_agents,
        run_script,
    ) -> None:
        run_script.side_effect = lambda root, script, *args: {
            ("new-session.sh", "november", "Child one"): "november",
            ("new-session.sh", "oscar", "Child two"): "oscar",
        }.get((script, *args), "ok")

        open_windows.return_value = [
            ChildWindow("november", "%1", "hub-november"),
            ChildWindow("oscar", "%2", "hub-oscar"),
        ]

        result = bootstrap_children(self.root, self.parent, approve=True)

        self.assertTrue(result["tmux"])
        self.assertEqual(len(result["children"]), 2)
        program = json.loads((self.session_dir / "program.json").read_text())
        self.assertTrue(program["decomposition_approved"])
        self.assertEqual(
            [entry["codename"] for entry in program["active_children"]],
            ["november", "oscar"],
        )
        open_windows.assert_called_once()
        launch_agents.assert_called_once()

    @patch("program_bootstrap._run_script")
    @patch.dict(os.environ, {}, clear=True)
    def test_bootstrap_without_tmux_prints_manual_steps(self, run_script) -> None:
        os.environ.pop("TMUX", None)
        run_script.side_effect = lambda root, script, *args: "november"

        with patch("sys.stdout") as stdout:
            result = bootstrap_children(self.root, self.parent, approve=True)

        self.assertFalse(result["tmux"])
        stdout.write.assert_called()

    def test_workspace_agent_reuse_forwards_workflow_prompt(self) -> None:
        hub = Path(__file__).resolve().parent.parent
        with tempfile.TemporaryDirectory() as td:
            mini = Path(td)
            scripts = mini / "scripts"
            lib = scripts / "lib"
            lib.mkdir(parents=True)
            shutil.copy(hub / "scripts/workspace-agent.sh", scripts / "workspace-agent.sh")
            shutil.copy(hub / "scripts/lib/hub-env.sh", lib / "hub-env.sh")
            ensure = scripts / "ensure-session-interactive.sh"
            args_file = mini / "agent-args.txt"
            ensure_log = mini / "ensure-args.txt"
            agent_stub = scripts / "fake-agent.sh"
            agent_stub.write_text(
                f'#!/usr/bin/env bash\nprintf "%s\\n" "$@" > "{args_file}"\n'
            )
            agent_stub.chmod(agent_stub.stat().st_mode | stat.S_IXUSR)
            (mini / "sessions/november").mkdir(parents=True)
            (mini / "sessions/november/session.json").write_text(
                json.dumps({"codename": "november", "tasks": []}) + "\n"
            )

            ensure.write_text(
                f"#!/usr/bin/env bash\n"
                f'printf "%s\\n" "$@" > "{ensure_log}"\n'
                f"echo november\n"
            )
            ensure.chmod(ensure.stat().st_mode | stat.S_IXUSR)
            env = {
                **os.environ,
                "WORKSPACE_ROOT": str(mini),
                "WORKSPACE_AGENT_BIN": str(agent_stub),
                "WORKSPACE_HUB_SLUG": "testhub",
                "WORKSPACE_AGENT_NO_TTY": "1",
            }
            result = subprocess.run(
                ["bash", str(scripts / "workspace-agent.sh"), "--reuse", "--workflow"],
                cwd=mini,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("--reuse", ensure_log.read_text())
            self.assertIn("/workflow-orchestrator", args_file.read_text())

    def _install_bootstrap_cli(self) -> Path:
        hub = Path(__file__).resolve().parent.parent
        dest_lib = self.root / "scripts/lib"
        dest_lib.mkdir(parents=True, exist_ok=True)
        for module in (hub / "scripts/lib").glob("*.py"):
            shutil.copy(module, dest_lib / module.name)
        for rel in (
            "program-bootstrap-children.py",
            "new-session.sh",
            "set-session-scope.sh",
        ):
            shutil.copy(hub / "scripts" / rel, self.root / "scripts" / rel)
        for script in ("new-session.sh", "set-session-scope.sh"):
            path = self.root / "scripts" / script
            path.chmod(path.stat().st_mode | stat.S_IXUSR)
        (self.root / "scripts/new-session.sh").write_text(
            "#!/usr/bin/env bash\necho \"${1:-child}\"\n"
        )
        (self.root / "scripts/set-session-scope.sh").write_text("#!/usr/bin/env bash\nexit 0\n")
        return self.root / "scripts/program-bootstrap-children.py"

    def test_bootstrap_cli_exits_zero_without_tmux(self) -> None:
        cli = self._install_bootstrap_cli()
        env = {**os.environ, "WORKSPACE_ROOT": str(self.root)}
        env.pop("TMUX", None)
        result = subprocess.run(
            [sys.executable, str(cli), self.parent, "--approve"],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("child sessions were created", result.stdout)


if __name__ == "__main__":
    unittest.main()
