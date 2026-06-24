"""Markdown-backed `FeedbackStore` adapter.

Reads per-consultant feedback from `{feedback_dir}/{consultant_id}.md`, splitting
content by section headings into client, internal EE, and beach trajectory notes.
An absent file yields empty `Feedback`; any I/O or parse error raises `FeedbackError`.
"""

from __future__ import annotations

from pathlib import Path

from staffeer.domain.errors import FeedbackError
from staffeer.ports.feedback import Feedback

_HEADING_CLIENT = "## Client feedback"
_HEADING_INTERNAL = "## Internal EE feedback"
_HEADING_BEACH = "## Beach trajectory"

_SECTION_HEADINGS = (_HEADING_CLIENT, _HEADING_INTERNAL, _HEADING_BEACH)


def _parse_feedback(raw: str) -> dict[str, tuple[str, ...]]:
    sections: dict[str, list[str]] = {h: [] for h in _SECTION_HEADINGS}
    current: str | None = None
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped in _SECTION_HEADINGS:
            current = stripped
        elif current is not None and stripped:
            sections[current].append(stripped)
    return {h: tuple(lines) for h, lines in sections.items()}


class MarkdownFeedbackStore:
    """Loads consultant feedback from per-consultant markdown files."""

    def __init__(self, feedback_dir: Path) -> None:
        self._feedback_dir = feedback_dir

    def for_consultant(self, consultant_id: str) -> Feedback:
        """Return `Feedback` for `consultant_id`; empty when no file exists."""
        path = self._feedback_dir / f"{consultant_id}.md"
        if not path.exists():
            return Feedback(consultant_id=consultant_id)
        try:
            raw = path.read_text(encoding="utf-8")
            sections = _parse_feedback(raw)
        except (OSError, ValueError) as exc:
            raise FeedbackError(f"Cannot load feedback: {path}") from exc
        return Feedback(
            consultant_id=consultant_id,
            client_notes=sections[_HEADING_CLIENT],
            internal_notes=sections[_HEADING_INTERNAL],
            beach_notes=sections[_HEADING_BEACH],
        )
