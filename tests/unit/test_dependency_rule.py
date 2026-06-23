"""Architecture guard: the domain core imports no adapters, CLI, config, or I/O libraries.

This keeps the fan-out boundary stable — domain stays pure so tracks build against it in
parallel (`docs/rules/hexagonal-architecture.md`).
"""

from __future__ import annotations

from pathlib import Path

import pytest

_DOMAIN_DIR = Path(__file__).resolve().parents[2] / "src" / "staffeer" / "domain"
_FORBIDDEN = (
    "staffeer.adapters",
    "staffeer.cli",
    "staffeer.config",
    "openpyxl",
    "docling",
    "presidio",
    "pymilvus",
    "dspy",
)


@pytest.mark.parametrize("module", sorted(_DOMAIN_DIR.glob("*.py")), ids=lambda p: p.name)
def test_domain_module_has_no_outward_or_io_imports(module: Path) -> None:
    source = module.read_text()
    offenders = [name for name in _FORBIDDEN if name in source]
    assert offenders == []
