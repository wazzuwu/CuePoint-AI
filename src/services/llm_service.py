"""
LLM answering service — Groq (Llama 3.1 8B) via the OpenAI SDK.

The OpenAI SDK provides a unified interface; we just point the base_url
at Groq's endpoint and pass the Groq API key.
"""

from __future__ import annotations

from typing import List, Optional

from openai import OpenAI

from src.config import config


class GroqProvider:
    """Thin wrapper around Groq's OpenAI-compatible API."""

    def __init__(self) -> None:
        self._client = OpenAI(
            base_url=config.groq_base_url,
            api_key=config.groq_api_key,
        )
        self._model = config.llm_model

    def answer(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 512,
    ) -> str:
        """Return the model's text response."""
        resp = self._client.chat.completions.create(
            model=self._model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return resp.choices[0].message.content or ""
