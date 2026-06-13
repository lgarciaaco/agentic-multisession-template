"""Route parent program feedback to child tmux panes via send-keys."""

from __future__ import annotations

from pathlib import Path

from gate_command_registry import allowed_route_messages, is_allowed_route_message
from program_child_tabs import in_tmux, resolve_child_pane, send_to_child_pane
from program_state import GATE_PHASES, load_program
from session_binding import resolve_codename, sanitize_goal_text, validate_codename


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


def _active_child_entry(program: dict, child_name: str) -> dict:
    active = program.get("active_children") or []
    for entry in active:
        if entry.get("codename") == child_name:
            return entry
    raise ValueError(f"child {child_name!r} is not registered in parent program active_children")


def _child_pane_id(root: Path, program: dict, child_name: str) -> str:
    entry = _active_child_entry(program, child_name)
    stored = entry.get("pane_id")
    stored_id = str(stored).strip() if stored else None
    return resolve_child_pane(root, child_name, stored_id)


def route_feedback(
    root: Path,
    *,
    parent: str,
    child: str,
    gate: str,
    message: str,
    dry_run: bool = False,
) -> str:
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

    program = load_program(root / "sessions" / parent_name)
    _active_child_entry(program, child_name)

    command = message.strip()
    _require_bound_parent(root, parent_name)
    if dry_run:
        return command

    _require_tmux()
    pane_id = _child_pane_id(root, program, child_name)
    send_to_child_pane(pane_id, command, submit=True)
    return command


def route_correction(
    root: Path,
    *,
    parent: str,
    child: str,
    message: str,
    dry_run: bool = False,
) -> str:
    """Send free-text brief/plan correction to child pane (no inbox file)."""
    parent_name = validate_codename(parent)
    child_name = validate_codename(child)
    body = sanitize_goal_text(message.strip())
    if not body:
        raise ValueError("correction message must not be empty")

    program = load_program(root / "sessions" / parent_name)
    _active_child_entry(program, child_name)

    _require_bound_parent(root, parent_name)
    if dry_run:
        return body

    _require_tmux()
    pane_id = _child_pane_id(root, program, child_name)
    send_to_child_pane(pane_id, body, submit=True)
    return body
