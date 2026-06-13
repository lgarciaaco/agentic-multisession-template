"""Tmux helpers for opening program-orchestrator child session tabs."""

from __future__ import annotations

import os
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from session_binding import (
    _index_sessions,
    _pane_path_under_hub_root,
    _run_tmux,
    agent_launcher_name,
    is_active_session,
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


def _pane_live(pane_id: str) -> bool:
    result = _run_tmux("display-message", "-p", "-t", pane_id, "#{pane_id}")
    if not result:
        return False
    return bool(result.stdout.strip())


def _pane_window_index(pane_id: str) -> str | None:
    result = _run_tmux("display-message", "-p", "-t", pane_id, "#{window_index}")
    if not result:
        return None
    value = result.stdout.strip()
    return value or None


def _path_under_hub(root: Path, pane_path: str) -> bool:
    if not pane_path or not pane_path.strip():
        return False
    try:
        resolved = Path(pane_path).expanduser().resolve()
        return resolved == root.resolve() or root.resolve() in resolved.parents
    except OSError:
        return False


def _list_session_panes(root: Path) -> list[dict[str, str]]:
    if not in_tmux():
        return []
    opt = tmux_pane_option()
    result = _run_tmux(
        "list-panes",
        "-s",
        "-F",
        f"#{{pane_id}}\t#{{@{opt}}}\t#{{pane_current_path}}\t#{{window_name}}\t#{{window_index}}",
    )
    if not result:
        return []
    hub = root.resolve()
    panes: list[dict[str, str]] = []
    for line in result.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 5:
            continue
        pane_id, codename, pane_path, window_name, window_index = parts[:5]
        if not _path_under_hub(hub, pane_path):
            continue
        panes.append(
            {
                "pane_id": pane_id.strip(),
                "codename": codename.strip(),
                "window_name": window_name.strip(),
                "window_index": window_index.strip(),
            }
        )
    return panes


def _pane_codename_and_path(pane_id: str) -> tuple[str, str]:
    opt = tmux_pane_option()
    result = _run_tmux(
        "display-message",
        "-p",
        "-t",
        pane_id,
        f"#{{@{opt}}}\t#{{pane_current_path}}",
    )
    if not result:
        return "", ""
    parts = result.stdout.split("\t", 1)
    codename = parts[0].strip() if parts else ""
    pane_path = parts[1].strip() if len(parts) > 1 else ""
    return codename, pane_path


def _pane_matches_child(
    root: Path,
    pane_id: str,
    codename: str,
) -> bool:
    if not _pane_live(pane_id):
        return False
    pane_codename, pane_path = _pane_codename_and_path(pane_id)
    return pane_codename == codename and _path_under_hub(root, pane_path)


def resolve_child_window(
    root: Path,
    codename: str,
    *,
    pane_id: str | None = None,
    window_label: str | None = None,
) -> str | None:
    """Resolve a child tmux window target for kill-window."""
    name = validate_codename(codename)
    if pane_id and _pane_matches_child(root, pane_id, name):
        return pane_id

    label = (window_label or tmux_window_label(name) or "").strip()
    panes = _list_session_panes(root)
    for pane in panes:
        if pane["codename"] == name:
            return pane["pane_id"]
    if label:
        for pane in panes:
            if pane["window_name"] == label:
                return pane["pane_id"]
    return None


def is_safe_child_close_target(
    parent_codename: str,
    child_codename: str,
    pane_id: str,
    *,
    root: Path | None = None,
) -> bool:
    """Reject parent codename and the parent's current tmux window."""
    parent = validate_codename(parent_codename)
    child = validate_codename(child_codename)
    if child == parent:
        return False
    if not _pane_live(pane_id):
        return False
    if root is not None and not _pane_matches_child(root, pane_id, child):
        return False
    parent_window = _current_window_index()
    target_window = _pane_window_index(pane_id)
    if parent_window is not None and target_window == parent_window:
        return False
    return True


def close_child_window(pane_id: str) -> bool:
    """Kill the tmux window containing pane_id. Returns False when absent or tmux fails."""
    if not pane_id or not _pane_live(pane_id):
        return False
    return _run_tmux("kill-window", "-t", pane_id) is not None


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


def list_hub_panes(root: Path) -> list[dict[str, str]]:
    """List tmux panes under hub_root with pane_id and bound codename.

    Shared lookup surface for program routing (pc2) and tab cleanup (pc3).
    """
    if not in_tmux():
        return []
    opt = tmux_pane_option()
    result = _run_tmux(
        "list-panes",
        "-s",
        "-F",
        f"#{{pane_id}}\t#{{@{opt}}}\t#{{pane_current_path}}",
    )
    if not result:
        return []
    hub = root.resolve()
    index_sessions = _index_sessions(hub)
    panes: list[dict[str, str]] = []
    for line in result.stdout.splitlines():
        parts = line.split("\t", 2)
        if len(parts) < 3:
            continue
        pane_id, codename, pane_path = parts[0].strip(), parts[1].strip(), parts[2].strip()
        if not codename or not _pane_path_under_hub_root(hub, pane_path):
            continue
        if not is_active_session(hub, codename, index_sessions.get(codename, {})):
            continue
        panes.append({"pane_id": pane_id, "codename": codename, "path": pane_path})
    return panes

def resolve_child_pane(
    root: Path,
    codename: str,
    stored_pane_id: str | None = None,
) -> str:
    """Return a live pane id for codename; prefer stored id when still valid."""
    name = validate_codename(codename)
    if stored_pane_id and _pane_matches_child(root, stored_pane_id, name):
        return stored_pane_id
    for pane in list_hub_panes(root):
        if pane["codename"] == name:
            return pane["pane_id"]
    raise ValueError(f"no tmux pane found for child {name!r}")


def send_to_child_pane(pane_id: str, text: str, *, submit: bool = True) -> None:
    """Send text to a child pane; append Enter when submit is True."""
    message = text.strip()
    if not message:
        raise ValueError("message must not be empty")
    if _run_tmux("send-keys", "-l", "-t", pane_id, message) is None:
        raise RuntimeError(f"tmux send-keys failed for pane {pane_id!r}")
    if submit:
        if _run_tmux("send-keys", "-t", pane_id, "C-m") is None:
            raise RuntimeError(f"tmux send-keys failed for pane {pane_id!r}")


def persist_child_panes(
    program: dict[str, Any],
    windows: list[ChildWindow],
) -> dict[str, Any]:
    """Merge bootstrap window records into program active_children."""
    by_codename = {window.codename: window for window in windows}
    active = list(program.get("active_children") or [])
    for entry in active:
        codename = entry.get("codename")
        window = by_codename.get(codename)
        if window is None:
            continue
        entry["pane_id"] = window.pane_id
        if window.window_label:
            entry["window_label"] = window.window_label
    program["active_children"] = active
    return program


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
        send_to_child_pane(window.pane_id, cmd, submit=True)


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
