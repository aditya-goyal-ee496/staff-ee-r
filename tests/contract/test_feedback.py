"""Contract suite for the `FeedbackStore` port (spec: `docs/tasks/00b-contracts.md`)."""

from __future__ import annotations

import pytest

from staffeer.adapters.null_feedback import NullFeedbackStore
from staffeer.ports.feedback import Feedback, FeedbackStore


@pytest.fixture
def store() -> FeedbackStore:
    return NullFeedbackStore()


def test_implementation_satisfies_the_port(store: FeedbackStore) -> None:
    assert isinstance(store, FeedbackStore)


def test_for_consultant_returns_feedback_keyed_by_id(store: FeedbackStore) -> None:
    assert store.for_consultant("C-01").consultant_id == "C-01"


def test_consultant_with_no_feedback_yields_empty_client_notes(store: FeedbackStore) -> None:
    assert store.for_consultant("C-01").client_notes == ()


def test_consultant_with_no_feedback_yields_empty_internal_notes(store: FeedbackStore) -> None:
    # Absence of feedback must not be fabricated into notes (Principle 5).
    assert store.for_consultant("C-01").internal_notes == ()


def test_returned_value_is_a_feedback(store: FeedbackStore) -> None:
    assert isinstance(store.for_consultant("C-01"), Feedback)


# I4 — beach_notes contract tests (Slice 04)


def test_beach_notes_defaults_empty() -> None:
    # Arrange / Act
    feedback = Feedback(consultant_id="C-01")
    # Assert
    assert feedback.beach_notes == ()


def test_null_store_beach_notes_is_empty() -> None:
    # Arrange
    store = NullFeedbackStore()
    # Act
    result = store.for_consultant("C-01")
    # Assert
    assert result.beach_notes == ()
