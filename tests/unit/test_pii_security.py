"""Security negative-case tests — scrubbed text must contain no original PII (I9).

These tests deliberately assert what must NOT be present after scrubbing.  A 100 %
pass rate on positive scenarios alone is a coverage warning; these negative cases
prove the scrubber actually removes content rather than merely returning it.
"""

from __future__ import annotations

import pytest

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
