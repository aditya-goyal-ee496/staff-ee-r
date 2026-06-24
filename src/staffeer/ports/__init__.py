"""Ports: Protocols the domain core depends on; implemented by adapters. No concrete logic."""

from staffeer.ports.reasoner import (
    Evidence,
    LLMReasoner,
    NullLLMReasoner,
    SoftAssessment,
)
from staffeer.ports.semantic_index import (
    Hit,
    IndexItem,
    NullSemanticIndex,
    SemanticIndex,
)

__all__ = [
    "Evidence",
    "Hit",
    "IndexItem",
    "LLMReasoner",
    "NullLLMReasoner",
    "NullSemanticIndex",
    "SemanticIndex",
    "SoftAssessment",
]
