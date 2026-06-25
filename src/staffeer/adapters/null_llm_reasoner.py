"""Null-object adapter for the `LLMReasoner` port.

Abstains on every call — score 0.0, empty evidence, `abstained=True`.  Used when
LLM assessment is disabled or unconfigured; wired by the composition root.
"""

from __future__ import annotations

from staffeer.ports.reasoner import SoftAssessment


class NullLLMReasoner:
    """Null-object implementation — abstains with score 0.0 and no evidence."""

    def assess(self, *, consultant_summary: str, role_description: str) -> SoftAssessment:
        return SoftAssessment(
            score=0.0,
            confidence=0.0,
            evidence=(),
            cited_sources=(),
            summary="",
            abstained=True,
        )
