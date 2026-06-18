"""Null-object `FeedbackStore` — satisfies the port with no stored feedback.

The default wiring until the markdown feedback loader lands (Track B). Returns an empty
`Feedback` for every consultant; it never fabricates notes.
"""

from __future__ import annotations

from staffeer.ports.feedback import Feedback


class NullFeedbackStore:
    """Returns empty `Feedback` for any consultant id."""

    def for_consultant(self, consultant_id: str) -> Feedback:
        """Return empty feedback keyed by `consultant_id`."""
        return Feedback(consultant_id=consultant_id)
