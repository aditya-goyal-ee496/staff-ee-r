"""Pure-domain ingestion service — composes parser, feedback store, and PII scrubber.

All profile and feedback text passes through `PIIScrubber` before leaving this service
(invariant I14: scrubbing mandatory, fail-closed). No I/O; depends only on ports.
"""

from __future__ import annotations

from pathlib import Path

from staffeer.ports.feedback import Feedback, FeedbackStore
from staffeer.ports.pii import PIIScrubber, ScrubbedText
from staffeer.ports.profiles import ParsedProfile, ProfileParser


class IngestionService:
    """Orchestrates profile parsing and feedback retrieval with mandatory PII scrubbing."""

    def __init__(
        self,
        parser: ProfileParser,
        feedback: FeedbackStore,
        scrubber: PIIScrubber,
    ) -> None:
        self._parser = parser
        self._feedback = feedback
        self._scrubber = scrubber

    def ingest_profile(self, path: Path) -> tuple[ParsedProfile, ScrubbedText]:
        """Parse a consultant profile and scrub PII from its text."""
        profile = self._parser.parse(path)
        scrubbed = self._scrubber.scrub(profile.text)
        return profile, scrubbed

    def ingest_feedback(self, consultant_id: str) -> tuple[Feedback, ScrubbedText]:
        """Retrieve consultant feedback and scrub PII from all notes."""
        fb = self._feedback.for_consultant(consultant_id)
        all_notes = fb.client_notes + fb.internal_notes + fb.beach_notes
        combined = " ".join(all_notes)
        scrubbed = self._scrubber.scrub(combined)
        return fb, scrubbed
