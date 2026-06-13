"""Non-interactive git editor environment for headless agent sessions."""

from __future__ import annotations

NONINTERACTIVE_EDITOR_ENV: dict[str, str] = {
    "GIT_EDITOR": "true",
    "EDITOR": "true",
}


def noninteractive_editor_env() -> dict[str, str]:
    """Return editor env vars that prevent git from opening an interactive editor."""
    return dict(NONINTERACTIVE_EDITOR_ENV)
