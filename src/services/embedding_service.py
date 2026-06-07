"""
Embedding service.

Wraps ``sentence-transformers`` to convert text chunks into vectors.
Model is loaded once and reused (singleton pattern).
"""

from __future__ import annotations

from typing import List

import numpy as np
from sentence_transformers import SentenceTransformer

from src.config import config


class EmbeddingProvider:
    """Converts text to embedding vectors using a local model."""

    def __init__(self, model_name: str | None = None) -> None:
        if model_name is None:
            model_name = config.embedding_model_name
        self._model = SentenceTransformer(model_name)

    def embed(self, texts: List[str]) -> np.ndarray:
        """Return array of shape (len(texts), embedding_dim)."""
        return self._model.encode(texts, show_progress_bar=False)

    @property
    def dim(self) -> int:
        return self._model.get_sentence_embedding_dimension()


# Singleton
_instance: EmbeddingProvider | None = None


def get_embedding_provider() -> EmbeddingProvider:
    global _instance
    if _instance is None:
        _instance = EmbeddingProvider()
    return _instance
