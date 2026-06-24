"""Docling-backed `ProfileParser` adapter.

Parses consultant profile PDFs using the Docling library. Docling is imported
lazily inside `parse` so the module can be imported even when Docling is absent.
Any infrastructure failure is mapped to `ProfileParseError` — raw exceptions
never escape the boundary.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from staffeer.domain.errors import ProfileParseError
from staffeer.ports.profiles import ParsedProfile


class DoclingProfileParser:
    """Implements `ProfileParser` using Docling to extract text from PDFs."""

    def parse(self, path: Path) -> ParsedProfile:
        """Parse *path* into a `ParsedProfile`, or raise `ProfileParseError`."""
        try:
            document = _convert_document(path)
            text = document.export_to_text()
            skills = _extract_skills(document)
        except Exception as exc:
            raise ProfileParseError(f"Cannot parse profile: {path}") from exc

        return ParsedProfile(
            consultant_id=path.stem,
            text=text,
            skills=skills,
            skills_verified=not path.stem.endswith("_nj"),
        )


def _convert_document(path: Path) -> Any:
    """Convert *path* to a Docling document object."""
    from docling.document_converter import DocumentConverter

    return DocumentConverter().convert(str(path)).document


def _extract_skills(document: Any) -> tuple[str, ...]:
    """Return skills mentioned in *document*; propagates exceptions to the caller."""
    texts = getattr(document, "texts", None) or []
    skills: list[str] = []
    for item in texts:
        label = str(getattr(item, "label", "")).lower()
        if "skill" in label:
            text = str(getattr(item, "text", "")).strip()
            if text:
                skills.append(text)
    return tuple(skills)
