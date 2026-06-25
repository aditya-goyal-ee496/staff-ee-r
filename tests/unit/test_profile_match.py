"""Unit tests for staffeer.domain.profile_match — slice 05b (I3).

Covers profile_key and resolve_profile_stem, both pure functions with no I/O.
One assertion per test; AAA layout; no mocking.

RULE: domain core has NO I/O — these tests run without any adapters or fixtures.
"""

from __future__ import annotations

from staffeer.domain.profile_match import profile_key, resolve_profile_stem

# ---------------------------------------------------------------------------
# profile_key — _pp suffix
# ---------------------------------------------------------------------------


def test_profile_key_strips_pp_suffix() -> None:
    """profile_key('karan_mehta_pp') returns 'karan mehta'."""
    # Arrange
    stem = "karan_mehta_pp"
    # Act
    result = profile_key(stem)
    # Assert
    assert result == "karan mehta"


# ---------------------------------------------------------------------------
# profile_key — _nj suffix
# ---------------------------------------------------------------------------


def test_profile_key_strips_nj_suffix() -> None:
    """profile_key('aarav_nair_nj') returns 'aarav nair'."""
    # Arrange
    stem = "aarav_nair_nj"
    # Act
    result = profile_key(stem)
    # Assert
    assert result == "aarav nair"


# ---------------------------------------------------------------------------
# resolve_profile_stem — case-insensitive match
# ---------------------------------------------------------------------------


def test_resolve_profile_stem_case_insensitive() -> None:
    """resolve_profile_stem('Karan Mehta', ...) finds 'karan_mehta_pp' case-insensitively."""
    # Arrange
    name = "Karan Mehta"
    stems = ("karan_mehta_pp", "aarav_nair")
    # Act
    result = resolve_profile_stem(name, stems)
    # Assert
    assert result == "karan_mehta_pp"


# ---------------------------------------------------------------------------
# resolve_profile_stem — no match returns None
# ---------------------------------------------------------------------------


def test_resolve_profile_stem_no_match_returns_none() -> None:
    """resolve_profile_stem('Nobody Here', ...) returns None when no stem matches."""
    # Arrange
    name = "Nobody Here"
    stems = ("karan_mehta_pp",)
    # Act
    result = resolve_profile_stem(name, stems)
    # Assert
    assert result is None
