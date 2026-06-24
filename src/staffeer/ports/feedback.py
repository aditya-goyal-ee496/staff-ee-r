"""`FeedbackStore` port — retrieves client and internal feedback for a consultant.

The spec (`docs/tasks/00b-contracts.md`): `for_consultant(id)` returns a `Feedback`; a consultant
with no feedback yields an empty `Feedback`, never `None` and never fabricated notes. Client
feedback may be one-dimensional; internal EE feedback is richer on fit/hands-on ability (brief).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from staffeer.domain.models import ValueObject


class Feedback(ValueObject):
    """Collected feedback for one consultant, separated by source.

    Includes client feedback (one-dimensional), internal EE feedback (richer on fit/ability),
    and beach trajectory notes capturing ongoing performance on the beach.
    """

    consultant_id: str
    client_notes: tuple[str, ...] = ()
    internal_notes: tuple[str, ...] = ()
    beach_notes: tuple[str, ...] = ()


@runtime_checkable
class FeedbackStore(Protocol):
    """Looks up feedback for a consultant by id."""

    def for_consultant(self, consultant_id: str) -> Feedback:
        """Feedback for `consultant_id`; empty `Feedback` when none exists."""
        ...
