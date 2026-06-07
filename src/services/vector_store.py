"""
Vector store service.

Uses ChromaDB with a persistent backend to store chunk embeddings
and perform similarity search at query time.

Each video gets its own collection to support multi-video queries.
"""

from __future__ import annotations

from typing import Any, Dict, List

import chromadb
from chromadb.utils import embedding_functions

from src.config import config


class VectorStore:
    """
    Persistent ChromaDB wrapper for transcript chunks.

    Parameters
    ----------
    collection_name : str
        ChromaDB collection name (per-video).
    """

    def __init__(self, collection_name: str = "podcast_transcripts") -> None:
        self._ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=config.embedding_model_name,
        )

        self._client = chromadb.PersistentClient(
            path=config.chroma_persist_dir,
        )

        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            embedding_function=self._ef,
        )

    def add_chunks(self, chunks: List[dict]) -> None:
        """Index chunks. Skips IDs that already exist (idempotent)."""
        ids = [c["chunk_id"] for c in chunks]

        existing = set()
        try:
            fetched = self._collection.get(ids=ids)
            if fetched and fetched["ids"]:
                existing = set(fetched["ids"])
        except Exception:
            pass

        to_add = [c for c in chunks if c["chunk_id"] not in existing]
        if not to_add:
            return

        self._collection.add(
            ids=[c["chunk_id"] for c in to_add],
            documents=[c["text"] for c in to_add],
            metadatas=[
                {"start": c["start"], "end": c["end"], "tokens": c["tokens"]}
                for c in to_add
            ],
        )

    def search(
        self,
        query: str,
        k: int = 20,
    ) -> List[Dict[str, Any]]:
        """Return top-*k* chunks similar to *query*."""
        results = self._collection.query(
            query_texts=[query],
            n_results=k,
        )

        output = []
        for i in range(len(results["ids"][0])):
            output.append(
                {
                    "id": results["ids"][0][i],
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i]
                    if results.get("distances")
                    else None,
                }
            )
        return output

    def get_all(self) -> List[Dict[str, Any]]:
        """Return all chunks in the collection."""
        results = self._collection.get()
        output = []
        for i in range(len(results["ids"])):
            output.append({
                "id": results["ids"][i],
                "text": results["documents"][i],
                "metadata": results["metadatas"][i],
            })
        return output

    def count(self) -> int:
        return self._collection.count()

    def delete_all(self) -> None:
        """Delete the current collection."""
        self._collection.delete()
