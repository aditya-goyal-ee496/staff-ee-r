"""Unit tests for IngestionService — scrubbing is mandatory on every path (I14).

Uses null adapters for parser and feedback; spies on the scrubber to assert that
scrub() is called exactly once for each ingest operation.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from staffeer.adapters.null_feedback import NullFeedbackStore
from staffeer.adapters.null_profiles import NullProfileParser
from staffeer.domain.ingestion import IngestionService
from staffeer.ports.pii import PIIScrubber, ScrubbedText


@pytest.fixture
def spy_scrubber() -> PIIScrubber:
    """A MagicMock that satisfies PIIScrubber and always returns an empty ScrubbedText."""
    mock = MagicMock(spec=PIIScrubber)
    mock.scrub.return_value = ScrubbedText(text="x", redactions=())
    return mock


def test_ingest_profile_calls_scrubber(spy_scrubber: PIIScrubber, tmp_path: Path) -> None:
    # Arrange
    service = IngestionService(
        parser=NullProfileParser(),
        feedback=NullFeedbackStore(),
        scrubber=spy_scrubber,
    )
    # Act
    service.ingest_profile(tmp_path / "C-01.pdf")
    # Assert
    assert spy_scrubber.scrub.call_count == 1  # type: ignore[union-attr]


def test_ingest_feedback_calls_scrubber(spy_scrubber: PIIScrubber) -> None:
    # Arrange
    service = IngestionService(
        parser=NullProfileParser(),
        feedback=NullFeedbackStore(),
        scrubber=spy_scrubber,
    )
    # Act
    service.ingest_feedback("C-01")
    # Assert
    assert spy_scrubber.scrub.call_count == 1  # type: ignore[union-attr]
