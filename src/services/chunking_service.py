"""
Chunking service — token-aware snippet grouping with overlap.

Groups transcript snippets into ~``target_tokens``-sized chunks while
never splitting a snippet.  Overlap between consecutive chunks ensures
answers that span chunk boundaries are still captured.

Key design decision:
  Each chunk stores its exact ``start_time`` and ``end_time`` so we
  can always return a real, verified timestamp rather than asking the
  LLM to hallucinate one.
"""

from __future__ import annotations

from typing import List

from src.config import config
from src.models.transcript import Transcript


def chunk_transcript(
    transcript: Transcript,
    target_tokens: int | None = None,
    overlap_tokens: int | None = None,
) -> list[dict]:
    """
    Group transcript snippets into chunks.

    Each returned dict has:
      chunk_id  : str   — unique identifier
      text      : str   — joined snippet text
      start     : float — start time in seconds
      end       : float — end time in seconds
      tokens    : int   — approximate token count

    Returns
    -------
    list[dict]
    """
    if target_tokens is None:
        target_tokens = config.chunk_target_tokens
    if overlap_tokens is None:
        overlap_tokens = config.chunk_overlap_tokens

    chunks: list[dict] = []
    current: list = []
    current_tokens = 0
    chunk_idx = 0

    for snippet in transcript.snippets:
        tok = len(snippet.text.split())

        if current_tokens + tok > target_tokens and current:
            _flush(chunks, current, current_tokens, transcript, chunk_idx)
            chunk_idx += 1

            # Build overlap from the tail of the flushed group
            overlap: list = []
            overlap_tok = 0
            for x in reversed(current):
                xt = len(x.text.split())
                if overlap_tok + xt > overlap_tokens and overlap:
                    break
                overlap.insert(0, x)
                overlap_tok += xt

            current = overlap
            current_tokens = overlap_tok

        current.append(snippet)
        current_tokens += tok

    if current:
        _flush(chunks, current, current_tokens, transcript, chunk_idx)

    return chunks


def _flush(
    chunks: list,
    snippets: list,
    token_count: int,
    transcript: Transcript,
    idx: int,
) -> None:
    """Convert snippet list into a chunk dict."""
    text = " ".join(s.text.strip() for s in snippets)
    first = snippets[0]
    last = snippets[-1]
    chunks.append(
        {
            "chunk_id": f"{transcript.video_id}_{idx:04d}",
            "text": text,
            "start": first.start,
            "end": last.end,
            "tokens": token_count,
        }
    )
