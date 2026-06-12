"""Route parent program gate feedback to child inbox."""

from __future__ import annotations

from pathlib import Path

from gate_command_registry import (
    allowed_route_messages,
    format_program_gate_message,
    is_allowed_route_message,
)
from program_state import GATE_PHASES, load_program
from session_binding import resolve_codename, validate_codename, write_inbox_program_route


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
    active = {entry["codename"] for entry in program.get("active_children") or []}
    if child_name not in active:
        raise ValueError(f"child {child_name!r} is not registered in parent program active_children")

    payload = format_program_gate_message(parent_name, gate, message)
    if dry_run:
        return payload
    bound, _ = resolve_codename(root)
    if bound != parent_name:
        if bound is None:
            raise ValueError(
                f"route_feedback requires bound session {parent_name!r}, not unbound caller"
            )
        raise ValueError(
            f"route_feedback requires bound session {parent_name!r}, not {bound!r}"
        )
    write_inbox_program_route(root, parent_name, child_name, payload)
    return payload
