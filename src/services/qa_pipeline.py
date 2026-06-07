"""
QA pipeline — ties retrieval, reranking, and LangChain LLM together.

Sources (timestamps) are extracted programmatically from the top-ranked
chunks regardless of whether the LLM mentions them in its answer.
The LLM is asked for natural, thorough responses without inline labels.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from src.config import config
from src.services.embedding_service import get_embedding_provider
from src.services.reranker import Reranker
from src.services.vector_store import VectorStore

SYSTEM_PROMPT = """You're discussing a podcast you just listened to with a friend who also heard it.

Rules:
1. Speak naturally, like you're in the conversation. Refer to the speakers' comments directly ("Elon brought up...", "Nikhil asked about...", "they discussed...").
2. Give a thorough, well-explained answer covering the key points. Expand with relevant details from the excerpts. Aim for 4-6 sentences.
3. If the excerpts don't contain the answer, say "I don't recall them discussing that" and don't fabricate.
4. Do NOT cite timestamps or chunk labels in your answer. Just answer naturally."""


def _format_context(chunks: List[Dict[str, Any]]) -> str:
    """Build the context block for the LLM with no labels it could parrot."""
    lines = []
    for c in chunks:
        lines.append(c['text'])
    return "\n\n".join(lines)


class QAPipeline:
    """End-to-end question answering over a podcast transcript."""

    def __init__(self, video_id: str) -> None:
        self._video_id = video_id
        ep = get_embedding_provider()
        self._store = VectorStore(collection_name=f"podcast_{video_id}")
        self._reranker = Reranker()
        self._llm = ChatGroq(
            model=config.llm_model,
            temperature=config.llm_temperature,
            max_tokens=config.llm_max_tokens,
        )

    def ask(
        self,
        question: str,
        history: Optional[List[BaseMessage]] = None,
    ) -> Dict[str, Any]:
        """
        Answer a question about the podcast.

        Parameters
        ----------
        question : str
        history : list[BaseMessage] | None
            Previous conversation messages.

        Returns
        -------
        dict with keys:
          answer   : str
          sources  : list[dict]
        """
        candidates = self._store.search(question, k=config.retrieval_candidates)

        top_chunks = self._reranker.rerank(
            question, candidates, top_k=config.retrieval_top_k
        )

        context = _format_context(top_chunks)

        messages = [SystemMessage(content=SYSTEM_PROMPT)]
        if history:
            messages.extend(history)
        user_content = (
            f"Excerpts from the podcast:\n{context}\n\n"
            f"Question: {question}"
        )
        messages.append(HumanMessage(content=user_content))

        response = self._llm.invoke(messages)
        answer = response.content

        return {"answer": answer, "sources": top_chunks}

    def ask_stream(self, question: str, history: Optional[List[BaseMessage]] = None):
        """Stream answer tokens, yielding them one by one."""
        candidates = self._store.search(question, k=config.retrieval_candidates)
        top_chunks = self._reranker.rerank(
            question, candidates, top_k=config.retrieval_top_k
        )
        context = _format_context(top_chunks)

        messages = [SystemMessage(content=SYSTEM_PROMPT)]
        if history:
            messages.extend(history)
        user_content = (
            f"Excerpts from the podcast:\n{context}\n\n"
            f"Question: {question}"
        )
        messages.append(HumanMessage(content=user_content))

        self._last_sources = top_chunks

        for chunk in self._llm.stream(messages):
            if chunk.content:
                yield chunk.content

    def summarize(self) -> Dict[str, Any]:
        """Generate a comprehensive summary using map-reduce over chunks."""
        all_chunks = self._store.get_all()
        all_chunks.sort(key=lambda c: c['metadata']['start'])

        batch_size = 12
        batches = [all_chunks[i:i + batch_size] for i in range(0, len(all_chunks), batch_size)]

        mini_prompt = """Summarize the following podcast excerpt concisely in 2-3 sentences. Capture the key topic or point discussed."""

        mini_summaries = []
        for batch in batches:
            ctx = _format_context(batch)
            messages = [
                SystemMessage(content=mini_prompt),
                HumanMessage(content=f"Excerpt:\n{ctx}\n\nSummary:"),
            ]
            resp = self._llm.invoke(messages)
            mini_summaries.append(resp.content)

        combined = "\n\n".join(
            f"[Part {i + 1}] {s}" for i, s in enumerate(mini_summaries)
        )

        reduce_prompt = """You are combining summaries of different parts of a podcast into one cohesive overview. Write a comprehensive, well-structured summary covering all the main topics discussed. Write at least 8-12 sentences organized by topic."""

        messages = [
            SystemMessage(content=reduce_prompt),
            HumanMessage(
                content=f"Part summaries:\n{combined}\n\n"
                f"Combine these into one comprehensive summary:"
            ),
        ]
        resp = self._llm.invoke(messages)

        sources = [batch[0] for batch in batches[:5]]
        for s in sources:
            if 'id' not in s:
                s['id'] = s.get('chunk_id', '')

        return {"answer": resp.content, "sources": sources}
