"""Shared test support — build a demand-supply workbook matching the real tab layout.

The `workbook_factory` fixture writes a temporary `.xlsx` with the same title/header structure
as the Parity Partners workbook, so adapter tests and the supply-demand contract suite exercise
the real parser without depending on the git-ignored production data.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import openpyxl
import pytest

_HEADERS: dict[str, list[str]] = {
    "Open Roles": [
        "Role ID",
        "Title",
        "Client",
        "Sector",
        "Required Skills",
        "Start",
        "Location",
        "Co-location",
        "Priority",
        "Notes",
    ],
    "Beach": [
        "#",
        "Name",
        "Email",
        "Grade",
        "Key Skills",
        "Location",
        "Chennai-open",
        "Days on Beach",
        "Notes",
    ],
    "Rolling Off": [
        "#",
        "Name",
        "Email",
        "Grade",
        "Key Skills",
        "Current Client",
        "Roll-off Date",
        "Confidence",
        "Location",
        "Chennai-open",
        "Notes",
    ],
    "New Joiners": [
        "#",
        "Name",
        "Email",
        "Grade",
        "Key Skills (from CV)",
        "Join Date",
        "Location",
        "Chennai-open",
        "Notes",
    ],
}


def _write_workbook(
    path: Path,
    as_of: str,
    rows_by_sheet: dict[str, Sequence[Sequence[Any]]],
) -> Path:
    workbook = openpyxl.Workbook()
    workbook.remove(workbook.active)
    for sheet, header in _HEADERS.items():
        worksheet = workbook.create_sheet(sheet)
        worksheet.append([f"{sheet} - test - as of {as_of} (synthetic)"])
        worksheet.append(header)
        for row in rows_by_sheet.get(sheet, ()):
            worksheet.append(list(row))
    workbook.save(path)
    return path


@pytest.fixture
def workbook_factory(tmp_path: Path) -> Callable[..., Path]:
    """Return a builder that writes a demand-supply workbook from the given tab rows."""

    def build(
        *,
        as_of: str = "2026-06-01",
        roles: Sequence[Sequence[Any]] = (),
        beach: Sequence[Sequence[Any]] = (),
        rolling: Sequence[Sequence[Any]] = (),
        joiners: Sequence[Sequence[Any]] = (),
    ) -> Path:
        return _write_workbook(
            tmp_path / "demand-supply.xlsx",
            as_of,
            {
                "Open Roles": roles,
                "Beach": beach,
                "Rolling Off": rolling,
                "New Joiners": joiners,
            },
        )

    return build
