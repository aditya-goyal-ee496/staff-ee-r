"""Integration tests for MarkdownFeedbackStore (I11).

Verifies absent-file, beach_notes population, and OSError mapping to FeedbackError.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from staffeer.adapters.markdown_feedback import MarkdownFeedbackStore
from staffeer.domain.errors import FeedbackError

_BEACH_MARKDOWN = """\
## Client feedback
Delivered well on project Alpha.

## Internal EE feedback
Good communicator, strong on TDD.

## Beach trajectory
Completed Python advanced course.
Working on Kubernetes certification.
"""


def test_absent_file_returns_empty_feedback(tmp_path: Path) -> None:
    # Arrange
    store = MarkdownFeedbackStore(tmp_path)
    # Act
    result = store.for_consultant("X")
    # Assert
    assert result.consultant_id == "X"
    assert result.client_notes == ()
    assert result.internal_notes == ()
    assert result.beach_notes == ()


def test_beach_notes_populated_from_section(tmp_path: Path) -> None:
    # Arrange
    (tmp_path / "C-01.md").write_text(_BEACH_MARKDOWN)
    store = MarkdownFeedbackStore(tmp_path)
    # Act
    result = store.for_consultant("C-01")
    # Assert — two non-blank lines under ## Beach trajectory
    assert len(result.beach_notes) == 2


def test_malformed_file_raises_feedback_error(tmp_path: Path) -> None:
    # Arrange
    feedback_path = tmp_path / "C-01.md"
    feedback_path.write_text("placeholder")
    store = MarkdownFeedbackStore(tmp_path)
    # Act / Assert — patch read_text to raise OSError at the boundary
    with (
        patch.object(Path, "read_text", side_effect=OSError("disk error")),
        pytest.raises(FeedbackError),
    ):
        store.for_consultant("C-01")
