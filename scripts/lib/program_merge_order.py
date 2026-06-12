"""Merge order helpers for program orchestrator."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from program_state import load_program
from session_binding import validate_codename

PR_RE = re.compile(r"/pull/(\d+)")


def _task_rows(session_dir: Path) -> list[dict[str, Any]]:
    path = session_dir / "session.json"
    if not path.exists():
        return []
    doc = json.loads(path.read_text())
    rows: list[dict[str, Any]] = []
    for task in doc.get("tasks") or []:
        if not isinstance(task, dict) or not task.get("pr"):
            continue
        pr = str(task["pr"])
        match = PR_RE.search(pr)
        rows.append(
            {
                "id": task.get("id"),
                "pr": pr,
                "pr_number": int(match.group(1)) if match else None,
                "status": task.get("status"),
            }
        )
    return rows


def merge_order(root: Path, parent_codename: str) -> dict[str, Any]:
    parent = validate_codename(parent_codename)
    program = load_program(root / "sessions" / parent)
    active = program.get("active_children") or []
    ordered_hint = (program.get("merge_hints") or {}).get("ordered_children") or []

    entries: list[dict[str, Any]] = []
    for child in active:
        codename = validate_codename(str(child.get("codename", "")))
        session_dir = root / "sessions" / codename
        entries.append(
            {
                "codename": codename,
                "status": child.get("status"),
                "tasks": _task_rows(session_dir),
            }
        )

    if len(entries) <= 1:
        sequence = [entry["codename"] for entry in entries]
        notes = ["single active child — trivial merge order"]
    else:
        hint_index = {name: idx for idx, name in enumerate(ordered_hint)}
        entries.sort(key=lambda row: (hint_index.get(row["codename"], 999), row["codename"]))
        sequence = [entry["codename"] for entry in entries]
        notes = ["default ordered by merge_hints then codename"]

    return {
        "parent": parent,
        "merge_sequence": sequence,
        "children": entries,
        "notes": notes,
    }
