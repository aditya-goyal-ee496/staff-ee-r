"""Ports: Protocols the domain core depends on; implemented by adapters. No concrete logic."""

from staffeer.ports.reasoner import (
    Evidence,
    LLMReasoner,
    SoftAssessment,
)
from staffeer.ports.semantic_index import (
    Hit,
    IndexItem,
    SemanticIndex,
)

__all__ = [
    "Evidence",
    "Hit",
    "IndexItem",
    "LLMReasoner",
    "SemanticIndex",
    "SoftAssessment",
]
