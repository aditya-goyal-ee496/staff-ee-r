"""Deterministic golden-table SCENARIO EVALS — Slice 05b: Profile-text embeddings.

Each scenario is a frozen fixture asserting the exact behaviour of the new
profile-mapping domain functions and index-wiring fallback logic.  No network
I/O; no real Docling or Milvus.

Scenarios
---------
1. profile_key_strips_pp_suffix
   profile_key('karan_mehta_pp') normalises to 'karan mehta'.

2. profile_key_strips_nj_suffix
   profile_key('aarav_nair_nj') normalises to 'aarav nair'.

3. profile_key_lowercases_and_replaces_underscores
   profile_key('PRIYA_DAS') normalises to 'priya das'.

4. resolve_profile_stem_case_insensitive_match
   resolve_profile_stem('Karan Mehta', ('karan_mehta_pp', 'aarav_nair'))
   returns 'karan_mehta_pp'.

5. resolve_profile_stem_no_match_returns_none
   resolve_profile_stem('Nobody Here', ('karan_mehta_pp',)) returns None.

6. [NEGATIVE] resolve_profile_stem_partial_name_does_not_match
   'Karan' alone must NOT match 'karan_mehta_pp'.
   This NEGATIVE scenario guards against substring/prefix false positives.
   A 100% pass rate without this scenario is a COVERAGE WARNING — it confirms
   the mapping requires an exact (normalised) key match, not a substring hit.

NOTE: A 100% pass rate across all scenarios (including scenario 6) is correct;
what would be a WARNING is *omitting* the negative scenario.
"""

from __future__ import annotations

from staffeer.domain.profile_match import profile_key, resolve_profile_stem

# ---------------------------------------------------------------------------
# Scenario 1 — profile_key strips _pp suffix
# ---------------------------------------------------------------------------


def test_profile_key_strips_pp_suffix() -> None:
    """profile_key normalises 'karan_mehta_pp' to 'karan mehta'."""
    # Arrange
    stem = "karan_mehta_pp"
    # Act
    key = profile_key(stem)
    # Assert
    assert key == "karan mehta"


# ---------------------------------------------------------------------------
# Scenario 2 — profile_key strips _nj suffix
# ---------------------------------------------------------------------------


def test_profile_key_strips_nj_suffix() -> None:
    """profile_key normalises 'aarav_nair_nj' to 'aarav nair'."""
    # Arrange
    stem = "aarav_nair_nj"
    # Act
    key = profile_key(stem)
    # Assert
    assert key == "aarav nair"


# ---------------------------------------------------------------------------
# Scenario 3 — profile_key lowercases and replaces underscores
# ---------------------------------------------------------------------------


def test_profile_key_lowercases_and_replaces_underscores() -> None:
    """profile_key lowercases the input and replaces underscores with spaces."""
    # Arrange
    stem = "PRIYA_DAS"
    # Act
    key = profile_key(stem)
    # Assert
    assert key == "priya das"


# ---------------------------------------------------------------------------
# Scenario 4 — resolve_profile_stem case-insensitive match
# ---------------------------------------------------------------------------


def test_resolve_profile_stem_case_insensitive_match() -> None:
    """resolve_profile_stem matches 'Karan Mehta' to 'karan_mehta_pp' case-insensitively."""
    # Arrange
    name = "Karan Mehta"
    stems = ("karan_mehta_pp", "aarav_nair")
    # Act
    result = resolve_profile_stem(name, stems)
    # Assert
    assert result == "karan_mehta_pp"


# ---------------------------------------------------------------------------
# Scenario 5 — resolve_profile_stem returns None when no stem matches
# ---------------------------------------------------------------------------


def test_resolve_profile_stem_no_match_returns_none() -> None:
    """resolve_profile_stem returns None when no stem key matches the consultant name."""
    # Arrange
    name = "Nobody Here"
    stems = ("karan_mehta_pp",)
    # Act
    result = resolve_profile_stem(name, stems)
    # Assert
    assert result is None


# ---------------------------------------------------------------------------
# Scenario 6 — NEGATIVE: partial name does NOT match a longer stem
#
# This is the mandatory NEGATIVE scenario.  Guards against substring/prefix
# false positives: 'Karan' must not match 'karan_mehta_pp'.  If the
# implementation used `in` instead of exact key equality this test would fail —
# which is exactly what we want.
# ---------------------------------------------------------------------------


def test_resolve_profile_stem_partial_name_does_not_match() -> None:
    """NEGATIVE: 'Karan' alone must not match 'karan_mehta_pp' (exact key required)."""
    # Arrange
    name = "Karan"
    stems = ("karan_mehta_pp",)
    # Act
    result = resolve_profile_stem(name, stems)
    # Assert — partial name must NOT produce a false-positive match
    assert result is None
