"""Pure name<->filename mapping utilities for consultant profile stems.

No I/O; stdlib only. Domain core — no adapters imported.
"""

from __future__ import annotations

import re


def profile_key(value: str) -> str:
    """Return canonical key: lowercase, strip trailing _pp/_nj, normalise separators."""
    key = value.lower()
    key = re.sub(r"[_-](pp|nj)$", "", key)
    key = re.sub(r"[_-]", " ", key)
    return key.strip()


def resolve_profile_stem(name: str, stems: tuple[str, ...]) -> str | None:
    """Return first stem whose profile_key equals profile_key(name), else None."""
    target = profile_key(name)
    return next((s for s in stems if profile_key(s) == target), None)
