"""Monitor helpers for program orchestrator parent sessions."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from program_child_tabs import (
    close_child_window,
    in_tmux,
    is_safe_child_close_target,
    resolve_child_window,
)
from gate_metadata_registry import (
    gate_artifact_path,
    gate_column_short_label,
)
from program_state import GATE_PHASES, load_program, save_program
from session_binding import validate_codename
from workflow_plan import load_workflow, parse_action_plan_tasks
from workflow_resume import workflow_next_action


def _mtime_iso(path: Path) -> str | None:
    if not path.exists():
        return None
    ts = path.stat().st_mtime
    return datetime.fromtimestamp(ts, tz=timezone.utc).replace(microsecond=0).isoformat()


def _pending_gate(phase: str) -> str | None:
    if phase in GATE_PHASES:
        return phase
    return None


def gate_column_short(pending_gate: str | None) -> str:
    """Map workflow gate phase to slim parent chat column."""
    return gate_column_short_label(pending_gate)


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


def _parse_files_areas(plan_text: str) -> list[str]:
    files_areas: list[str] = []
    in_files = False
    for line in plan_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## Files"):
            in_files = True
            continue
        if in_files and stripped.startswith("## "):
            break
        if not in_files:
            continue
        if stripped.startswith("**") and stripped.endswith(":**"):
            files_areas.append(stripped.rstrip(":"))
        elif stripped.startswith("- `"):
            match = re.match(r"- `([^`]+)`", stripped)
            if match:
                files_areas.append(match.group(1))
    return files_areas


def _parse_action_plan_summary(plan_path: Path) -> dict[str, Any] | None:
    """Build sibling plan-gate summary via shared action-plan task parser."""
    if not plan_path.is_file():
        return None
    text = plan_path.read_text(encoding="utf-8")
    tasks: list[dict[str, str]] = []
    try:
        parsed = parse_action_plan_tasks(text)
        tasks = [{"id": row["id"], "summary": row["title"]} for row in parsed]
    except ValueError:
        pass
    files_areas = _parse_files_areas(text)
    if not tasks and not files_areas:
        return None
    return {"tasks": tasks, "files_areas": files_areas}


def sibling_program_context(
    root: Path,
    program: dict[str, Any],
    exclude_codename: str,
    *,
    pending_gate: str | None = None,
) -> list[dict[str, Any]]:
    """Read-only sibling scope for cross-child gate review (excludes reviewed child)."""
    exclude = validate_codename(exclude_codename)
    entries: list[dict[str, Any]] = []
    for row in program.get("active_children") or []:
        codename = validate_codename(str(row.get("codename", "")))
        if codename == exclude:
            continue
        entry: dict[str, Any] = {
            "codename": codename,
            "decomposition_scope": _proposed_scope_for_child(program, codename),
            "child_scope": _child_scope_from_session(root, codename),
        }
        if pending_gate == "plan_user_review":
            plan_path = (
                root / "sessions" / codename / gate_artifact_path("plan_user_review")
            )
            summary = _parse_action_plan_summary(plan_path)
            if summary:
                entry["plan_summary"] = summary
        entries.append(entry)
    return entries


def child_gate_review(
    root: Path,
    codename: str,
    gate: str,
    *,
    program: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return read-only review context for a child at a parent gate."""
    if gate not in GATE_PHASES:
        raise ValueError(f"unsupported gate for review: {gate!r}")
    name = validate_codename(codename)
    artifact_rel = gate_artifact_path(gate)
    session_dir = root / "sessions" / name
    artifact_path = session_dir / artifact_rel
    review: dict[str, Any] = {
        "gate": gate,
        "artifact_path": f"sessions/{name}/{artifact_rel}",
        "artifact_present": artifact_path.is_file(),
        "decomposition_scope": _proposed_scope_for_child(program, name) if program else None,
        "child_scope": _child_scope_from_session(root, name),
    }
    if program is not None:
        review["sibling_program_context"] = sibling_program_context(
            root, program, name, pending_gate=gate
        )
    return review


