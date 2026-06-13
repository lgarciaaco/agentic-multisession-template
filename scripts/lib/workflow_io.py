"""Shared workflow I/O helpers (JSON summaries)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

MissingPolicy = Literal["raise", "none"]


def read_summary_json(path: Path, *, missing: MissingPolicy = "raise") -> dict[str, Any] | None:
    """
    Read a review summary JSON file.

    missing='raise': raise FileNotFoundError when the path is absent.
    missing='none': return None when the path is absent.
    """
    if not path.exists():
        if missing == "none":
            return None
        raise FileNotFoundError(f"Review summary not found: {path}")
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}") from exc
