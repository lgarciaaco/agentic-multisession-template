"""Shared git subprocess helper for hub scripts."""

from __future__ import annotations

import subprocess
from pathlib import Path

_GIT_TIMEOUT_SEC = 300


def run_git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=check,
        timeout=_GIT_TIMEOUT_SEC,
    )
