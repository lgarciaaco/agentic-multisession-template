"""Monitor helpers for program orchestrator parent sessions."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from program_state import load_program
from session_binding import validate_codename
from workflow_plan import load_workflow
from workflow_resume import workflow_next_action

GATE_PHASES = frozenset({"brief_review", "plan_user_review"})


def _mtime_iso(path: Path) -> str | None:
    if not path.exists():
        return None
    ts = path.stat().st_mtime
    return datetime.fromtimestamp(ts, tz=timezone.utc).replace(microsecond=0).isoformat()


def _pending_gate(phase: str) -> str | None:
    if phase in GATE_PHASES:
        return phase
    return None


def child_snapshot(root: Path, codename: str) -> dict[str, Any]:
    session_dir = root / "sessions" / codename
    workflow_path = session_dir / "workflow.json"
    session_path = session_dir / "session.json"
    snapshot: dict[str, Any] = {
        "codename": codename,
        "phase": None,
        "pending_gate": None,
        "resume_hint": None,
        "last_updated": _mtime_iso(workflow_path) or _mtime_iso(session_path),
        "tasks_with_pr": [],
        "error": None,
    }
    if not workflow_path.exists():
        snapshot["error"] = "missing workflow.json"
        return snapshot
    try:
        workflow = load_workflow(session_dir)
    except (ValueError, OSError) as exc:
        snapshot["error"] = str(exc)
        return snapshot
    phase = str(workflow.get("phase") or "unknown")
    snapshot["phase"] = phase
    snapshot["pending_gate"] = _pending_gate(phase)
    snapshot["resume_hint"] = workflow_next_action(workflow)
    snapshot["last_updated"] = _mtime_iso(workflow_path)

    if session_path.exists():
        try:
            session_doc = json.loads(session_path.read_text())
        except json.JSONDecodeError:
            session_doc = {}
        for task in session_doc.get("tasks") or []:
            if isinstance(task, dict) and task.get("pr"):
                snapshot["tasks_with_pr"].append(
                    {
                        "id": task.get("id"),
                        "pr": task.get("pr"),
                        "status": task.get("status"),
                    }
                )
    return snapshot


def monitor_program(root: Path, parent_codename: str) -> dict[str, Any]:
    parent = validate_codename(parent_codename)
    session_dir = root / "sessions" / parent
    program = load_program(session_dir)
    children = [
        child_snapshot(root, validate_codename(str(entry.get("codename", ""))))
        for entry in program.get("active_children") or []
    ]
    return {
        "parent": parent,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "decomposition_approved": program.get("decomposition_approved"),
        "children": children,
        "gate_queue": program.get("gate_queue") or [],
    }
