"""Integration tests for DspyOpenRouterReasoner (I06-14).

Requires OPENROUTER_API_KEY in the environment. Both tests are gated on
pytest.mark.integration and the full module is skipped when the key is absent.

Module docstring note: set OPENROUTER_API_KEY before running these tests.
These tests make a real network call to OpenRouter; do not run in CI without
a funded key.
"""

from __future__ import annotations

import os

import pytest

dspy = pytest.importorskip("dspy")

_API_KEY = os.environ.get("OPENROUTER_API_KEY")
pytestmark = pytest.mark.skipif(
    not _API_KEY,
    reason="OPENROUTER_API_KEY not set — integration tests skipped",
)


@pytest.mark.integration
def test_dspy_reasoner_returns_soft_assessment() -> None:
    """DspyOpenRouterReasoner.assess() returns a SoftAssessment (real network call)."""
    # Arrange
    from staffeer.adapters.dspy_openrouter import DspyOpenRouterReasoner  # noqa: PLC0415
    from staffeer.ports.reasoner import SoftAssessment  # noqa: PLC0415

    reasoner = DspyOpenRouterReasoner(api_key=_API_KEY)  # type: ignore[arg-type]
    # Act
    result = reasoner.assess(
        consultant_summary="Experienced backend engineer, Python and Django, 5 years.",
        role_description="Backend engineer role in Python, building REST APIs.",
    )
    # Assert
    assert isinstance(result, SoftAssessment)


@pytest.mark.integration
def test_dspy_reasoner_confidence_within_unit_interval() -> None:
    """DspyOpenRouterReasoner.assess() returns confidence in [0.0, 1.0]."""
    # Arrange
    from staffeer.adapters.dspy_openrouter import DspyOpenRouterReasoner  # noqa: PLC0415

    reasoner = DspyOpenRouterReasoner(api_key=_API_KEY)  # type: ignore[arg-type]
    # Act
    result = reasoner.assess(
        consultant_summary="Data scientist with pandas, sklearn, and PyTorch.",
        role_description="ML engineer to build recommendation models.",
    )
    # Assert
    assert 0.0 <= result.confidence <= 1.0
