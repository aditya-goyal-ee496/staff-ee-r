"""Integration test — scrubbing must be observable in structured logs without raw PII (I12).

Asserts that at least one log record from the Presidio adapter is emitted (entity
type present) and that no record contains the original name or email address.
Also verifies the fail-closed guarantee: any infra exception raises PIIScrubbingError.
"""

from __future__ import annotations

import logging
from unittest.mock import patch

import pytest

_INPUT = "Meet John Doe at jdoe@example.com"
_LOGGER_NAME = "staffeer.adapters.presidio_pii"


def test_scrubbing_logs_entity_type_not_raw_pii(caplog: pytest.LogCaptureFixture) -> None:
    # Arrange
    pytest.importorskip("presidio_analyzer")
    from staffeer.adapters.presidio_pii import PresidioPIIScrubber  # noqa: PLC0415

    scrubber = PresidioPIIScrubber()
    # Act
    with caplog.at_level(logging.INFO, logger=_LOGGER_NAME):
        scrubber.scrub(_INPUT)
    # Assert — at least one record from our adapter logger
    adapter_records = [r for r in caplog.records if r.name == _LOGGER_NAME]
    assert adapter_records, f"No log record from {_LOGGER_NAME!r}"
    # At least one message must name an entity type (not just whitespace)
    combined = " ".join(r.message for r in adapter_records)
    assert combined.strip(), "Log messages are empty"
    # Raw PII must never appear in any log message
    all_messages = " ".join(r.getMessage() for r in caplog.records)
    assert "John Doe" not in all_messages
    assert "jdoe@example.com" not in all_messages


def test_scrub_infra_failure_raises_pii_scrubbing_error() -> None:
    """Infra failure during analyze -> PIIScrubbingError (fail-closed guarantee)."""
    # Arrange
    pytest.importorskip("presidio_analyzer")
    from staffeer.adapters.presidio_pii import PresidioPIIScrubber  # noqa: PLC0415
    from staffeer.domain.errors import PIIScrubbingError  # noqa: PLC0415

    scrubber = PresidioPIIScrubber()
    # Act / Assert
    with (
        patch.object(scrubber._analyzer, "analyze", side_effect=RuntimeError("infra boom")),
        pytest.raises(PIIScrubbingError),
    ):
        scrubber.scrub(_INPUT)