def program_parent_next_action(report: dict[str, Any]) -> str:
    """Mandatory parent conductor action — always review at child gates."""
    pending = [child for child in report.get("children") or [] if child.get("pending_gate")]
    cross_child = (
        " Review cross-child overlap via gate_review.sibling_program_context; "
        "full assessments in artifacts/program-status.md."
    )
    if pending:
        if len(pending) == 1:
            child = pending[0]
            gate = str(child["pending_gate"])
            codename = str(child["codename"])
            review = child.get("gate_review") or {}
            artifact = review.get("artifact_path") or gate_artifact_path(gate)
            return (
                f"Review child `{codename}` `{artifact}` against decomposition scope; "
                "route accept, reopen, or inbox correction after reading program-status.md"
                f"{cross_child}"
            )
        names = ", ".join(f"`{c['codename']}`" for c in pending)
        return (
            f"Review gate artifacts for {names} against decomposition scope; "
            f"route per child after reading program-status.md{cross_child}"
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


def _child_workflow_phase(root: Path, codename: str) -> str | None:
    session_dir = root / "sessions" / codename
    workflow_path = session_dir / "workflow.json"
    if not workflow_path.exists():
        return None
    try:
        workflow = load_workflow(session_dir)
    except (ValueError, OSError):
        return None
    phase = workflow.get("phase")
    return str(phase) if phase is not None else None


def cleanup_completed_children(
    root: Path,
    parent_codename: str,
    program: dict[str, Any],
) -> dict[str, Any]:
    """Close completed child tabs and mark active_children status on the monitor pass."""
    parent = validate_codename(parent_codename)
    session_dir = root / "sessions" / parent
    changed = False

    for entry in program.get("active_children") or []:
        if not isinstance(entry, dict):
            continue
        codename = str(entry.get("codename", "")).strip()
        if not codename:
            continue
        phase = _child_workflow_phase(root, codename)
        if phase != "completed":
            continue

        if entry.get("status") != "completed":
            entry["status"] = "completed"
            changed = True

        if in_tmux():
            raw_pane = entry.get("pane_id")
            pane_id = (
                str(raw_pane).strip()
                if isinstance(raw_pane, str) and str(raw_pane).strip()
                else None
            )
            raw_label = entry.get("window_label")
            window_label = (
                str(raw_label).strip()
                if isinstance(raw_label, str) and str(raw_label).strip()
                else None
            )
            target = resolve_child_window(
                root,
                codename,
                pane_id=pane_id,
                window_label=window_label,
            )
            if target and is_safe_child_close_target(
                parent, codename, target, root=root
            ):
                close_child_window(target)

    if changed:
        save_program(session_dir, program, codename=parent)
    return program


def monitor_program(root: Path, parent_codename: str) -> dict[str, Any]:
    parent = validate_codename(parent_codename)
    session_dir = root / "sessions" / parent
    program = load_program(session_dir)
    program = cleanup_completed_children(root, parent, program)
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


def _one_line_next(child: dict[str, Any], review_payload: dict[str, Any] | None) -> str:
    if review_payload and review_payload.get("next"):
        return str(review_payload["next"]).replace("|", "/").replace("\n", " ").strip()
    if child.get("error"):
        return f"error: {child['error']}"
    hint = child.get("resume_hint") or "—"
    return str(hint).replace("|", "/").replace("\n", " ").strip()


def render_program_status_markdown(
    report: dict[str, Any],
    *,
    child_reviews: dict[str, dict[str, str]] | None = None,
) -> str:
    """Render artifacts/program-status.md body from monitor report and optional Task reviews."""
    reviews = child_reviews or {}
    lines = [
        f"# Program status — {report['parent']}",
        "",
        f"Generated: {report['generated_at']}",
        f"Decomposition approved: {report.get('decomposition_approved')}",
        "",
        "## Children",
        "",
        "| Child | Phase | Pending gate | Updated | Resume |",
        "|-------|-------|--------------|---------|--------|",
    ]

    for child in report.get("children") or []:
        gate = child.get("pending_gate") or "—"
        phase = child.get("phase") or "—"
        updated = child.get("last_updated") or "—"
        codename = str(child["codename"])
        hint = _one_line_next(child, reviews.get(codename))
        lines.append(f"| `{codename}` | {phase} | {gate} | {updated} | {hint} |")

    lines.extend(["", "## Gate review (parent)", ""])
    lines.append(f"**Next:** {report.get('parent_next_action') or '—'}")
    lines.append("")
    pending = [c for c in report.get("children") or [] if c.get("pending_gate")]
    if not pending:
        lines.append("_No child gates pending parent review._")
    else:
        for child in pending:
            codename = str(child["codename"])
            review = child.get("gate_review") or {}
            artifact = review.get("artifact_path") or "—"
            present = "present" if review.get("artifact_present") else "missing"
            lines.append(f"### `{codename}` — `{child.get('pending_gate')}`")
            lines.append(f"- **Artifact:** `{artifact}` ({present})")
            decomp = review.get("decomposition_scope") or {}
            if decomp.get("title") or decomp.get("goal"):
                title = decomp.get("title") or "—"
                goal = (decomp.get("goal") or "—").replace("\n", " ")
                lines.append(f"- **Decomposition scope:** {title} — {goal}")
            scope = review.get("child_scope") or {}
            if scope.get("title") or scope.get("goal"):
                title = scope.get("title") or "—"
                goal = (scope.get("goal") or "—").replace("\n", " ")
                lines.append(f"- **Child session scope:** {title} — {goal}")
            siblings = review.get("sibling_program_context") or []
            if siblings:
                codes = ", ".join(f"`{s['codename']}`" for s in siblings)
                lines.append(f"- **Sibling context:** {len(siblings)} active ({codes})")
                for sibling in siblings:
                    sib_code = sibling.get("codename") or "—"
                    sib_decomp = sibling.get("decomposition_scope") or {}
                    sib_title = sib_decomp.get("title") or "—"
                    lines.append(f"  - `{sib_code}`: {sib_title}")
                    plan_summary = sibling.get("plan_summary")
                    if plan_summary:
                        task_bits = [
                            f"{t.get('id')}: {t.get('summary')}"
                            for t in plan_summary.get("tasks") or []
                        ]
                        if task_bits:
                            lines.append(f"    - tasks: {'; '.join(task_bits)}")
                        areas = plan_summary.get("files_areas") or []
                        if areas:
                            lines.append(f"    - files/areas: {', '.join(areas[:5])}")

            payload = reviews.get(codename) or {}
            if payload.get("parent_assessment"):
                lines.append("")
                lines.append("**Parent assessment**")
                lines.append("")
                lines.append(str(payload["parent_assessment"]).strip())
            if payload.get("cross_child_check"):
                lines.append("")
                lines.append("**Cross-child check**")
                lines.append("")
                lines.append(str(payload["cross_child_check"]).strip())
            if payload.get("child_agent_action"):
                lines.append("")
                lines.append("**Child agent action**")
                lines.append("")
                lines.append(str(payload["child_agent_action"]).strip())

    if reviews:
        lines.extend(["", "## Child reviewer synthesis", ""])
        for child in report.get("children") or []:
            codename = str(child["codename"])
            payload = reviews.get(codename)
            if not payload:
                continue
            lines.append(f"### `{codename}`")
            if payload.get("next"):
                lines.append(f"- **Next:** {payload['next']}")
            if payload.get("parent_assessment"):
                lines.append("")
                lines.append("**Parent assessment**")
                lines.append("")
                lines.append(str(payload["parent_assessment"]).strip())
            if payload.get("cross_child_check"):
                lines.append("")
                lines.append("**Cross-child check**")
                lines.append("")
                lines.append(str(payload["cross_child_check"]).strip())
            if payload.get("child_agent_action"):
                lines.append("")
                lines.append("**Child agent action**")
                lines.append("")
                lines.append(str(payload["child_agent_action"]).strip())
            lines.append("")

    lines.extend(["", "## Gate queue", ""])
    queue = report.get("gate_queue") or []
    if not queue:
        lines.append("_No queued gate events._")
    else:
        for item in queue:
            lines.append(
                f"- `{item.get('child_codename')}` @ `{item.get('gate')}` handled={item.get('handled')}"
            )

    return "\n".join(lines).rstrip() + "\n"
