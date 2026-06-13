"""Shared gate phase metadata for workflow and program orchestrator consumers."""

from __future__ import annotations

from typing import TypedDict

from program_state import GATE_PHASES


class GateMetadataEntry(TypedDict):
    artifact_path: str
    feedback_kind: str
    display_label: str
    column_short: str


GATE_METADATA: dict[str, GateMetadataEntry] = {
    "brief_review": {
        "artifact_path": "artifacts/problem-brief.md",
        "feedback_kind": "brief_correction",
        "display_label": "Brief review",
        "column_short": "brief",
    },
    "plan_user_review": {
        "artifact_path": "artifacts/action-plan.md",
        "feedback_kind": "plan_feedback",
        "display_label": "Plan review",
        "column_short": "plan",
    },
}


def gate_artifact_path(phase: str) -> str:
    if phase not in GATE_METADATA:
        raise ValueError(f"unknown gate phase: {phase!r}")
    return GATE_METADATA[phase]["artifact_path"]


def gate_feedback_kind(phase: str) -> str:
    if phase not in GATE_METADATA:
        raise ValueError(f"unknown gate phase: {phase!r}")
    return GATE_METADATA[phase]["feedback_kind"]


def gate_display_label(phase: str) -> str:
    if phase not in GATE_METADATA:
        raise ValueError(f"unknown gate phase: {phase!r}")
    return GATE_METADATA[phase]["display_label"]


def gate_feedback_kinds() -> frozenset[str]:
    return frozenset(entry["feedback_kind"] for entry in GATE_METADATA.values())


def gate_column_short_label(pending_gate: str | None) -> str:
    if pending_gate is None or pending_gate not in GATE_METADATA:
        return "—"
    return GATE_METADATA[pending_gate]["column_short"]


def _validate_registry_coherence() -> None:
    registry_keys = frozenset(GATE_METADATA)
    if registry_keys != GATE_PHASES:
        missing = GATE_PHASES - registry_keys
        extra = registry_keys - GATE_PHASES
        raise RuntimeError(
            f"GATE_METADATA keys must match GATE_PHASES; missing={missing!r} extra={extra!r}"
        )
    for phase in GATE_PHASES:
        entry = GATE_METADATA[phase]
        for field in ("artifact_path", "feedback_kind", "display_label", "column_short"):
            value = entry.get(field)
            if not isinstance(value, str) or not value.strip():
                raise RuntimeError(f"GATE_METADATA[{phase!r}] missing or empty {field!r}")


_validate_registry_coherence()
