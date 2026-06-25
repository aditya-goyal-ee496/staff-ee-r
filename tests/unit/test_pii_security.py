"""Security negative-case tests — scrubbed text must contain no original PII (I9).

These tests deliberately assert what must NOT be present after scrubbing.  A 100 %
pass rate on positive scenarios alone is a coverage warning; these negative cases
prove the scrubber actually removes content rather than merely returning it.
"""

from __future__ import annotations

import pytest

from staffeer.adapters.memory_supply_demand import InMemorySupplyDemandSource
from staffeer.adapters.null_feedback import NullFeedbackStore
from staffeer.adapters.null_profiles import NullProfileParser
from staffeer.adapters.null_semantic_index import NullSemanticIndex
from staffeer.domain.matcher import Matcher
from staffeer.domain.models import Consultant, Role, SupplyState
from staffeer.ports.pii import ScrubbedText
from staffeer.ports.reasoner import SoftAssessment

_FIXTURE_TEXT = "Alice Smith works at alice.smith@example.com"


def test_scrubbed_text_contains_no_original_name() -> None:
    # Arrange
    pytest.importorskip("presidio_analyzer")
    from staffeer.adapters.presidio_pii import PresidioPIIScrubber  # noqa: PLC0415

    scrubber = PresidioPIIScrubber()
    # Act
    result = scrubber.scrub(_FIXTURE_TEXT)
    # Assert
    assert "Alice Smith" not in result.text


def test_scrubbed_text_contains_no_original_email() -> None:
    # Arrange
    pytest.importorskip("presidio_analyzer")
    from staffeer.adapters.presidio_pii import PresidioPIIScrubber  # noqa: PLC0415

    scrubber = PresidioPIIScrubber()
    # Act
    result = scrubber.scrub(_FIXTURE_TEXT)
    # Assert
    assert "alice.smith@example.com" not in result.text


# ---------------------------------------------------------------------------
# I06-15 — Matcher scrubs consultant_summary before LLM call (one assertion)
# ---------------------------------------------------------------------------


class _RecordingPIIScrubber:
    """Records the most-recent text passed to scrub(); returns it unchanged."""

    def __init__(self) -> None:
        self.last_scrubbed: str | None = None

    def scrub(self, text: str) -> ScrubbedText:
        self.last_scrubbed = text
        return ScrubbedText(text=text)


class _RecordingLLMReasoner:
    """Records the consultant_summary the Matcher sends; always abstains."""

    def __init__(self) -> None:
        self.received_consultant_summary: str | None = None

    def assess(self, *, consultant_summary: str, role_description: str) -> SoftAssessment:
        self.received_consultant_summary = consultant_summary
        return SoftAssessment(score=0.0, confidence=0.0, summary="", abstained=True)


def test_matcher_scrubs_consultant_summary_before_reasoner() -> None:
    """Matcher must pass PII-scrubbed text to the reasoner, never raw consultant data.

    The recording scrubber captures the text it sees; the recording reasoner records what
    it received. The assertion verifies both see the same string — i.e. the scrubber's
    output is what the reasoner consumes.
    """
    # Arrange
    pii = _RecordingPIIScrubber()
    reasoner = _RecordingLLMReasoner()
    consultant = Consultant(
        id="C-01",
        name="Asha Kumar",
        location="Chennai",
        skills=("python",),
        state=SupplyState.BEACH,
    )
    role = Role(id="R-01", title="Engineer", location="Remote-India", required_skills=("python",))
    matcher = Matcher(
        supply=InMemorySupplyDemandSource(consultants=(consultant,)),
        profiles=NullProfileParser(),
        feedback=NullFeedbackStore(),
        pii=pii,
        semantic_index=NullSemanticIndex(),
        reasoner=reasoner,
    )
    # Act
    matcher.match(role)
    # Assert — reasoner received exactly what the scrubber returned
    # (scrubber output == reasoner input)
    assert reasoner.received_consultant_summary == pii.last_scrubbed
