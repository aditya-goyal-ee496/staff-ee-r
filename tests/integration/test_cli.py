"""CLI behaviour: roles list, matched shortlist, exclusions, and clean failure on bad input."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from typer.testing import CliRunner

from staffeer.cli.main import app

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
_ASHA = [1, "Asha Rao", "a@x.example", "Senior", "python, sql", "Chennai", "No", 5, ""]
_PUNE = [2, "Imran Khan", "i@x.example", "Senior", "python", "Pune", "No", 9, ""]


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
