"""CLI behaviour: roles list, matched shortlist, exclusions, and clean failure on bad input."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from staffeer.cli.main import app
from staffeer.domain.errors import StaffeerError

runner = CliRunner()

_REMOTE_ROLE = [
    "ROLE-1",
    "Engineer",
    "",
    "",
    "python",
    "2026-07-01",
    "Remote-India",
    "No",
    "High",
    "",
]
_CHENNAI_ROLE = ["ROLE-2", "SRE", "", "", "python", "2026-07-01", "Chennai", "No", "High", ""]
_SKILL_ROLE = [
    "ROLE-3",
    "Data Engineer",
    "",
    "",
    "python, sql",
    "2026-07-01",
    "Remote-India",
    "No",
    "High",
    "",
]
_ASHA = [1, "Asha Rao", "a@x.example", "Senior", "python, sql", "Chennai", "No", 5, ""]
_PUNE = [2, "Imran Khan", "i@x.example", "Senior", "python", "Pune", "No", 9, ""]
_PARTIAL_CONSULTANT = [3, "Priya Das", "p@x.example", "Mid", "python", "Chennai", "No", 3, ""]
_ADJACENT_CONSULTANT = [4, "Ravi Kumar", "r@x.example", "Senior", "java", "Chennai", "No", 2, ""]
_KOTLIN_ROLE = [
    "ROLE-4",
    "Kotlin Engineer",
    "",
    "",
    "kotlin",
    "2026-07-01",
    "Remote-India",
    "No",
    "High",
    "",
]


def test_roles_command_lists_an_open_role(workbook_factory: Callable[..., Path]) -> None:
    path = workbook_factory(roles=[_REMOTE_ROLE])
    result = runner.invoke(app, ["roles", "--data", str(path)])
    assert "ROLE-1" in result.stdout


def test_match_command_lists_an_eligible_consultant(workbook_factory: Callable[..., Path]) -> None:
    path = workbook_factory(roles=[_REMOTE_ROLE], beach=[_ASHA])
    result = runner.invoke(app, ["match", "ROLE-1", "--data", str(path)])
    assert "Asha Rao" in result.stdout


def test_match_command_exits_non_zero_for_an_unknown_role(
    workbook_factory: Callable[..., Path],
) -> None:
    path = workbook_factory(roles=[_REMOTE_ROLE])
    result = runner.invoke(app, ["match", "ROLE-404", "--data", str(path)])
    assert result.exit_code == 1


def test_show_excluded_reports_a_location_blocked_consultant(
    workbook_factory: Callable[..., Path],
) -> None:
    path = workbook_factory(roles=[_CHENNAI_ROLE], beach=[_PUNE])
    result = runner.invoke(app, ["match", "ROLE-2", "--data", str(path), "--show-excluded"])
    assert "Imran Khan" in result.stdout


def test_match_command_shows_skill_coverage_detail(workbook_factory: Callable[..., Path]) -> None:
    """Skill block renders matched skills and gap text when a consultant has partial coverage."""
    path = workbook_factory(roles=[_SKILL_ROLE], beach=[_PARTIAL_CONSULTANT])
    result = runner.invoke(app, ["match", "ROLE-3", "--data", str(path)])
    assert "matched" in result.stdout
    assert "missing" in result.stdout
    assert "adjacent" in result.stdout


def test_match_command_shows_adjacent_skill_substitution(
    workbook_factory: Callable[..., Path],
) -> None:
    """Skill summary shows a non-zero adjacent count when a consultant has an adjacent skill."""
    path = workbook_factory(roles=[_KOTLIN_ROLE], beach=[_ADJACENT_CONSULTANT])
    result = runner.invoke(app, ["match", "ROLE-4", "--data", str(path)])
    assert "1 adjacent" in result.stdout


def test_index_command_warns_when_supply_has_no_beach_consultants(
    workbook_factory: Callable[..., Path],
) -> None:
    """When the workbook has no beach supply the index command warns the operator on stderr."""
    path = workbook_factory()  # no beach rows
    mock_matcher = MagicMock()
    mock_matcher.supply.consultants.return_value = []
    mock_matcher.include_states = ()
    with patch("staffeer.cli.main.build_matcher", return_value=mock_matcher):
        result = runner.invoke(
            app, ["index", "--data", str(path)], env={"STAFFEER_MILVUS_PATH": "/tmp/test.db"}
        )
    assert "no beach consultants" in result.output


def test_index_command_exits_nonzero_when_build_matcher_raises_staffeer_error(
    workbook_factory: Callable[..., Path],
) -> None:
    """A StaffeerError from build_matcher (e.g. no PII scrubber) exits with code 1."""
    path = workbook_factory()
    with patch("staffeer.cli.main.build_matcher", side_effect=StaffeerError("fail closed")):
        result = runner.invoke(
            app, ["index", "--data", str(path)], env={"STAFFEER_MILVUS_PATH": "/tmp/test.db"}
        )
    assert result.exit_code == 1
