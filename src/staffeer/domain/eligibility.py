"""Eligibility — the hard-constraint screening that gates staffing (Track A, slice 02).

A consultant is *eligible* for a role only when they clear every **hard constraint**:
**location** and **availability**. Hard constraints are deterministic and never use the LLM
(`CLAUDE.md` principle 2). An ineligible consultant is screened out *with a reason* —
exclusions are surfaced, never silently dropped (slice 02, `.claude/principles/code-quality.md`).
No I/O lives here (dependency rule, `.claude/principles/hexagonal-architecture.md`).

**Location-string contract** (what Track B's xlsx loader must produce): a location is
`"City"` or `"City, Region"`. `Region` defaults to **India** when only a city is given, since
Parity is an India-based consultancy. "Remote" is detected by the literal token; a remote role
co-located nowhere accepts any consultant in the same region (India). A co-located non-Chennai
role requires the named city; a Chennai co-located role admits a Chennai-based *or* a
Chennai-open consultant — one willing to work on-site in Chennai (`CLAUDE.md` domain rules).
"""

from __future__ import annotations

from datetime import date, timedelta

from staffeer.domain.models import (
    ConstraintCheck,
    Consultant,
    EligibilityResult,
    Role,
)

DEFAULT_AVAILABILITY_BUFFER_DAYS = 7
_DEFAULT_REGION = "india"
_CHENNAI = "chennai"


def _city_of(location: str) -> str:
    """The city token of a location string (the part before any comma, normalised)."""
    return location.split(",", 1)[0].strip().lower()


def _region_of(location: str) -> str:
    """The region of a location, defaulting to India when only a city is given."""
    parts = location.split(",", 1)
    return parts[1].strip().lower() if len(parts) > 1 else _DEFAULT_REGION


def _is_remote(location: str) -> bool:
    """True when the location names a remote arrangement."""
    return "remote" in location.lower()


def location_constraint(consultant: Consultant, role: Role) -> ConstraintCheck:
    """Whether `consultant`'s location satisfies `role`'s location demand, with a reason."""
    if role.chennai_open:
        satisfied = _city_of(consultant.location) == _CHENNAI or consultant.chennai_open
        return _location_outcome(
            satisfied, consultant, "Chennai co-located team (Chennai-based or Chennai-open)"
        )
    if role.co_location:
        satisfied = _city_of(consultant.location) == _city_of(role.location)
        return _location_outcome(satisfied, consultant, f"co-located in {role.location}")
    if _is_remote(role.location):
        satisfied = _region_of(consultant.location) == _region_of(role.location)
        return _location_outcome(
            satisfied, consultant, f"remote across {_region_of(role.location)}"
        )
    satisfied = _city_of(consultant.location) == _city_of(role.location)
    return _location_outcome(satisfied, consultant, f"on-site in {role.location}")


def _location_outcome(satisfied: bool, consultant: Consultant, demand: str) -> ConstraintCheck:
    """Assemble a location `ConstraintCheck` stating the demand and the consultant's place."""
    verb = "satisfies" if satisfied else "does not satisfy"
    return ConstraintCheck(
        name="location",
        passed=satisfied,
        reason=f"{consultant.location} {verb} {demand}",
    )


def availability_constraint(
    consultant: Consultant,
    role: Role,
    buffer_days: int = DEFAULT_AVAILABILITY_BUFFER_DAYS,
) -> ConstraintCheck:
    """Whether `consultant` is available by `role.start_date` plus the buffer, with a reason."""
    if role.start_date is None:
        return ConstraintCheck(
            name="availability",
            passed=True,
            reason="role has no start date; any availability accepted",
        )
    if consultant.available_from is None:
        return ConstraintCheck(
            name="availability",
            passed=True,
            reason=f"available now; meets start {role.start_date}",
        )
    latest = role.start_date + timedelta(days=buffer_days)
    satisfied = consultant.available_from <= latest
    return _availability_outcome(
        satisfied, consultant.available_from, role.start_date, latest, buffer_days
    )


def _availability_outcome(
    satisfied: bool, available_from: date, start: date, latest: date, buffer_days: int
) -> ConstraintCheck:
    """Assemble an availability `ConstraintCheck` naming the dates and latest acceptable day."""
    relation = "by" if satisfied else "after"
    return ConstraintCheck(
        name="availability",
        passed=satisfied,
        reason=(
            f"available {available_from} is {relation} latest-acceptable {latest} "
            f"(start {start} + {buffer_days}d buffer)"
        ),
    )


def screen_consultants(
    consultants: tuple[Consultant, ...],
    role: Role,
    buffer_days: int = DEFAULT_AVAILABILITY_BUFFER_DAYS,
) -> tuple[EligibilityResult, ...]:
    """Screen every consultant against `role`'s hard constraints, eligible ones first.

    Returns a result for *every* consultant (not only the eligible ones) so exclusions stay
    explainable. Order within the eligible/excluded groups is stable (input order).
    """
    results = tuple(
        EligibilityResult(
            consultant=consultant,
            checks=(
                location_constraint(consultant, role),
                availability_constraint(consultant, role, buffer_days),
            ),
        )
        for consultant in consultants
    )
    return tuple(sorted(results, key=lambda result: not result.eligible))
