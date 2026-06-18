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
