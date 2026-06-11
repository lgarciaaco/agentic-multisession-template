"""CI observe loop helpers for workflow-orchestrator."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from workflow_plan import load_workflow, save_workflow

CI_GREEN = frozenset({"GREEN"})
CI_CONFLICT = frozenset({"CONFLICT"})
CI_TEST_FAILURE = frozenset({"TEST_FAILURE"})
CI_TIMEOUT = frozenset({"TIMEOUT"})
CI_ESCALATE = frozenset({"FAIL", "TIMEOUT"})


def begin_ci_observe(session_dir: Path) -> dict[str, Any]:
    """Initialize ci_observe loop counters (called after pr_creation SUCCESS)."""
    workflow = load_workflow(session_dir)
    phase = str(workflow.get("phase") or "")
    if phase != "ci_observe":
        raise ValueError(f"cannot begin ci_observe from phase '{phase}'")
    loops = workflow.setdefault("loops", {})
    ci_loop = loops.setdefault("ci_observe", {"iteration": 0, "max": 5, "last_verdict": None})
    ci_loop["iteration"] = 0
    ci_loop["last_verdict"] = None
    save_workflow(session_dir, workflow)
    return workflow


def advance_ci_observe(
    session_dir: Path,
    verdict: str,
) -> dict[str, Any]:
    """
    Advance CI observe loop after polling/fix attempt.

    Verdicts:
      GREEN        → phase: delivery
      CONFLICT     → stay in ci_observe (conductor rebases + retries)
      TEST_FAILURE → stay in ci_observe (conductor runs ci-fixer + retries)
      TIMEOUT      → escalate
      FAIL         → escalate
    """
    workflow = load_workflow(session_dir)
    loops = workflow.setdefault("loops", {})
    ci_loop = loops.setdefault("ci_observe", {"iteration": 0, "max": 5, "last_verdict": None})

    normalized = str(verdict).upper()
    _VALID_VERDICTS = CI_GREEN | CI_CONFLICT | CI_TEST_FAILURE | CI_TIMEOUT | frozenset({"FAIL"})
    if normalized not in _VALID_VERDICTS:
        raise ValueError(f"unknown ci_observe verdict: {verdict!r}")

    iteration = int(ci_loop.get("iteration", 0)) + 1
    maximum = int(ci_loop.get("max", 5))
    ci_loop["iteration"] = iteration
    ci_loop["last_verdict"] = normalized

    if normalized in CI_GREEN:
        workflow["phase"] = "delivery"
    elif ci_observe_escalate(normalized, iteration, maximum):
        workflow["phase"] = "ci_observe"
    else:
        workflow["phase"] = "ci_observe"

    save_workflow(session_dir, workflow)
    return workflow


def ci_observe_complete(verdict: str) -> bool:
    return str(verdict).upper() in CI_GREEN


def ci_observe_escalate(verdict: str, iteration: int, maximum: int) -> bool:
    normalized = str(verdict).upper()
    if normalized in CI_ESCALATE:
        return True
    return iteration >= maximum


def ci_observe_needs_rebase(verdict: str) -> bool:
    return str(verdict).upper() in CI_CONFLICT


def ci_observe_needs_fix(verdict: str) -> bool:
    return str(verdict).upper() in CI_TEST_FAILURE
