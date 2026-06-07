"""
Cross-encoder reranker.

After fast cosine-similarity search returns broad candidates (top-20),
the cross-encoder re-scores each ``(query, chunk)`` pair for higher
precision, returning a narrower top-5.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from sentence_transformers import CrossEncoder

from src.config import config


class Reranker:
    """Re-rank chunks by query relevance."""

    def __init__(self, model_name: str | None = None) -> None:
        if model_name is None:
            model_name = config.reranker_model
        self._model = CrossEncoder(model_name)

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int | None = None,
    ) -> List[Dict[str, Any]]:
        """
        Score each candidate against *query* and return top-*k*.

        Each candidate dict must have at least a ``"text"`` key.
        A ``"score"`` key is added to the returned dicts.
        """
        if top_k is None:
            top_k = config.retrieval_top_k

        if not candidates:
            return []

        pairs = [(query, c["text"]) for c in candidates]
        scores = self._model.predict(pairs, show_progress_bar=False)

        # Attach scores and sort
        for c, s in zip(candidates, scores):
            c["score"] = float(s)

        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates[:top_k]
