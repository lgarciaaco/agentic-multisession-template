"""Route parent program feedback to child tmux panes via send-keys."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from gate_command_registry import (
    ACCEPT_BRIEF,
    ACCEPT_PLAN,
    allowed_route_messages,
    classify_gate_command,
    is_allowed_route_message,
    normalize_route_message,
)
from program_child_tabs import in_tmux, resolve_child_pane, send_to_child_pane
from program_state import GATE_PHASES, load_program, save_program
from session_binding import resolve_codename, sanitize_goal_text, validate_codename
from workflow_plan import load_workflow

DEFAULT_ROUTE_COOLDOWN_SECONDS = 300
CORRECTION_PHASES = frozenset({"brief_review", "plan_user_review"})


@dataclass(frozen=True)
class RouteResult:
    sent: bool
    payload: str
    skip_reason: str | None = None


def _parse_iso_timestamp(value: str | None) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _dedupe_skip_reason(
    entry: dict[str, Any],
    normalized_message: str,
    *,
    gate_command: bool = False,
    cooldown_seconds: int = DEFAULT_ROUTE_COOLDOWN_SECONDS,
) -> str | None:
    last_at = entry.get("last_routed_at")
    last_msg = entry.get("last_routed_message")
    if not isinstance(last_at, str) or not isinstance(last_msg, str):
        return None
    if (
        normalize_route_message(last_msg, gate_command=gate_command)
        != normalized_message
    ):
        return None
    parsed = _parse_iso_timestamp(last_at)
    if parsed is None:
        return None
    elapsed = (datetime.now(timezone.utc) - parsed).total_seconds()
    if elapsed < cooldown_seconds:
        return f"duplicate message within {cooldown_seconds}s cooldown"
    return None


def _gate_already_accepted_skip(
    workflow: dict[str, Any],
    gate: str,
    message: str,
) -> str | None:
    action = classify_gate_command(gate, message)
    gates = workflow.get("gates") or {}
    if action == ACCEPT_BRIEF and gates.get("brief_accepted"):
        return "brief gate already accepted"
    if action == ACCEPT_PLAN and gates.get("plan_user_accepted"):
        return "plan gate already accepted"
    return None


def _correction_phase_skip(phase: str | None) -> str | None:
    if phase not in CORRECTION_PHASES:
        return f"child phase is {phase!r}, not brief_review or plan_user_review"
    return None


def _gate_feedback_skip_reason(
    workflow: dict[str, Any],
    entry: dict[str, Any],
    gate: str,
    message: str,
    *,
    force: bool = False,
) -> str | None:
    """Return skip reason when gate feedback is not routable; None when guards pass."""
    if not force:
        accepted_skip = _gate_already_accepted_skip(workflow, gate, message)
        if accepted_skip:
            return accepted_skip
        normalized = normalize_route_message(message.strip(), gate_command=True)
        dedupe = _dedupe_skip_reason(entry, normalized, gate_command=True)
        if dedupe:
            return dedupe
    return None


def _correction_skip_reason(
    workflow: dict[str, Any],
    entry: dict[str, Any],
    message: str,
    *,
    force: bool = False,
) -> str | None:
    """Return skip reason when correction is not routable; None when guards pass."""
    phase = str(workflow.get("phase") or "unknown")
    if not force:
        phase_skip = _correction_phase_skip(phase)
        if phase_skip:
            return phase_skip
        normalized = normalize_route_message(message, gate_command=False)
        dedupe = _dedupe_skip_reason(entry, normalized, gate_command=False)
        if dedupe:
            return dedupe
    return None


def _require_bound_parent(root: Path, parent_name: str) -> None:
    bound, _ = resolve_codename(root)
    if bound != parent_name:
        if bound is None:
            raise ValueError(
                f"route_feedback requires bound session {parent_name!r}, not unbound caller"
            )
        raise ValueError(
            f"route_feedback requires bound session {parent_name!r}, not {bound!r}"
        )


def _require_tmux() -> None:
    if not in_tmux():
        raise ValueError(
            "program parent routing requires TMUX — open child tabs manually "
            "(see program bootstrap manual steps)"
        )


def _active_child_entry(program: dict[str, Any], child_name: str) -> dict[str, Any]:
    active = program.get("active_children") or []
    for entry in active:
        if entry.get("codename") == child_name:
            return entry
    raise ValueError(f"child {child_name!r} is not registered in parent program active_children")


def _child_pane_id(root: Path, program: dict[str, Any], child_name: str) -> str:
    entry = _active_child_entry(program, child_name)
    stored = entry.get("pane_id")
    stored_id = str(stored).strip() if stored else None
    return resolve_child_pane(root, child_name, stored_id)


def _load_child_workflow(root: Path, child_name: str) -> dict[str, Any]:
    session_dir = root / "sessions" / child_name
    workflow_path = session_dir / "workflow.json"
    if not workflow_path.is_file():
        raise ValueError(
            f"child {child_name!r} has no workflow.json; cannot route gate feedback"
        )
    return load_workflow(session_dir)


def _require_child_gate_phase(workflow: dict[str, Any], child_name: str, gate: str) -> None:
    phase = workflow.get("phase")
    if phase != gate:
        raise ValueError(
            f"child {child_name!r} workflow phase is {phase!r}, not {gate!r}"
        )


def _persist_last_routed(
    root: Path,
    parent_name: str,
    child_name: str,
    payload: str,
) -> None:
    session_dir = root / "sessions" / parent_name
    program = load_program(session_dir)
    entry = _active_child_entry(program, child_name)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    entry["last_routed_at"] = now
    entry["last_routed_message"] = payload
    save_program(session_dir, program, codename=parent_name)


def evaluate_route_feedback(
    root: Path,
    *,
    parent: str,
    child: str,
    gate: str,
    message: str,
    force: bool = False,
) -> dict[str, Any]:
    """Read-only guard evaluation for monitor and tests."""
    parent_name = validate_codename(parent)
    child_name = validate_codename(child)
    if gate not in GATE_PHASES:
        return {"routable": False, "skip_reason": f"invalid gate {gate!r}"}
    if not is_allowed_route_message(gate, message):
        return {"routable": False, "skip_reason": "invalid gate message"}
    try:
        program = load_program(root / "sessions" / parent_name)
        entry = _active_child_entry(program, child_name)
    except ValueError as exc:
        return {"routable": False, "skip_reason": str(exc)}
    try:
        workflow = _load_child_workflow(root, child_name)
    except ValueError as exc:
        return {"routable": False, "skip_reason": str(exc)}
    phase = workflow.get("phase")
    if phase != gate:
        return {
            "routable": False,
            "skip_reason": f"child {child_name!r} workflow phase is {phase!r}, not {gate!r}",
        }
    skip = _gate_feedback_skip_reason(workflow, entry, gate, message, force=force)
    if skip:
        return {"routable": False, "skip_reason": skip}
    return {"routable": True, "skip_reason": None}


def evaluate_route_correction(
    root: Path,
    *,
    parent: str,
    child: str,
    message: str,
    force: bool = False,
) -> dict[str, Any]:
    """Read-only correction guard evaluation for monitor and tests."""
    parent_name = validate_codename(parent)
    child_name = validate_codename(child)
    body = sanitize_goal_text(message.strip())
    if not body:
        return {"routable": False, "skip_reason": "correction message must not be empty"}
    try:
        program = load_program(root / "sessions" / parent_name)
        entry = _active_child_entry(program, child_name)
    except ValueError as exc:
        return {"routable": False, "skip_reason": str(exc)}
    try:
        workflow = _load_child_workflow(root, child_name)
    except ValueError as exc:
        return {"routable": False, "skip_reason": str(exc)}
    skip = _correction_skip_reason(workflow, entry, body, force=force)
    if skip:
        return {"routable": False, "skip_reason": skip}
    return {"routable": True, "skip_reason": None}


def _first_routable_gate_feedback(
    root: Path,
    *,
    parent: str,
    child: str,
    gate: str,
) -> dict[str, Any]:
    """Probe all allowed gate messages; routable if any action passes guards."""
    evaluation: dict[str, Any] = {
        "routable": False,
        "skip_reason": "no routable gate action",
    }
    for msg in sorted(allowed_route_messages(gate)):
        candidate = evaluate_route_feedback(
            root,
            parent=parent,
            child=child,
            gate=gate,
            message=msg,
        )
        if candidate.get("routable"):
            return candidate
        evaluation = candidate
    return evaluation


def child_route_snapshot_fields(
    root: Path,
    *,
    parent: str,
    child_entry: dict[str, Any],
    pending_gate: str | None,
) -> dict[str, Any]:
    """Monitor fields: last route metadata plus hypothetical routable evaluation."""
    child_name = validate_codename(str(child_entry.get("codename", "")))
    fields: dict[str, Any] = {
        "last_routed_at": child_entry.get("last_routed_at"),
        "last_routed_message": child_entry.get("last_routed_message"),
        "routable": False,
        "route_skip_reason": None,
    }
    if pending_gate == "brief_review":
        evaluation = _first_routable_gate_feedback(
            root,
            parent=parent,
            child=child_name,
            gate="brief_review",
        )
    elif pending_gate == "plan_user_review":
        evaluation = _first_routable_gate_feedback(
            root,
            parent=parent,
            child=child_name,
            gate="plan_user_review",
        )
    else:
        evaluation = evaluate_route_correction(
            root,
            parent=parent,
            child=child_name,
            message="progress nudge",
        )
    fields["routable"] = bool(evaluation.get("routable"))
    fields["route_skip_reason"] = evaluation.get("skip_reason")
    return fields


def route_feedback(
    root: Path,
    *,
    parent: str,
    child: str,
    gate: str,
    message: str,
    dry_run: bool = False,
    force: bool = False,
) -> RouteResult:
    parent_name = validate_codename(parent)
    child_name = validate_codename(child)
    if gate not in GATE_PHASES:
        allowed = ", ".join(sorted(GATE_PHASES))
        raise ValueError(f"invalid gate {gate!r}; expected one of: {allowed}")

    if not is_allowed_route_message(gate, message):
        allowed_msgs = allowed_route_messages(gate)
        raise ValueError(
            f"invalid message for {gate}; expected one of: {', '.join(sorted(allowed_msgs))}"
        )

    _require_bound_parent(root, parent_name)
    program = load_program(root / "sessions" / parent_name)
    entry = _active_child_entry(program, child_name)
    workflow = _load_child_workflow(root, child_name)

    command = message.strip()
    _require_child_gate_phase(workflow, child_name, gate)

    skip = _gate_feedback_skip_reason(workflow, entry, gate, message, force=force)
    if skip:
        return RouteResult(sent=False, payload=command, skip_reason=skip)

    if dry_run:
        return RouteResult(sent=False, payload=command)

    _require_tmux()
    pane_id = _child_pane_id(root, program, child_name)
    send_to_child_pane(pane_id, command, submit=True)
    _persist_last_routed(root, parent_name, child_name, command)
    return RouteResult(sent=True, payload=command)


def route_correction(
    root: Path,
    *,
    parent: str,
    child: str,
    message: str,
    dry_run: bool = False,
    force: bool = False,
) -> RouteResult:
    """Send free-text brief/plan correction to child pane (no inbox file)."""
    parent_name = validate_codename(parent)
    child_name = validate_codename(child)
    body = sanitize_goal_text(message.strip())
    if not body:
        raise ValueError("correction message must not be empty")

    _require_bound_parent(root, parent_name)
    program = load_program(root / "sessions" / parent_name)
    entry = _active_child_entry(program, child_name)
    workflow = _load_child_workflow(root, child_name)

    skip = _correction_skip_reason(workflow, entry, body, force=force)
    if skip:
        return RouteResult(sent=False, payload=body, skip_reason=skip)

    if dry_run:
        return RouteResult(sent=False, payload=body)

    _require_tmux()
    pane_id = _child_pane_id(root, program, child_name)
    send_to_child_pane(pane_id, body, submit=True)
    _persist_last_routed(root, parent_name, child_name, body)
    return RouteResult(sent=True, payload=body)
