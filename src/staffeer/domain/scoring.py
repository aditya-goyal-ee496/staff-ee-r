"""Deterministic skill scoring — required-skill coverage as a `SkillScore` (Track A, slice 03).

Coverage is purely lexical: exact canonical matches count full, adjacency substitutions count at
a lower, configurable weight, and everything else is a surfaced gap (no semantic similarity — that
is slice 05). Pure function over `(role, consultant)`; no I/O (`hexagonal-architecture.md`).
"""

from __future__ import annotations

from collections.abc import Mapping

from staffeer.domain.models import Consultant, Role, SkillScore
from staffeer.domain.skills import DEFAULT_ADJACENCY, adjacent_alternatives, canonical_skills

DEFAULT_ADJACENCY_WEIGHT = 0.5


def skill_coverage(
    role: Role,
    consultant: Consultant,
    adjacency: Mapping[str, tuple[str, ...]] = DEFAULT_ADJACENCY,
    adjacency_weight: float = DEFAULT_ADJACENCY_WEIGHT,
) -> SkillScore:
    """How well `consultant`'s skills cover `role`'s required skills, as a `SkillScore` (0..1)."""
    required = canonical_skills(role.required_skills)
    if not required:
        return SkillScore(value=1.0, detail="role lists no required skills")
    held = set(canonical_skills(consultant.skills))
    matched = tuple(skill for skill in required if skill in held)
    substitutions = _substitutions(required, held, adjacency)
    adjacent = tuple(substitutions)
    missing = tuple(skill for skill in required if skill not in held and skill not in substitutions)
    value = (len(matched) + adjacency_weight * len(adjacent)) / len(required)
    return SkillScore(
        value=value,
        matched=matched,
        missing=missing,
        adjacent=adjacent,
        detail=_coverage_detail(matched, substitutions, missing),
    )


def _substitutions(
    required: tuple[str, ...],
    held: set[str],
    adjacency: Mapping[str, tuple[str, ...]],
) -> dict[str, str]:
    """Map each unmet required skill to a held skill that may substitute for it, if any."""
    substitutions: dict[str, str] = {}
    for skill in required:
        if skill in held:
            continue
        alternatives = held.intersection(adjacent_alternatives(skill, adjacency))
        if alternatives:
            substitutions[skill] = sorted(alternatives)[0]
    return substitutions


def _coverage_detail(
    matched: tuple[str, ...], substitutions: Mapping[str, str], missing: tuple[str, ...]
) -> str:
    """A human-readable summary of matched, adjacent-substituted, and missing skills."""
    parts: list[str] = []
    if matched:
        parts.append(f"matched {', '.join(matched)}")
    if substitutions:
        adjacent = ", ".join(f"{req} via {alt}" for req, alt in substitutions.items())
        parts.append(f"adjacent {adjacent}")
    if missing:
        parts.append(f"missing {', '.join(missing)}")
    return "; ".join(parts)
