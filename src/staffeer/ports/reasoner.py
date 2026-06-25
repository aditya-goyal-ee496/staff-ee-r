"""`LLMReasoner` port — soft/LLM-based assessment of a consultant against a role.

Spec reference: `docs/tasks/00b-contracts.md` (C2-03).

The port decouples the domain core from any concrete LLM backend.  Every implementation
must satisfy the structural invariants verified by `tests/contract/test_reasoner.py`.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import Field, model_validator

from staffeer.domain.models import ValueObject


class LLMReasonerError(Exception):
    """Raised by an LLMReasoner implementation when the LLM call fails."""


class Evidence(ValueObject):
    """A single piece of evidence backing a soft assessment.

    Each item names its source so reasoning is always traceable (Principle 1).
    """

    source: str
    claim: str


class SoftAssessment(ValueObject):
    """The outcome of an LLM soft-assessment — a score with traceable reasoning."""

    score: float
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: tuple[Evidence, ...] = ()
    cited_sources: tuple[str, ...] = ()
    summary: str = ""
    abstained: bool = False

    @model_validator(mode="before")
    @classmethod
    def _low_confidence_abstains(cls, data: Any) -> Any:
        """When confidence < 0.3, force abstention and zero-out score/evidence."""
        if isinstance(data, dict) and data.get("confidence", 1.0) < 0.3:
            data["abstained"] = True
            data["score"] = 0.0
            data["evidence"] = ()
            data["cited_sources"] = ()
            data["summary"] = ""
        return data

    @model_validator(mode="after")
    def _non_abstaining_requires_summary(self) -> SoftAssessment:
        if not self.abstained and not self.summary:
            raise ValueError("non-abstaining SoftAssessment must have a non-empty summary")
        return self


@runtime_checkable
class LLMReasoner(Protocol):
    """Port: soft-assess a consultant against a role description using an LLM."""

    def assess(self, *, consultant_summary: str, role_description: str) -> SoftAssessment:
        """Return a `SoftAssessment`; never fabricate evidence when abstaining."""
        ...
