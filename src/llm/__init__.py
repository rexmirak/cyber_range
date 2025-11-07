"""
LLM Module for Cyber Range Scenario Deployer

Provides LLM-powered features:
- Scenario authoring and repair
- In-lab guidance
- Learning explanations
- RAG-based context retrieval
"""

from .adapter import OllamaAdapter, HintTier, LLMConfig
from .rag import LocalRAG, Document, SearchResult

__all__ = [
    "OllamaAdapter",
    "HintTier",
    "LLMConfig",
    "LocalRAG",
    "Document",
    "SearchResult",
]
