"""Unit tests for parse_free_text_role (I06-05) with a stubbed DSPy predictor.

Six one-assertion AAA tests — no network, no real LLM. DSPy is patched at
dspy.Predict.__call__ to return a fixed namespace.  If dspy is not installed the
entire module is skipped (pytest.importorskip).
"""

from __future__ import annotations

import types
from unittest.mock import MagicMock

import pytest

dspy = pytest.importorskip("dspy")

from staffeer.adapters.dspy_openrouter import parse_free_text_role  # noqa: E402


def _fixed_prediction(**_kwargs: object) -> types.SimpleNamespace:
    """Return a fixed DSPy prediction namespace (no network)."""
    return types.SimpleNamespace(
        title="Backend Engineer",
        location="Remote-India",
        required_skills="python, sql",
        seniority="senior",
        co_location=False,
    )


@pytest.fixture(autouse=True)
def _patch_dspy_predict(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch dspy.Predict so __call__ returns the fixed namespace."""
    mock_predict = MagicMock(side_effect=_fixed_prediction)
    mock_predict_cls = MagicMock(return_value=mock_predict)
    monkeypatch.setattr(dspy, "Predict", mock_predict_cls)
    # Also patch dspy.LM so configure() does not attempt a real network call
    mock_lm = MagicMock()
    monkeypatch.setattr(dspy, "LM", MagicMock(return_value=mock_lm))
    monkeypatch.setattr(dspy, "configure", MagicMock())


def test_parse_free_text_role_title_is_backend_engineer() -> None:
    # Arrange
    free_text = "We need a senior backend engineer with Python and SQL skills."
    # Act
    role = parse_free_text_role(free_text, api_key="fake-key")
    # Assert
    assert role.title == "Backend Engineer"


def test_parse_free_text_role_required_skills_contains_python_and_sql() -> None:
    # Arrange
    free_text = "We need a senior backend engineer with Python and SQL skills."
    # Act
    role = parse_free_text_role(free_text, api_key="fake-key")
    # Assert
    assert "python" in role.required_skills and "sql" in role.required_skills


def test_parse_free_text_role_empty_title_raises_value_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange — override the patch to return an empty title
    def _empty_title(**_kwargs: object) -> types.SimpleNamespace:
        return types.SimpleNamespace(
            title="",
            location="Remote-India",
            required_skills="python",
            seniority="mid",
            co_location=False,
        )

    mock_predict = MagicMock(side_effect=_empty_title)
    mock_predict_cls = MagicMock(return_value=mock_predict)
    monkeypatch.setattr(dspy, "Predict", mock_predict_cls)
    # Act / Assert
    with pytest.raises(ValueError, match="free-text parse produced no role title"):
        parse_free_text_role("something vague", api_key="fake-key")


def test_parse_free_text_role_skills_are_stripped_of_whitespace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange — skills with surrounding whitespace
    def _spaced_skills(**_kwargs: object) -> types.SimpleNamespace:
        return types.SimpleNamespace(
            title="Engineer",
            location="Remote-India",
            required_skills="  python  ,  sql  ",
            seniority="mid",
            co_location=False,
        )

    mock_predict = MagicMock(side_effect=_spaced_skills)
    mock_predict_cls = MagicMock(return_value=mock_predict)
    monkeypatch.setattr(dspy, "Predict", mock_predict_cls)
    # Act
    role = parse_free_text_role("build an API", api_key="fake-key")
    # Assert
    assert all(skill == skill.strip() for skill in role.required_skills)


def test_parse_free_text_role_blank_location_defaults_to_remote_india(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange — LLM returns a blank location
    def _blank_location(**_kwargs: object) -> types.SimpleNamespace:
        return types.SimpleNamespace(
            title="Engineer",
            location="",
            required_skills="python",
            seniority="mid",
            co_location=False,
        )

    mock_predict = MagicMock(side_effect=_blank_location)
    mock_predict_cls = MagicMock(return_value=mock_predict)
    monkeypatch.setattr(dspy, "Predict", mock_predict_cls)
    # Act
    role = parse_free_text_role("engineer with python", api_key="fake-key")
    # Assert
    assert role.location == "Remote-India"


def test_parse_free_text_role_llm_exception_raises_llm_reasoner_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange — DSPy call raises a network error
    mock_predict = MagicMock(side_effect=ConnectionError("network failure"))
    mock_predict_cls = MagicMock(return_value=mock_predict)
    monkeypatch.setattr(dspy, "Predict", mock_predict_cls)
    from staffeer.ports.reasoner import LLMReasonerError

    # Act / Assert
    with pytest.raises(LLMReasonerError, match="DSPy/network error during role parse"):
        parse_free_text_role("senior engineer", api_key="fake-key")
