"""Route parent program gate feedback to child inbox."""

from __future__ import annotations

from pathlib import Path

from program_state import GATE_PHASES, load_program
from session_binding import validate_codename, write_inbox

ALLOWED_MESSAGES = {
    "brief_review": frozenset({"accept brief", "accept", "reopen brief"}),
    "plan_user_review": frozenset({"accept plan", "reopen plan"}),
}


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

    normalized = message.strip().lower()
    allowed_msgs = ALLOWED_MESSAGES[gate]
    if normalized not in allowed_msgs:
        raise ValueError(
            f"invalid message for {gate}; expected one of: {', '.join(sorted(allowed_msgs))}"
        )

    program = load_program(root / "sessions" / parent_name)
    active = {entry["codename"] for entry in program.get("active_children") or []}
    if child_name not in active:
        raise ValueError(f"child {child_name!r} is not registered in parent program active_children")

    command = message.strip()
    payload = (
        f"{command}\n\n"
        f"[program-orchestrator gate={gate}]\n"
        f"Parent `{parent_name}` routed feedback."
    )
    if dry_run:
        return payload
    write_inbox(root, parent_name, child_name, payload)
    return payload
