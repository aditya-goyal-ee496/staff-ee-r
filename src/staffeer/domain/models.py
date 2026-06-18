"""Frozen domain models and value objects — the contracts every track builds against.

Pure Pydantic, no I/O (dependency rule, `docs/rules/hexagonal-architecture.md`). All known
optional fields are pre-baked with safe defaults so later slices add behaviour without a
breaking model change (`docs/tasks/00b-contracts.md`). Ubiquitous language is taken from the
brief: beach, roll-off, new joiner, co-location, Chennai-open.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class SupplyState(StrEnum):
    """Where a consultant's availability comes from."""

    BEACH = "beach"
    ROLLING_OFF = "rolling_off"
    NEW_JOINER = "new_joiner"


class Priority(StrEnum):
    """Demand priority for an open role."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ValueObject(BaseModel):
    """Base for immutable, equality-by-value domain objects (DDD value objects)."""

    model_config = ConfigDict(frozen=True)


class Consultant(ValueObject):
    """A person available to be staffed (entity; identity is `id`)."""

    id: str
    name: str
    location: str
    grade: str | None = None
    skills: tuple[str, ...] = ()
    state: SupplyState = SupplyState.BEACH
    # Pre-baked optional fields for later supply states (`docs/tasks/08-supply-expansion.md`).
    available_from: date | None = None
    confidence: float = 1.0
    skills_verified: bool = True
    source: str | None = None


class Role(ValueObject):
    """An open consulting role to be staffed (entity; identity is `id`)."""

    id: str
    title: str
    location: str
    required_skills: tuple[str, ...] = ()
    start_date: date | None = None
    priority: Priority = Priority.MEDIUM
    # Co-location means the team must be physically in `location`; Chennai-open is the
    # structured signal for a Chennai-co-located team (brief, domain rules).
    co_location: bool = False
    chennai_open: bool = False


class ConstraintCheck(ValueObject):
    """The outcome of one hard-constraint check, with a human-readable reason."""

    name: str
    passed: bool
    reason: str


class EligibilityResult(ValueObject):
    """A consultant's hard-constraint outcome — eligible only if every check passed."""

    consultant: Consultant
    checks: tuple[ConstraintCheck, ...] = ()

    @property
    def eligible(self) -> bool:
        """True only when no check failed (an empty check list is vacuously eligible)."""
        return all(check.passed for check in self.checks)

    @property
    def failures(self) -> tuple[ConstraintCheck, ...]:
        """The checks that excluded this consultant — surfaced, never silently dropped."""
        return tuple(check for check in self.checks if not check.passed)


class SkillScore(ValueObject):
    """Deterministic required-skill coverage for a consultant against a role (0..1)."""

    value: float = 0.0
    matched: tuple[str, ...] = ()
    missing: tuple[str, ...] = ()
    adjacent: tuple[str, ...] = ()
    detail: str = ""


class ScoreContribution(ValueObject):
    """One named, weighted contributor to a match score.

    Scoring is a *sum of contributions*, never a monolithic formula: lexical, semantic,
    soft-LLM and provenance tracks each append a contributor, and an absent adapter
    contributes `value=0` so the blend is always valid (`docs/tasks/00b-contracts.md`).
    """

    source: str
    value: float
    weight: float = 1.0
    detail: str = ""

    @property
    def weighted(self) -> float:
        """This contributor's effect on the blended score."""
        return self.value * self.weight


class ExplanationFactor(ValueObject):
    """One factor that moved a consultant's rank, with the source backing the claim."""

    source: str
    summary: str
    detail: str = ""


class Explanation(ValueObject):
    """An open list of factors — every factor that moved the rank is appended (Principle 1)."""

    factors: tuple[ExplanationFactor, ...] = ()

    def with_factor(self, factor: ExplanationFactor) -> Explanation:
        """Return a new explanation with `factor` appended (immutably)."""
        return Explanation(factors=(*self.factors, factor))


class Match(ValueObject):
    """A ranked consultant on a shortlist, with its score breakdown and explanation."""

    consultant: Consultant
    score: float = 0.0
    contributions: tuple[ScoreContribution, ...] = ()
    explanation: Explanation = Field(default_factory=Explanation)


class Shortlist(ValueObject):
    """The ranked, explainable result for a role, plus explained exclusions."""

    role: Role
    matches: tuple[Match, ...] = ()
    excluded: tuple[EligibilityResult, ...] = ()
