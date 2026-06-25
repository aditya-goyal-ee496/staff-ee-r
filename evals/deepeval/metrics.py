"""DeepEval metric wrappers for relevance and faithfulness.

Both metrics wrap a DeepEval LLM-judge.  Thresholds default to values well below 1.0
because a score of exactly 1.0 is a coverage WARNING, not a success signal (ADR-001).

deepeval is an optional extra; guard the import and raise a clear error when absent.
The deepeval package import is deferred to method call time to avoid module-level
circular-import issues caused by the evals/deepeval/ local package name.
"""

from __future__ import annotations

from evals.deepeval.judge_prompts import FAITHFULNESS_JUDGE_PROMPT, RELEVANCE_JUDGE_PROMPT


def _load_deepeval():  # type: ignore[no-untyped-def]
    """Import deepeval at call time; raise a clear error when the extra is absent."""
    try:
        import importlib

        geval_mod = importlib.import_module("deepeval.metrics.g_eval")
        tc_mod = importlib.import_module("deepeval.test_case")
        return geval_mod.GEval, tc_mod.LLMTestCase, tc_mod.LLMTestCaseParams
    except ImportError as exc:
        raise RuntimeError("deepeval is not installed. Run: uv sync --extra eval") from exc


class RelevanceMetric:
    """Score how relevant a shortlist is to a role (0.0–1.0).

    A score of 1.0 is a coverage WARNING — scenarios may be too easy.
    """

    def __init__(self, threshold: float = 0.7) -> None:
        self.threshold = threshold

    def measure(self, shortlist: list[str], role_description: str) -> float:
        """Return a relevance score using the versioned RELEVANCE_JUDGE_PROMPT."""
        GEval, LLMTestCase, LLMTestCaseParams = _load_deepeval()
        prompt = RELEVANCE_JUDGE_PROMPT.format(
            role_description=role_description,
            shortlist=", ".join(shortlist) if shortlist else "(empty)",
        )
        metric = GEval(
            name="Relevance",
            criteria=prompt,
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            threshold=self.threshold,
        )
        test_case = LLMTestCase(
            input=role_description,
            actual_output=", ".join(shortlist) if shortlist else "(empty)",
        )
        metric.measure(test_case)
        if metric.score is None:
            raise ValueError(
                f"RelevanceMetric: GEval returned no score for role '{role_description[:60]}'"
            )
        return float(metric.score)


class FaithfulnessMetric:
    """Score whether rationale claims are grounded in consultant skills (0.0–1.0).

    A score of 1.0 is a coverage WARNING — rationale may be trivially verifiable.
    """

    def __init__(self, threshold: float = 0.6) -> None:
        self.threshold = threshold

    @staticmethod
    def _format_rationale(rationale: dict[str, list[str]]) -> str:
        """Flatten rationale dict to a single string for the judge prompt."""
        return "; ".join(f"{name}: {', '.join(factors)}" for name, factors in rationale.items())

    def measure(self, rationale: dict[str, list[str]], consultant_profile: str) -> float:
        """Return a faithfulness score using the versioned FAITHFULNESS_JUDGE_PROMPT."""
        GEval, LLMTestCase, LLMTestCaseParams = _load_deepeval()
        rationale_text = self._format_rationale(rationale)
        prompt = FAITHFULNESS_JUDGE_PROMPT.format(
            consultant_profile=consultant_profile,
            rationale=rationale_text,
        )
        metric = GEval(
            name="Faithfulness",
            criteria=prompt,
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            threshold=self.threshold,
        )
        test_case = LLMTestCase(input=consultant_profile, actual_output=rationale_text)
        metric.measure(test_case)
        if metric.score is None:
            raise ValueError(
                "FaithfulnessMetric: GEval returned no score for profile "
                f"'{consultant_profile[:60]}'"
            )
        return float(metric.score)
