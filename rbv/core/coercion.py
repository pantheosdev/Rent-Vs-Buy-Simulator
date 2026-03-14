"""Input coercion helpers shared by core modules."""

from __future__ import annotations


def as_bool(value: object) -> bool:
    """Parse booleans from config-like values.

    Supports:
    - bool
    - numeric 0/1 (and other numerics via truthiness)
    - common string forms ("true"/"false", "yes"/"no", "on"/"off", "1"/"0")
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    t = str(value or "").strip().lower()
    if t in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if t in {"0", "false", "f", "no", "n", "off", "", "none", "null"}:
        return False
    return bool(value)
