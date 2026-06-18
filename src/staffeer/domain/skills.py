"""Skill vocabulary — canonical skill names and adjacency substitutions (Track A, slice 03).

Required and consultant skills are reconciled in a single *canonical* form (trimmed, lower-cased,
de-qualified, de-aliased) so "K8s", "kubernetes" and "Kubernetes (expert)" all match. Adjacency
captures the brief's rule that a related skill may substitute at a lower score — e.g. a Java
developer for a Kotlin role. Pure, no I/O (`docs/rules/hexagonal-architecture.md`).
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping

# Aliases fold common spellings onto one canonical skill name.
_ALIASES: Mapping[str, str] = {
    "k8s": "kubernetes",
    "golang": "go",
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "postgres": "postgresql",
}

# A required skill (key) may be satisfied — at a lower score — by any listed adjacent skill.
# Seeded from the brief (a Java developer for a Kotlin role). Extend by adding entries; keys and
# values must already be canonical (the same form `canonical_skill` produces).
DEFAULT_ADJACENCY: Mapping[str, tuple[str, ...]] = {
    "kotlin": ("java",),
    "java": ("kotlin",),
    "typescript": ("javascript",),
}

_QUALIFIER = re.compile(r"\(.*?\)")


def canonical_skill(raw: str) -> str:
    """The canonical form of a skill name: trimmed, lower-cased, de-qualified, de-aliased."""
    name = _QUALIFIER.sub("", raw).strip().lower()
    return _ALIASES.get(name, name)


def canonical_skills(raw_skills: Iterable[str]) -> tuple[str, ...]:
    """Canonical skill names, blanks dropped and duplicates removed, in first-seen order."""
    ordered: dict[str, None] = {}
    for raw in raw_skills:
        name = canonical_skill(raw)
        if name:
            ordered.setdefault(name, None)
    return tuple(ordered)


def adjacent_alternatives(
    required: str, adjacency: Mapping[str, tuple[str, ...]] = DEFAULT_ADJACENCY
) -> tuple[str, ...]:
    """Canonical skills that may substitute for `required` at a lower score."""
    return adjacency.get(required, ())
