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

GATE_ARTIFACT = {
    "brief_review": "artifacts/problem-brief.md",
    "plan_user_review": "artifacts/action-plan.md",
}


def _mtime_iso(path: Path) -> str | None:
    if not path.exists():
        return None
    ts = path.stat().st_mtime
    return datetime.fromtimestamp(ts, tz=timezone.utc).replace(microsecond=0).isoformat()


def _pending_gate(phase: str) -> str | None:
    if phase in GATE_PHASES:
        return phase
    return None


def _child_scope_from_session(root: Path, codename: str) -> dict[str, str | None]:
    name = validate_codename(codename)
    session_dir = root / "sessions" / name
    title: str | None = None
    goal: str | None = None
    session_path = session_dir / "session.json"
    if session_path.exists():
        try:
            doc = json.loads(session_path.read_text())
            raw_title = doc.get("title")
            if isinstance(raw_title, str) and raw_title.strip():
                title = raw_title.strip()
        except json.JSONDecodeError:
            pass
    try:
        from session_binding import _goal_text_from_tasks

        goal_text = _goal_text_from_tasks(session_dir)
        if goal_text:
            goal = goal_text
    except (ImportError, ValueError, OSError):
        pass
    return {"title": title, "goal": goal}


def _proposed_scope_for_child(program: dict[str, Any], codename: str) -> dict[str, Any] | None:
    for row in program.get("proposed_children") or []:
        if row.get("suggested_codename") == codename:
            return {
                "id": row.get("id"),
                "title": row.get("title"),
                "goal": row.get("goal"),
            }
    active = [entry["codename"] for entry in program.get("active_children") or []]
    proposed = program.get("proposed_children") or []
    try:
        idx = active.index(codename)
    except ValueError:
        return None
    if idx >= len(proposed):
        return None
    row = proposed[idx]
    return {
        "id": row.get("id"),
        "title": row.get("title"),
        "goal": row.get("goal"),
    }


def child_gate_review(
    root: Path,
    codename: str,
    gate: str,
    *,
    program: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return read-only review context for a child at a parent gate."""
    if gate not in GATE_ARTIFACT:
        raise ValueError(f"unsupported gate for review: {gate!r}")
    name = validate_codename(codename)
    artifact_rel = GATE_ARTIFACT[gate]
    session_dir = root / "sessions" / name
    artifact_path = session_dir / artifact_rel
    return {
        "gate": gate,
        "artifact_path": f"sessions/{name}/{artifact_rel}",
        "artifact_present": artifact_path.is_file(),
        "decomposition_scope": _proposed_scope_for_child(program, name) if program else None,
        "child_scope": _child_scope_from_session(root, name),
    }


def program_parent_next_action(report: dict[str, Any]) -> str:
    """Mandatory parent conductor action — always review at child gates."""
    pending = [child for child in report.get("children") or [] if child.get("pending_gate")]
    if pending:
        if len(pending) == 1:
            child = pending[0]
            gate = str(child["pending_gate"])
            codename = str(child["codename"])
            review = child.get("gate_review") or {}
            artifact = review.get("artifact_path") or GATE_ARTIFACT.get(gate, "gate artifact")
            return (
                f"Review child `{codename}` `{artifact}` against decomposition scope; "
                "present assessment, then route accept, reopen, or inbox correction"
            )
        names = ", ".join(f"`{c['codename']}`" for c in pending)
        return (
            f"Review gate artifacts for {names} against decomposition scope; "
            "present assessment per child before routing gate commands"
        )
    if not report.get("decomposition_approved"):
        return "Ingest → decompose → present proposed_children; block until approve decomposition"
    return "Monitor children (program-monitor.py); no gate review pending"


def child_snapshot(
    root: Path,
    codename: str,
    *,
    program: dict[str, Any] | None = None,
) -> dict[str, Any]:
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
        "gate_review": None,
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
    pending_gate = _pending_gate(phase)
    snapshot["pending_gate"] = pending_gate
    snapshot["resume_hint"] = workflow_next_action(workflow)
    snapshot["last_updated"] = _mtime_iso(workflow_path)
    if pending_gate:
        snapshot["gate_review"] = child_gate_review(
            root, codename, pending_gate, program=program
        )

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
        child_snapshot(
            root,
            validate_codename(str(entry.get("codename", ""))),
            program=program,
        )
        for entry in program.get("active_children") or []
    ]
    report: dict[str, Any] = {
        "parent": parent,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "decomposition_approved": program.get("decomposition_approved"),
        "plan_path": program.get("plan_path"),
        "children": children,
        "gate_queue": program.get("gate_queue") or [],
    }
    report["parent_next_action"] = program_parent_next_action(report)
    return report
