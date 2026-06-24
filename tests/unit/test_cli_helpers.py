"""Unit tests for CLI formatting helpers — _skill_detail and _format_match.

These tests exercise pure formatting logic without touching I/O.  No domain
logic is reproduced here: helpers are called directly and outputs are inspected
(one assertion per test, AAA, RULE-006).
"""

from __future__ import annotations

from staffeer.cli.main import _format_match, _skill_detail
from staffeer.domain.explain import SKILLS_SOURCE
from staffeer.domain.models import (
    Consultant,
    Explanation,
    ExplanationFactor,
    Match,
)


def _consultant() -> Consultant:
    return Consultant(id="C-01", name="Asha Rao", location="Chennai", grade="Senior")


def _match_with_skills_factor(detail: str) -> Match:
    factor = ExplanationFactor(
        source=SKILLS_SOURCE,
        summary="1 matched, 0 adjacent, 1 missing of 2 required skills",
        detail=detail,
    )
    return Match(consultant=_consultant(), score=0.75, explanation=Explanation(factors=(factor,)))


def _match_without_skills_factor() -> Match:
    factor = ExplanationFactor(
        source="location", summary="location: Remote-India matches Remote-India"
    )
    return Match(consultant=_consultant(), score=0.5, explanation=Explanation(factors=(factor,)))


def _match_adjacent_only() -> Match:
    """Match where the skills factor has adjacent skills but no exact matches and no missing."""
    factor = ExplanationFactor(
        source=SKILLS_SOURCE,
        summary="0 matched, 1 adjacent, 0 missing of 1 required skills",
        detail="adjacent: kotlin (substitutes java)",
    )
    return Match(consultant=_consultant(), score=0.5, explanation=Explanation(factors=(factor,)))


# _skill_detail tests


def test_skill_detail_returns_detail_when_skills_factor_has_non_empty_detail() -> None:
    match = _match_with_skills_factor("matched: python; missing: go")

    result = _skill_detail(match)

    assert result == "matched: python; missing: go"


def test_skill_detail_returns_empty_string_when_skills_factor_detail_is_empty() -> None:
    """A skills factor with detail='' is silently suppressed — documented, not a bug."""
    match = _match_with_skills_factor("")

    result = _skill_detail(match)

    assert result == ""


def test_skill_detail_returns_empty_string_when_no_skills_factor_present() -> None:
    match = _match_without_skills_factor()

    result = _skill_detail(match)

    assert result == ""


# _format_match tests


def test_format_match_includes_skill_detail_block_when_detail_is_present() -> None:
    """The dedicated skill-detail block (indented 'skills: <detail>') appears when detail is set."""
    match = _match_with_skills_factor("matched: python; missing: go")

    output = _format_match(1, match)

    assert "matched: python; missing: go" in output


def test_format_match_omits_skill_detail_block_when_skills_factor_detail_is_empty() -> None:
    """When detail is empty the skill_block is suppressed; the factor summary line still renders."""
    match = _match_with_skills_factor("")

    output = _format_match(1, match)

    # Factor summary still prints (e.g. "- skills: 1 matched ...").
    # The detail block ("     skills: <detail>") must be absent.
    assert "\n     skills: " not in output


def test_format_match_omits_skill_detail_block_when_no_skills_factor() -> None:
    """No dedicated skill-detail block when no skills ExplanationFactor is present."""
    match = _match_without_skills_factor()

    output = _format_match(1, match)

    assert "\n     skills: " not in output


def test_format_match_shows_adjacent_substitution_in_skills_line() -> None:
    """Adjacency-substitution branch of the acceptance criterion is covered."""
    match = _match_adjacent_only()

    output = _format_match(1, match)

    assert "adjacent" in output
