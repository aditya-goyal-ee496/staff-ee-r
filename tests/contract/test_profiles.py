"""Contract suite for the `ProfileParser` port (spec: `docs/tasks/00b-contracts.md`)."""

from __future__ import annotations

from pathlib import Path

import pytest

from staffeer.adapters.null_profiles import NullProfileParser
from staffeer.ports.profiles import ParsedProfile, ProfileParser


@pytest.fixture
def parser() -> ProfileParser:
    return NullProfileParser()


def test_implementation_satisfies_the_port(parser: ProfileParser) -> None:
    assert isinstance(parser, ProfileParser)


def test_parse_returns_a_parsed_profile(parser: ProfileParser, tmp_path: Path) -> None:
    profile = parser.parse(tmp_path / "C-01.pdf")
    assert isinstance(profile, ParsedProfile)


def test_parse_fabricates_no_skills_it_did_not_read(parser: ProfileParser, tmp_path: Path) -> None:
    # The null parser reads nothing, so it must invent no skills (Principle 5).
    profile = parser.parse(tmp_path / "C-01.pdf")
    assert profile.skills == ()


# I3 — skills_verified contract tests (Slice 04)


def test_skills_verified_defaults_true() -> None:
    # Arrange / Act
    profile = ParsedProfile(consultant_id="C-01")
    # Assert
    assert profile.skills_verified is True


def test_null_parser_sets_skills_verified_true(tmp_path: Path) -> None:
    # Arrange
    parser = NullProfileParser()
    # Act
    profile = parser.parse(tmp_path / "C-01.pdf")
    # Assert
    assert profile.skills_verified is True
