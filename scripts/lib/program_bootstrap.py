"""Bootstrap program child sessions and open tmux tabs when available."""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from program_child_tabs import (
    DEFAULT_WORKFLOW_PROMPT,
    child_window_records,
    format_manual_child_steps,
    in_tmux,
    launch_child_agents,
    open_child_windows,
)
from program_state import load_program, save_program
from session_binding import validate_codename


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _run_script(root: Path, script: str, *args: str) -> str:
    path = root / "scripts" / script
    env = {**os.environ, "WORKSPACE_ROOT": str(root)}
    result = subprocess.run(
        [str(path), *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"{script} failed: {stderr}")
    return result.stdout.strip()


def _bootstrap_child_metadata(
    root: Path,
    row: dict[str, Any],
) -> dict[str, Any]:
    suggested = row.get("suggested_codename")
    title = (row.get("title") or "").strip() or None
    goal = (row.get("goal") or "").strip()

    if suggested:
        codename = _run_script(root, "new-session.sh", str(suggested), title or "")
    else:
        codename = _run_script(root, "new-session.sh", "", title or "")

    if goal:
        _run_script(root, "set-session-scope.sh", codename, "--goal", goal)

    return {
        "codename": validate_codename(codename),
        "title": title or codename,
        "goal": goal,
        "child_id": row.get("id"),
    }


def bootstrap_children(
    root: Path,
    parent: str,
    *,
    approve: bool = False,
    workflow_prompt: str = DEFAULT_WORKFLOW_PROMPT,
) -> dict[str, Any]:
    parent_name = validate_codename(parent)
    session_dir = root / "sessions" / parent_name
    program = load_program(session_dir, codename=parent_name)

    if not program.get("decomposition_approved") and not approve:
        raise ValueError(
            "decomposition not approved — user must say 'approve decomposition' "
            "or pass --approve"
        )

    proposed = program.get("proposed_children") or []
    if not proposed:
        raise ValueError("program.json has no proposed_children — run program-decompose.py first")

    bootstrapped: list[dict[str, Any]] = []
    program["decomposition_approved"] = True
    started = _utc_now_iso()
    existing_children = list(program.get("active_children") or [])
    existing_codenames = {
        str(item.get("codename"))
        for item in existing_children
        if item.get("codename")
    }
    initial_existing = set(existing_codenames)
    program["active_children"] = existing_children

    for row in proposed:
        suggested = row.get("suggested_codename")
        if suggested:
            codename_key = validate_codename(str(suggested))
            if codename_key in existing_codenames:
                bootstrapped.append(
                    {
                        "codename": codename_key,
                        "title": (row.get("title") or "").strip() or codename_key,
                        "goal": (row.get("goal") or "").strip(),
                        "child_id": row.get("id"),
                    }
                )
                continue

        child = _bootstrap_child_metadata(root, row)
        bootstrapped.append(child)
        if child["codename"] not in existing_codenames:
            program["active_children"].append(
                {
                    "codename": child["codename"],
                    "status": "running",
                    "started": started,
                }
            )
            existing_codenames.add(child["codename"])
            save_program(session_dir, program, codename=parent_name)

    result: dict[str, Any] = {
        "parent": parent_name,
        "children": bootstrapped,
        "tmux": False,
        "windows": [],
    }

    if in_tmux():
        new_codenames = [
            child["codename"]
            for child in bootstrapped
            if child["codename"] not in initial_existing
        ]
        if new_codenames:
            windows = open_child_windows(root, new_codenames)
            launch_child_agents(root, windows, prompt=workflow_prompt)
            result["tmux"] = True
            result["windows"] = child_window_records(windows)
    else:
        print(format_manual_child_steps(bootstrapped), file=sys.stdout)

    return result
