"""Presidio-backed `PIIScrubber` adapter — removes PII before text reaches an LLM.

Uses spaCy `en_core_web_sm` (not the default `en_core_web_lg`) via `NlpEngineProvider`
so that instantiation works in the project's lightweight venv. Presidio is imported lazily
inside `__init__` so the module loads even when the optional `nlp` extra is absent (the
composition root imports this class unconditionally). Infra failure is mapped to
`PIIScrubbingError` (fail-closed, `.claude/principles/security.md`).
"""

from __future__ import annotations

import logging

from staffeer.domain.errors import PIIScrubbingError
from staffeer.ports.pii import ScrubbedText

logger = logging.getLogger(__name__)

_NLP_CONFIG = {
    "nlp_engine_name": "spacy",
    "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
}


class PresidioPIIScrubber:
    """Scrubs PERSON and EMAIL_ADDRESS entities from free text using Presidio."""

    def __init__(self, entities: tuple[str, ...] = ("PERSON", "EMAIL_ADDRESS")) -> None:
        self._entities = entities
        try:
            from presidio_analyzer import AnalyzerEngine
            from presidio_analyzer.nlp_engine import NlpEngineProvider
            from presidio_anonymizer import AnonymizerEngine

            nlp_engine = NlpEngineProvider(nlp_configuration=_NLP_CONFIG).create_engine()
            self._analyzer = AnalyzerEngine(nlp_engine=nlp_engine)
            self._anonymizer = AnonymizerEngine()
        except Exception as exc:
            raise PIIScrubbingError("Presidio initialisation failed; see exception chain") from exc

    def scrub(self, text: str) -> ScrubbedText:
        """Return `text` with PII removed; log entity types found (never raw PII)."""
        try:
            results = self._analyzer.analyze(
                text=text, entities=list(self._entities), language="en"
            )
            anonymized = self._anonymizer.anonymize(text=text, analyzer_results=results)
            entity_types = [r.entity_type for r in results]
            logger.info("pii_entities_redacted", extra={"entity_types": entity_types})
            return ScrubbedText(text=anonymized.text, redactions=tuple(entity_types))
        except Exception as exc:
            raise PIIScrubbingError("PII scrubbing failed; see exception chain") from exc
