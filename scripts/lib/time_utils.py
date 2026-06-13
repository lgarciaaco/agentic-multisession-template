"""Shared UTC timestamp helpers for hub scripts."""

from __future__ import annotations

from datetime import datetime, timezone


def utc_now_iso() -> str:
    """Return UTC ISO-8601 timestamp with Z suffix (no microseconds)."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
