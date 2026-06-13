"""Shared gate command vocabulary for workflow gates and program route feedback."""

from __future__ import annotations

import re
from re import Pattern

from program_state import GATE_PHASES

ACCEPT_BRIEF = "accept_brief"
ACCEPT_PLAN = "accept_plan"
REOPEN_BRIEF = "reopen_brief"
REOPEN_PLAN = "reopen_plan"

GATE_COMMAND_ACTIONS: frozenset[str] = frozenset(
    {ACCEPT_BRIEF, ACCEPT_PLAN, REOPEN_BRIEF, REOPEN_PLAN}
)

PROGRAM_GATE_MARKER = "[program-orchestrator gate="


def format_program_gate_message(parent: str, gate: str, message: str) -> str:
    """Build the three-line inbox payload for program parent gate routing."""
    command = message.strip()
    return (
        f"{command}\n\n"
        f"{PROGRAM_GATE_MARKER}{gate}]\n"
        f"Parent `{parent}` routed feedback."
    )

# Lowercase user-facing strings per phase and action (route-feedback validation).
_ROUTE_MESSAGES: dict[str, dict[str, frozenset[str]]] = {
    "brief_review": {
        ACCEPT_BRIEF: frozenset({"accept brief", "accept"}),
        REOPEN_BRIEF: frozenset({"reopen brief"}),
    },
    "plan_user_review": {
        ACCEPT_PLAN: frozenset({"accept plan"}),
        REOPEN_PLAN: frozenset({"reopen plan"}),
    },
}

_COMMAND_PATTERNS: dict[str, Pattern[str]] = {
    ACCEPT_BRIEF: re.compile(
        r"^(?:workflow:\s*)?(?:accept brief|accept)\s*$",
        re.IGNORECASE,
    ),
    ACCEPT_PLAN: re.compile(
        r"^(?:workflow:\s*)?accept plan\s*$",
        re.IGNORECASE,
    ),
    REOPEN_BRIEF: re.compile(
        r"^(?:workflow:\s*)?reopen brief\s*$",
        re.IGNORECASE,
    ),
    REOPEN_PLAN: re.compile(
        r"^(?:workflow:\s*)?reopen plan\s*$",
        re.IGNORECASE,
    ),
}

if frozenset(_ROUTE_MESSAGES) != GATE_PHASES:
    raise RuntimeError("gate command registry phase keys must match program_state.GATE_PHASES")


def phase_command_actions(phase: str) -> tuple[str, ...]:
    """Return normalized actions valid for inbox classification at phase."""
    if phase not in GATE_PHASES:
        return ()
    return tuple(_ROUTE_MESSAGES[phase].keys())


def command_pattern(action: str) -> Pattern[str] | None:
    return _COMMAND_PATTERNS.get(action)


def allowed_route_messages(phase: str) -> frozenset[str]:
    """Lowercase allowed strings for program route-feedback validation."""
    if phase not in GATE_PHASES:
        raise ValueError(f"invalid gate phase {phase!r}")
    parts: set[str] = set()
    for strings in _ROUTE_MESSAGES[phase].values():
        parts.update(strings)
    return frozenset(parts)


def normalize_route_message(message: str) -> str:
    return message.strip().lower()


def is_allowed_route_message(phase: str, message: str) -> bool:
    return classify_gate_command(phase, message) is not None


def classify_gate_command(phase: str, first_line: str) -> str | None:
    """Return normalized action when first line matches a gate command at phase."""
    line = first_line.strip()
    for action in phase_command_actions(phase):
        pattern = command_pattern(action)
        if pattern and pattern.match(line):
            return action
    return None


def is_gate_command_action(action: str) -> bool:
    return action in GATE_COMMAND_ACTIONS


def _validate_registry_coherence() -> None:
    for phase in GATE_PHASES:
        for action in _ROUTE_MESSAGES[phase]:
            if command_pattern(action) is None:
                raise RuntimeError(f"missing command pattern for {action!r}")
        for action, strings in _ROUTE_MESSAGES[phase].items():
            for msg in strings:
                if not is_allowed_route_message(phase, msg):
                    raise RuntimeError(f"route message {msg!r} not allowed at {phase!r}")
                if classify_gate_command(phase, msg) != action:
                    raise RuntimeError(
                        f"classifier mismatch for {msg!r} at {phase!r}: expected {action!r}"
                    )
    for action in GATE_COMMAND_ACTIONS:
        if command_pattern(action) is None:
            raise RuntimeError(f"missing command pattern for {action!r}")


_validate_registry_coherence()
