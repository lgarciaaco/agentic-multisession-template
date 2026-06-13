"""Tmux helpers for opening program-orchestrator child session tabs."""

from __future__ import annotations

import os
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from session_binding import (
    _run_tmux,
    agent_launcher_name,
    tmux_pane_option,
    tmux_window_label,
    validate_codename,
)
from git_noninteractive import NONINTERACTIVE_EDITOR_ENV

DEFAULT_WORKFLOW_PROMPT = "/workflow-orchestrator"
NONINTERACTIVE_EDITOR_EXPORTS = " ".join(
    f"{k}={v}" for k, v in NONINTERACTIVE_EDITOR_ENV.items()
)


@dataclass(frozen=True)
class ChildWindow:
    codename: str
    pane_id: str
    window_label: str


def in_tmux() -> bool:
    return bool(os.environ.get("TMUX"))


def _current_window_index() -> str | None:
    result = _run_tmux("display-message", "-p", "#{window_index}")
    if not result:
        return None
    value = result.stdout.strip()
    return value or None


def _select_window(index: str) -> None:
    _run_tmux("select-window", "-t", index)


def _set_pane_codename(pane_id: str, codename: str) -> bool:
    option = tmux_pane_option()
    return _run_tmux(
        "set-option",
        "-p",
        "-t",
        pane_id,
        f"@{option}",
        codename,
    ) is not None


def _rename_pane_window(pane_id: str, codename: str) -> bool:
    label = tmux_window_label(codename)
    if not label:
        return False
    return _run_tmux("rename-window", "-t", pane_id, label) is not None


def open_child_windows(root: Path, codenames: list[str]) -> list[ChildWindow]:
    """Create one detached tmux window per child; keep the parent window selected."""
    if not in_tmux():
        return []

    parent_window = _current_window_index()
    records: list[ChildWindow] = []

    for raw in codenames:
        name = validate_codename(raw)
        result = _run_tmux(
            "new-window",
            "-d",
            "-P",
            "-F",
            "#{pane_id}",
            "-c",
            str(root),
        )
        if not result:
            continue
        pane_id = result.stdout.strip()
        if not pane_id:
            continue
        _set_pane_codename(pane_id, name)
        _rename_pane_window(pane_id, name)
        records.append(
            ChildWindow(
                codename=name,
                pane_id=pane_id,
                window_label=tmux_window_label(name),
            )
        )

    if parent_window is not None:
        _select_window(parent_window)
    return records


def _child_agent_launch_cmd(hub: str, launcher: str, *, prompt: str) -> str:
    """Shell command for starting a child agent with non-interactive editor env."""
    if prompt and prompt != DEFAULT_WORKFLOW_PROMPT:
        agent = f"{shlex.quote(launcher)} --reuse {shlex.quote(prompt)}"
    else:
        agent = f"{shlex.quote(launcher)} --reuse --workflow"
    return (
        f"cd {shlex.quote(hub)} && "
        f"{NONINTERACTIVE_EDITOR_EXPORTS} "
        f"{agent}"
    )


def launch_child_agents(
    root: Path,
    windows: list[ChildWindow],
    *,
    prompt: str = DEFAULT_WORKFLOW_PROMPT,
) -> None:
    """Start the hub launcher in each child pane with --reuse and an initial prompt."""
    launcher = agent_launcher_name()
    hub = str(root)
    for window in windows:
        cmd = _child_agent_launch_cmd(hub, launcher, prompt=prompt)
        _run_tmux("send-keys", "-t", window.pane_id, cmd, "C-m")


def child_window_records(windows: list[ChildWindow]) -> list[dict[str, Any]]:
    return [
        {
            "codename": window.codename,
            "pane_id": window.pane_id,
            "window_label": window.window_label,
        }
        for window in windows
    ]


def format_manual_child_steps(
    children: list[dict[str, Any]],
    *,
    launcher: str | None = None,
) -> str:
    """Printable instructions when TMUX is unset."""
    cmd = launcher or agent_launcher_name()
    lines = [
        "TMUX is not set — child sessions were created; open each child manually:",
        "",
    ]
    for child in children:
        codename = child.get("codename", "")
        title = child.get("title") or codename
        lines.append(f"## {codename} — {title}")
        lines.append(
            f"# New tmux tab: {NONINTERACTIVE_EDITOR_EXPORTS} "
            f"{cmd} --reuse --workflow"
        )
        lines.append(f"# Or bind first: ./scripts/bind-session.sh {codename}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
