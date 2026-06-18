"""Skill canonicalisation behaviour: spellings, qualifiers, aliases, and adjacency."""

from __future__ import annotations

from staffeer.domain.skills import adjacent_alternatives, canonical_skill, canonical_skills


def test_canonical_skill_lower_cases_and_trims() -> None:
    assert canonical_skill("  Kubernetes ") == "kubernetes"


def test_canonical_skill_folds_a_known_alias() -> None:
    assert canonical_skill("k8s") == "kubernetes"


def test_canonical_skill_drops_a_proficiency_qualifier() -> None:
    assert canonical_skill("Kotlin (expert)") == "kotlin"


def test_canonical_skills_removes_duplicates_keeping_first_seen_order() -> None:
    assert canonical_skills(("Java", "k8s", "java")) == ("java", "kubernetes")


def test_java_is_an_accepted_substitute_for_a_kotlin_requirement() -> None:
    assert "java" in adjacent_alternatives("kotlin")
