"""Shared review ID scan and allocate helpers for pr-NNN and r-NNN."""

from __future__ import annotations

import re
from pathlib import Path

_REVIEW_ID_PATTERN = re.compile(r"^([a-z]+)-(\d+)$")


def _parse_review_stem(stem: str) -> tuple[str, int] | None:
    match = _REVIEW_ID_PATTERN.match(stem)
    if not match:
        return None
    return match.group(1), int(match.group(2))


def scan_review_ids(directory: Path, prefix: str) -> list[int]:
    """Return sorted numeric suffixes for ``{prefix}-NNN`` files in *directory*."""
    if not directory.is_dir():
        return []
    numbers: list[int] = []
    for path in directory.iterdir():
        if not path.is_file() or path.suffix != ".json":
            continue
        parsed = _parse_review_stem(path.stem)
        if parsed and parsed[0] == prefix:
            numbers.append(parsed[1])
    return sorted(numbers)


def next_review_id(directory: Path, prefix: str, *, width: int = 3) -> str:
    """Allocate the next ``{prefix}-NNN`` id under *directory*."""
    directory.mkdir(parents=True, exist_ok=True)
    numbers = scan_review_ids(directory, prefix)
    highest = numbers[-1] if numbers else 0
    return f"{prefix}-{highest + 1:0{width}d}"


def latest_review_id(directory: Path, prefix: str, *, width: int = 3) -> str | None:
    """Return the highest ``{prefix}-NNN`` stem under *directory*, or None."""
    numbers = scan_review_ids(directory, prefix)
    if not numbers:
        return None
    return f"{prefix}-{numbers[-1]:0{width}d}"
