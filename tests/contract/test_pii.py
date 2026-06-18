"""Contract suite for the `PIIScrubber` port (spec: `docs/tasks/00b-contracts.md`).

The structural invariants below hold for every scrubber. The null scrubber is identity, so
redaction-strength assertions (an email must not survive) belong to the real Presidio adapter's
own tests in Track C — they would, by design, fail for the null object and so are not part of
this shared suite. `build_matcher` fail-closed wiring keeps the null scrubber away from any LLM.
"""

from __future__ import annotations

import pytest

from staffeer.adapters.null_pii import NullPIIScrubber
from staffeer.ports.pii import PIIScrubber, ScrubbedText


@pytest.fixture
def scrubber() -> PIIScrubber:
    return NullPIIScrubber()


def test_implementation_satisfies_the_port(scrubber: PIIScrubber) -> None:
    assert isinstance(scrubber, PIIScrubber)


def test_scrub_returns_scrubbed_text(scrubber: PIIScrubber) -> None:
    assert isinstance(scrubber.scrub("a profile summary"), ScrubbedText)


def test_scrub_does_not_raise_on_arbitrary_input(scrubber: PIIScrubber) -> None:
    assert scrubber.scrub("").text == ""


def test_redactions_is_always_a_tuple(scrubber: PIIScrubber) -> None:
    assert isinstance(scrubber.scrub("email me at a@b.com").redactions, tuple)
