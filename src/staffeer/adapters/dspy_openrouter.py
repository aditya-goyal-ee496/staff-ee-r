"""`LLMReasoner` adapter — DSPy soft assessment via OpenRouter.

Implements the frozen `LLMReasoner` port using DSPy over OpenRouter. The adapter
transforms DSPy ChainOfThought reasoning into traceable `SoftAssessment` with
evidence links and cited source fields.

Spec reference: `docs/tasks/00b-contracts.md` (C2-03).
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from staffeer.domain.models import Role
    from staffeer.ports.pii import PIIScrubber

try:
    import structlog

    _log = structlog.get_logger(__name__)
except ImportError:
    import logging

    _log = logging.getLogger(__name__)

try:
    import dspy
except ImportError as e:
    raise ImportError(
        "dspy-ai is required to use DspyOpenRouterReasoner. Install with: pip install staffeer[llm]"
    ) from e

from staffeer.ports.reasoner import Evidence, LLMReasonerError, SoftAssessment

MIN_CONFIDENCE = 0.3


class RoleParseSignature(dspy.Signature):  # type: ignore[misc]
    """DSPy Signature for parsing free-text role descriptions into structured fields.

    Input is a free-text role description; outputs are extracted title, location,
    comma-separated required skills, seniority level, and co-location flag.
    """

    free_text: str = dspy.InputField(desc="Free-text role description")
    title: str = dspy.OutputField(desc="Role title (e.g. 'Backend Engineer')")
    location: str = dspy.OutputField(desc="Role location (e.g. 'Remote-India', 'Chennai')")
    required_skills: str = dspy.OutputField(
        desc="Comma-separated list of required technical skills"
    )
    seniority: str = dspy.OutputField(desc="Seniority level (e.g. 'junior', 'mid', 'senior')")
    co_location: bool = dspy.OutputField(desc="True if role requires co-location; else False")


class FitAssessmentSignature(dspy.Signature):  # type: ignore[misc]
    """DSPy Signature for consultant-to-role fit assessment.

    Input fields describe the match context; output fields capture the assessment
    score, confidence, rationale, and evidence sources.
    """

    consultant_summary: str = dspy.InputField(
        desc="Consultant background, skills, experience, and availability state"
    )
    role_description: str = dspy.InputField(
        desc="Role requirements, seniority level, tech stack, and team location"
    )

    score: float = dspy.OutputField(desc="Numeric fit score in [0.0, 1.0]; 0=none, 1=perfect match")
    confidence: float = dspy.OutputField(
        desc="Confidence in the score, in [0.0, 1.0]; 0=guessing, 1=certain"
    )
    summary: str = dspy.OutputField(
        desc="Concise rationale for the score; cite specific matches/gaps"
    )
    cited_sources: str = dspy.OutputField(
        desc="Comma-separated list of source fields examined (e.g. 'profile,feedback,role_req')"
    )
    abstained: bool = dspy.OutputField(
        desc="True if assessment was refused due to insufficient data; else False"
    )


class DspyOpenRouterReasoner:
    """DSPy Predict reasoner over OpenRouter for soft consultant assessment.

    Wraps OpenRouter models via DSPy to produce structured, traceable fit scores
    backed by evidence. Transforms raw LLM output into the `SoftAssessment` contract.

    Each instance holds its own `dspy.LM` and uses `dspy.context` per call,
    avoiding mutation of the process-wide DSPy singleton.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "openai/gpt-4o-mini",
        temperature: float = 0.0,
    ) -> None:
        """Initialize with OpenRouter API key and optional model selection.

        Args:
            api_key: OpenRouter API key (required).
            model: OpenRouter model ID; defaults to openai/gpt-4o-mini.
            temperature: Sampling temperature; 0.0 for deterministic output.
        """
        if not api_key:
            raise ValueError("api_key is required and cannot be empty")

        self._model = model
        self._lm = dspy.LM(
            model=model,
            api_key=api_key,
            api_base="https://openrouter.ai/api/v1",
            temperature=temperature,
        )
        self._predictor = dspy.Predict(FitAssessmentSignature)

    def assess(self, *, consultant_summary: str, role_description: str) -> SoftAssessment:
        """Return a traceable `SoftAssessment` for consultant-role fit via DSPy.

        Args:
            consultant_summary: Scrubbed consultant background and skills (PII-free).
            role_description: Role requirements and context.

        Returns:
            SoftAssessment with score, confidence, evidence, and sources.

        Raises:
            LLMReasonerError: When the DSPy or network call fails.
        """
        output, latency_ms = self._call_predictor(consultant_summary, role_description)
        self._log_telemetry(output, latency_ms)
        return self._build_assessment(output)

    def _call_predictor(
        self, consultant_summary: str, role_description: str
    ) -> tuple[object, float]:
        """Invoke the DSPy predictor with the instance-local LM; return output and latency."""
        start = time.monotonic()
        try:
            with dspy.context(lm=self._lm):
                output = self._predictor(
                    consultant_summary=consultant_summary,
                    role_description=role_description,
                )
        except Exception as exc:
            _log.error(
                "dspy_reasoner_failed",
                model=self._model,
                error_type=type(exc).__name__,
            )
            raise LLMReasonerError(
                f"DSPy/network error during assessment: {type(exc).__name__}"
            ) from exc
        return output, (time.monotonic() - start) * 1000

    def _log_telemetry(self, output: object, latency_ms: float) -> None:
        """Log model, latency, and token counts; never touches PII fields."""
        usage: dict[str, object] = {}
        get_lm_usage = getattr(output, "get_lm_usage", None)
        if callable(get_lm_usage):
            usage = get_lm_usage() or {}
        _log.info(
            "dspy_reasoner_assessed",
            model=self._model,
            latency_ms=round(latency_ms, 1),
            prompt_tokens=usage.get("prompt_tokens") if isinstance(usage, dict) else None,
            completion_tokens=usage.get("completion_tokens") if isinstance(usage, dict) else None,
        )

    def _build_assessment(self, output: object) -> SoftAssessment:
        """Construct a SoftAssessment from raw DSPy predictor output."""
        confidence = max(0.0, min(1.0, self._parse_float(getattr(output, "confidence", 0.0), 0.0)))
        abstained = (
            self._parse_bool(getattr(output, "abstained", False), False)
            or confidence < MIN_CONFIDENCE
        )

        if abstained:
            return SoftAssessment(score=0.0, confidence=confidence, abstained=True)

        summary = str(getattr(output, "summary", "")).strip()
        cited_sources_str = str(getattr(output, "cited_sources", "")).strip()
        cited_sources = tuple(s.strip() for s in cited_sources_str.split(",") if s.strip())
        evidence: tuple[Evidence, ...] = (Evidence(source="llm_reasoning", claim=summary),)

        try:
            return SoftAssessment(
                score=self._parse_float(getattr(output, "score", 0.0), 0.0),
                confidence=confidence,
                evidence=evidence,
                cited_sources=cited_sources,
                summary=summary,
                abstained=False,
            )
        except ValueError as exc:
            raise LLMReasonerError(
                f"LLM output failed SoftAssessment validation: {type(exc).__name__}"
            ) from exc

    @staticmethod
    def _parse_float(value: str | float, default: float = 0.0) -> float:
        """Parse a float value, returning default if parsing fails."""
        if isinstance(value, float):
            return value
        try:
            return float(str(value).strip())
        except (ValueError, AttributeError):
            return default

    @staticmethod
    def _parse_bool(value: str | bool, default: bool = False) -> bool:
        """Parse a boolean value, returning default if parsing fails."""
        if isinstance(value, bool):
            return value
        s = str(value).strip().lower()
        if s in ("true", "yes", "1"):
            return True
        if s in ("false", "no", "0"):
            return False
        return default


