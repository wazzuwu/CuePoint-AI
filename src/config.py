"""
Configuration management for the Podcast Q&A Bot.

Centralises all configurable settings (API keys, model names, file paths, etc.)
so the rest of the code never hard-codes environment-specific values.

Follows the Principle of Single Responsibility by owning all configuration
in one place.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# ── Load .env file if present (optional) ──────────────────────────────
load_dotenv()


@dataclass(frozen=True)
class Config:
    """
    Immutable configuration container.

    All values are read from environment variables at import time so that
    they can be overridden without touching code.
    """

    # ── Paths ──────────────────────────────────────────────────────────
    data_dir: Path = field(
        default_factory=lambda: Path(
            os.getenv("DATA_DIR", str(Path.cwd() / "data"))
        )
    )

    # ── YouTube Transcript API ─────────────────────────────────────────
    youtube_proxy_username: str | None = os.getenv("YT_PROXY_USERNAME")
    youtube_proxy_password: str | None = os.getenv("YT_PROXY_PASSWORD")
    proxy_url: str | None = os.getenv("PROXY_URL")
    transcript_languages: list[str] = field(
        default_factory=lambda: [
            x.strip()
            for x in os.getenv("TRANSCRIPT_LANGUAGES", "en-IN,en").split(",")
        ]
    )

    # ── Embedding model ─────────────────────────────────────────────────
    embedding_model_name: str = os.getenv(
        "EMBEDDING_MODEL", "all-MiniLM-L6-v2"
    )

    # ── Chunking ──────────────────────────────────────────────────────
    chunk_target_tokens: int = int(os.getenv("CHUNK_TARGET_TOKENS", "200"))
    chunk_overlap_tokens: int = int(os.getenv("CHUNK_OVERLAP_TOKENS", "40"))

    # ── Vector store (ChromaDB) ───────────────────────────────────────
    chroma_persist_dir: str = os.getenv(
        "CHROMA_PERSIST_DIR", str(Path.cwd() / "data" / "chroma")
    )

    # ── Retrieval ─────────────────────────────────────────────────────
    retrieval_top_k: int = int(os.getenv("RETRIEVAL_TOP_K", "7"))

    # ── YouTube Data API (OAuth) ──────────────────────────────────────
    youtube_client_id: str | None = os.getenv("YOUTUBE_CLIENT_ID")
    youtube_client_secret: str | None = os.getenv("YOUTUBE_CLIENT_SECRET")
    youtube_refresh_token: str | None = os.getenv("YOUTUBE_REFRESH_TOKEN")

    # ── Groq ───────────────────────────────────────────────────────────
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_base_url: str = os.getenv(
        "GROQ_BASE_URL", "https://api.groq.com/openai/v1"
    )
    llm_model: str = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.3"))
    llm_max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "1024"))

    # ── Video ID to process ───────────────────────────────────────────
    target_video_id: str = os.getenv("VIDEO_ID", "Rni7Fz7208c")


# ── Singleton instance ────────────────────────────────────────────────
config = Config()
