"""Ranking behaviour: contributions sum into a score; matches order best-first with tie-breaks."""

from __future__ import annotations

from staffeer.domain.models import Consultant, Match, ScoreContribution, SkillScore
from staffeer.domain.ranking import assemble_match, rank, skill_contribution


def _consultant(consultant_id: str, name: str) -> Consultant:
    return Consultant(id=consultant_id, name=name, location="Chennai")


def _match(name: str, score: float) -> Match:
    return Match(consultant=_consultant(name[:3].upper(), name), score=score)


def test_skill_contribution_carries_the_coverage_value() -> None:
    contribution = skill_contribution(SkillScore(value=0.5), weight=2.0)
    assert contribution.weighted == 1.0


def test_assemble_match_sums_weighted_contributions_into_the_score() -> None:
    match = assemble_match(
        _consultant("C-01", "Asha"),
        (
            ScoreContribution(source="skills", value=0.5, weight=2.0),
            ScoreContribution(source="feedback", value=0.25),
        ),
    )
    assert match.score == 1.25


def test_rank_orders_the_higher_score_first() -> None:
    ranked = rank((_match("Asha", 0.4), _match("Bina", 0.9)))
    assert ranked[0].consultant.name == "Bina"


def test_rank_breaks_score_ties_by_consultant_name() -> None:
    ranked = rank((_match("Bina", 0.5), _match("Asha", 0.5)))
    assert [match.consultant.name for match in ranked] == ["Asha", "Bina"]