def _extract_skills(skills_text: str) -> tuple[str, ...]:
    """Split a comma-separated skills string into stripped, non-empty skill tokens."""
    return tuple(s.strip() for s in skills_text.split(",") if s.strip())


def _normalise_location(raw: str) -> str:
    """Return the location, defaulting to 'Remote-India' when blank."""
    return raw.strip() or "Remote-India"


def _normalise_co_location(raw: str | bool) -> bool:
    """Coerce the LLM co-location output to a Python bool."""
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() in ("true", "yes", "1")


def parse_free_text_role(
    free_text: str,
    *,
    api_key: str,
    model: str = "openai/gpt-4o-mini",
    pii_scrubber: PIIScrubber | None = None,
) -> Role:
    """Parse a free-text role description into a `Role` via DSPy + OpenRouter.

    PII is scrubbed from `free_text` before it is sent to the LLM.  Pass a
    `PIIScrubber` instance; when omitted a `NullPIIScrubber` is used (only safe
    in tests — production callers must supply a real scrubber).

    Raises `ValueError` when the LLM returns no role title.
    Raises `LLMReasonerError` when the underlying DSPy / network call fails.
    Blank location defaults to 'Remote-India'.
    """
    from staffeer.adapters.null_pii import NullPIIScrubber  # noqa: PLC0415
    from staffeer.domain.models import Role  # noqa: PLC0415 — avoids circular at module top

    scrubber: PIIScrubber = pii_scrubber if pii_scrubber is not None else NullPIIScrubber()
    scrubbed_text: str = scrubber.scrub(free_text).text

    lm = dspy.LM(model=model, api_key=api_key, api_base="https://openrouter.ai/api/v1")
    try:
        with dspy.context(lm=lm):
            prediction = dspy.Predict(RoleParseSignature)(free_text=scrubbed_text)
    except Exception as exc:
        raise LLMReasonerError(f"DSPy/network error during role parse: {exc}") from exc

    title: str = (prediction.title or "").strip()
    if not title:
        raise ValueError("free-text parse produced no role title")

    return Role(
        id="FREE-TEXT",
        title=title,
        location=_normalise_location(prediction.location or ""),
        required_skills=_extract_skills(prediction.required_skills or ""),
        co_location=_normalise_co_location(prediction.co_location),
    )
