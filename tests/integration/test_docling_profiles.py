"""Integration tests for DoclingProfileParser (I10).

Exercises the real Docling adapter against a genuine PDF (skipped when none is
available) and against deliberately corrupt bytes to assert ProfileParseError.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from staffeer.adapters.docling_profiles import DoclingProfileParser
from staffeer.domain.errors import ProfileParseError
from staffeer.ports.profiles import ParsedProfile

_PROFILES_DIR = Path("planning/raw-data/profiles")


def test_parse_returns_parsed_profile(tmp_path: Path) -> None:
    # Arrange — skip when docling is not installed or no real PDFs are available.
    pytest.importorskip("docling", reason="docling is not installed")
    pdfs = list(_PROFILES_DIR.glob("*.pdf")) if _PROFILES_DIR.exists() else []
    if not pdfs:
        pytest.skip("No PDF profiles found in planning/raw-data/profiles/")
    first_pdf = pdfs[0]
    parser = DoclingProfileParser()
    # Act
    profile = parser.parse(first_pdf)
    # Assert
    assert isinstance(profile, ParsedProfile)
    assert profile.consultant_id == first_pdf.stem
    assert len(profile.text) > 0


def test_parse_unreadable_file_raises_profile_parse_error(tmp_path: Path) -> None:
    # Arrange
    bad_pdf = tmp_path / "bad.pdf"
    bad_pdf.write_bytes(b"not a valid pdf at all")
    parser = DoclingProfileParser()
    # Act / Assert
    with pytest.raises(ProfileParseError) as exc_info:
        parser.parse(bad_pdf)
    assert str(bad_pdf) in str(exc_info.value)
