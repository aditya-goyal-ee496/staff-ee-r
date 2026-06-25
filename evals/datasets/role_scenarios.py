"""Role scenario dataset for Promptfoo and DeepEval eval suites.

Provenance: all consultants and roles here are synthetic, created for eval coverage.
Synthetic entries carry ``source='synthetic'`` on the Consultant. Scenarios are keyed
by ``id`` so the Promptfoo provider and DeepEval suites can look them up by name.

A 100% pass rate on relevance or faithfulness metrics is a COVERAGE WARNING — it means
the scenarios are too easy, not that the system is perfect (ADR-001).

Negative scenarios (label='negative') must number at least 4:
  1. no-viable-match      — none meet location, shortlist must be empty.
  2. location-blocked     — Chennai co-located role, all consultants lack chennai_open.
  3. unverified-new-joiner — NEW_JOINER with skills_verified=False; provenance penalty.
  4. adjacent-skill-only  — role needs kotlin, consultant has only java (adjacent, not exact).
"""

from __future__ import annotations

from datetime import date

from staffeer.domain.models import Consultant, Role, SupplyState

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _synth(
    consultant_id: str,
    name: str,
    location: str,
    skills: tuple[str, ...],
    state: SupplyState = SupplyState.BEACH,
    chennai_open: bool = False,
    skills_verified: bool = True,
) -> Consultant:
    """Build a synthetic Consultant for eval scenarios (no available_from needed)."""
    return Consultant(
        id=consultant_id,
        name=name,
        location=location,
        skills=skills,
        state=state,
        chennai_open=chennai_open,
        skills_verified=skills_verified,
        source="synthetic",
    )


# ---------------------------------------------------------------------------
# ROLE_SCENARIOS
# ---------------------------------------------------------------------------

ROLE_SCENARIOS: list[dict] = [
    # ------------------------------------------------------------------
    # POSITIVE: full-skill beach match, remote role
    # ------------------------------------------------------------------
    {
        "id": "positive-backend-match",
        "role": Role(
            id="R-BE",
            title="Backend Engineer",
            location="Remote-India",
            required_skills=("python", "postgres"),
        ),
        "consultants": [
            _synth("alice", "Alice", "Chennai", ("python", "postgres")),
            _synth("bob", "Bob", "Bengaluru", ("java",)),
        ],
        "label": "positive",
        "expected_includes": ["Alice"],
        "expected_excludes": [],
        "notes": "Alice matches all required skills; Bob has none — still ranked, not excluded.",
    },
    # ------------------------------------------------------------------
    # POSITIVE: partial match still shortlisted with gap explanation
    # ------------------------------------------------------------------
    {
        "id": "positive-partial-match",
        "role": Role(
            id="R-ML",
            title="ML Engineer",
            location="Remote-India",
            required_skills=("python", "tensorflow", "spark"),
        ),
        "consultants": [
            _synth("cara", "Cara", "Pune", ("python", "tensorflow")),
            _synth("dan", "Dan", "Delhi NCR", ("spark",)),
        ],
        "label": "positive",
        "expected_includes": ["Cara"],
        "expected_excludes": [],
        "notes": (
            "Cara has 2/3 skills (best coverage); Dan has 1/3. "
            "Both appear on shortlist, Cara ranked first."
        ),
    },
    # ------------------------------------------------------------------
    # NEGATIVE 1: no-viable-match — no consultant in required location
    # ------------------------------------------------------------------
    {
        "id": "negative-no-viable-match",
        "role": Role(
            id="R-NVM",
            title="SRE",
            location="Mumbai",
            required_skills=("kubernetes",),
            co_location=True,
        ),
        "consultants": [
            _synth("eve", "Eve", "Chennai", ("kubernetes",)),
            _synth("frank", "Frank", "Bengaluru", ("kubernetes",)),
        ],
        "label": "negative",
        "expected_includes": [],
        "expected_excludes": ["Eve", "Frank"],
        "notes": (
            "Role requires Mumbai co-location; all consultants are elsewhere "
            "and neither has chennai_open — shortlist must be empty."
        ),
    },
    # ------------------------------------------------------------------
    # NEGATIVE 2: location-blocked — Chennai co-located, none have chennai_open
    # ------------------------------------------------------------------
    {
        "id": "negative-location-blocked",
        "role": Role(
            id="R-LB",
            title="DevOps Engineer",
            location="Chennai",
            required_skills=("terraform",),
            co_location=True,
            chennai_open=True,
        ),
        "consultants": [
            _synth("gita", "Gita", "Bengaluru", ("terraform",), chennai_open=False),
            _synth("hari", "Hari", "Pune", ("terraform",), chennai_open=False),
        ],
        "label": "negative",
        "expected_includes": [],
        "expected_excludes": ["Gita", "Hari"],
        "notes": ("Chennai co-located role; both consultants lack chennai_open flag — excluded."),
    },
    # ------------------------------------------------------------------
    # NEGATIVE 3: unverified new joiner — skills_verified=False
    # ------------------------------------------------------------------
    {
        "id": "negative-unverified-new-joiner",
        "role": Role(
            id="R-UNJ",
            title="Kotlin Developer",
            location="Remote-India",
            required_skills=("kotlin",),
            start_date=date(2026, 8, 1),
        ),
        "consultants": [
            Consultant(
                id="nisha",
                name="Nisha",
                location="Pune",
                skills=("kotlin",),
                state=SupplyState.NEW_JOINER,
                skills_verified=False,
                available_from=date(2026, 8, 3),
                source="synthetic",
            ),
        ],
        "label": "negative",
        "expected_includes": ["Nisha"],
        "expected_excludes": [],
        "notes": (
            "Nisha appears on the shortlist but with a provenance penalty and "
            "unverified-skills flag in the explanation. She must appear so the "
            "penalty is visible; expected_includes enforces she is not silently dropped."
        ),
    },
    # ------------------------------------------------------------------
    # NEGATIVE 4: adjacent-skill-only — role needs kotlin, consultant has java only
    # ------------------------------------------------------------------
    {
        "id": "negative-adjacent-skill-only",
        "role": Role(
            id="R-KT",
            title="Kotlin Developer",
            location="Remote-India",
            required_skills=("kotlin",),
        ),
        "consultants": [
            _synth("ivan", "Ivan", "Chennai", ("java",)),
        ],
        "label": "negative",
        "expected_includes": ["Ivan"],
        "expected_excludes": [],
        "notes": (
            "Ivan has java (adjacent to kotlin) but not kotlin exactly. "
            "He must appear on the shortlist with a gap note; expected_includes "
            "enforces he is not silently suppressed — the gap explanation is the signal."
        ),
    },
]
