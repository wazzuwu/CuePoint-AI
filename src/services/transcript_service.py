"""
Transcript service layer.

Provides an abstract base class (``TranscriptProvider``) and concrete
implementations that fetch YouTube subtitles via:

1. Local cache (JSON files in ``data/cache/``)
2. YouTube Data API v3 (OAuth) — if credentials configured
3. youtube-transcript-api — fallback with proxy support

Why abstract?
-------------
- **Dependency Inversion**: callers depend on the interface, not on YouTube.
- **Open/Closed**: add Deepgram, Whisper, or local files by subclassing
  ``TranscriptProvider`` without touching existing code.
"""

from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional

import requests
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import GenericProxyConfig, WebshareProxyConfig

from src.config import config
from src.models.transcript import Transcript, TranscriptInfo, TranscriptSnippet

log = logging.getLogger("transcript_service")

CACHE_DIR = Path("data/cache")


# ── Cache helpers ─────────────────────────────────────────────────────

def _cache_path(video_id: str) -> Path:
    return CACHE_DIR / f"{video_id}.json"


def _load_cached(video_id: str) -> Transcript | None:
    path = _cache_path(video_id)
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        snippets = [
            TranscriptSnippet(text=s["text"], start=s["start"], duration=s["duration"])
            for s in data["snippets"]
        ]
        return Transcript(
            video_id=data["video_id"],
            language=data.get("language", "English"),
            language_code=data.get("language_code", "en"),
            snippets=snippets,
        )
    except Exception as exc:
        log.warning("Failed to load cached transcript for %s: %s", video_id, exc)
        return None


def _save_cache(transcript: Transcript) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_path(transcript.video_id)
    data = {
        "video_id": transcript.video_id,
        "language": transcript.language,
        "language_code": transcript.language_code,
        "snippets": [
            {"text": s.text, "start": s.start, "duration": s.duration}
            for s in transcript.snippets
        ],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ── Abstract interface ────────────────────────────────────────────────

class TranscriptProvider(ABC):
    """Interface that any transcript source must implement."""

    @abstractmethod
    def fetch(
        self,
        video_id: str,
        languages: Optional[List[str]] = None,
    ) -> Transcript:
        ...

    @abstractmethod
    def list_transcripts(self, video_id: str) -> List[TranscriptInfo]:
        ...


# ── SRT parser (for YouTube Data API) ─────────────────────────────────

def _srt_seconds(ts: str) -> float:
    """Convert an SRT timestamp (HH:MM:SS,mmm) to float seconds."""
    m = re.match(r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})", ts)
    if not m:
        return 0.0
    h, mi, s, ms = int(m[1]), int(m[2]), int(m[3]), int(m[4])
    return h * 3600 + mi * 60 + s + ms / 1000


def _parse_srt(text: str) -> list[dict]:
    """Parse SRT caption text into list of {start, end, text} dicts."""
    snippets = []
    blocks = re.split(r"\n\n+", text.strip())

    for block in blocks:
        lines = block.strip().splitlines()
        if len(lines) < 2:
            continue

        ts_line = None
        text_start = 1
        for i in range(min(3, len(lines))):
            if " --> " in lines[i]:
                ts_line = lines[i]
                text_start = i + 1
                break

        if not ts_line:
            continue

        start_str, end_str = ts_line.split(" --> ", 1)
        start = _srt_seconds(start_str)
        end = _srt_seconds(end_str)

        text = " ".join(l.strip() for l in lines[text_start:] if l.strip())
        if text:
            snippets.append({"start": start, "end": end, "text": text})

    return snippets


# ── Fallback: youtube-transcript-api ──────────────────────────────────

class YouTubeTranscriptProvider(TranscriptProvider):
    """
    Fetches transcript data from YouTube using ``youtube-transcript-api``.

    This provider supports proxy configuration (see ``config`` for proxy settings).
    """

    def __init__(self) -> None:
        proxy_config = None
        if config.proxy_url:
            proxy_config = GenericProxyConfig(http_url=config.proxy_url, https_url=config.proxy_url)
        elif config.youtube_proxy_username and config.youtube_proxy_password:
            proxy_config = WebshareProxyConfig(
                proxy_username=config.youtube_proxy_username,
                proxy_password=config.youtube_proxy_password,
            )
        self._client = YouTubeTranscriptApi(proxy_config=proxy_config)

    # ── Public API ────────────────────────────────────────────────────

    def fetch(
        self,
        video_id: str,
        languages: Optional[List[str]] = None,
    ) -> Transcript:
        if languages is None:
            languages = config.transcript_languages

        raw_data = self._client.fetch(video_id, languages=languages)

        snippets = [
            TranscriptSnippet(
                text=snippet.text,
                start=snippet.start,
                duration=snippet.duration,
            )
            for snippet in raw_data
        ]

        return Transcript(
            video_id=raw_data.video_id,
            language=raw_data.language,
            language_code=raw_data.language_code,
            snippets=snippets,
        )

    def list_transcripts(self, video_id: str) -> List[TranscriptInfo]:
        transcript_list = self._client.list(video_id)

        infos: List[TranscriptInfo] = []
        for t in transcript_list:
            infos.append(
                TranscriptInfo(
                    video_id=t.video_id,
                    language=t.language,
                    language_code=t.language_code,
                    is_generated=t.is_generated,
                    is_translatable=t.is_translatable,
                    translation_languages=t.translation_languages,
                )
            )
        return infos


# ── YouTube Data API (OAuth) ──────────────────────────────────────────

class YouTubeDataApiTranscriptProvider(TranscriptProvider):
    """
    Fetches transcripts via the official YouTube Data API v3 using OAuth.

    Requires these env vars on Render:
      YOUTUBE_CLIENT_ID
      YOUTUBE_CLIENT_SECRET
      YOUTUBE_REFRESH_TOKEN

    See ``scripts/get_youtube_refresh_token.py`` for one-time setup.
    """

    _TOKEN_URL = "https://oauth2.googleapis.com/token"
    _API_BASE = "https://youtube.googleapis.com/youtube/v3"
    _SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]

    def __init__(self) -> None:
        self._client_id = config.youtube_client_id or ""
        self._client_secret = config.youtube_client_secret or ""
        self._refresh_token = config.youtube_refresh_token or ""

    def _access_token(self) -> str:
        resp = requests.post(self._TOKEN_URL, data={
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "refresh_token": self._refresh_token,
            "grant_type": "refresh_token",
        })
        resp.raise_for_status()
        return resp.json()["access_token"]

    def fetch(
        self,
        video_id: str,
        languages: Optional[List[str]] = None,
    ) -> Transcript:
        if languages is None:
            languages = config.transcript_languages

        token = self._access_token()
        headers = {"Authorization": f"Bearer {token}"}

        # List available caption tracks
        resp = requests.get(
            f"{self._API_BASE}/captions",
            params={"videoId": video_id, "part": "snippet"},
            headers=headers,
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
        if not items:
            raise RuntimeError(f"No caption tracks found for video {video_id}")

        # Pick best matching language
        caption_id = None
        chosen_lang = languages[0]
        for lang in languages:
            for item in items:
                cl = item["snippet"]["language"]
                if cl == lang:
                    caption_id = item["id"]
                    chosen_lang = lang
                    break
            if caption_id:
                break
        if not caption_id:
            caption_id = items[0]["id"]
            chosen_lang = items[0]["snippet"]["language"]

        # Download caption content (SRT format)
        resp = requests.get(
            f"{self._API_BASE}/captions/{caption_id}",
            params={"tfmt": "srt", "alt": "media"},
            headers=headers,
        )
        if not resp.ok:
            log.error(
                "captions.download failed: %s %s — body: %s",
                resp.status_code, resp.reason, resp.text[:500],
            )
        resp.raise_for_status()

        snippets_raw = _parse_srt(resp.text)

        snippets = [
            TranscriptSnippet(
                text=s["text"],
                start=s["start"],
                duration=s["end"] - s["start"],
            )
            for s in snippets_raw
        ]

        return Transcript(
            video_id=video_id,
            language=chosen_lang,
            language_code=chosen_lang,
            snippets=snippets,
        )

    def list_transcripts(self, video_id: str) -> List[TranscriptInfo]:
        token = self._access_token()
        resp = requests.get(
            f"{self._API_BASE}/captions",
            params={"videoId": video_id, "part": "snippet"},
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()

        infos: List[TranscriptInfo] = []
        for item in resp.json().get("items", []):
            s = item["snippet"]
            infos.append(
                TranscriptInfo(
                    video_id=video_id,
                    language=s["language"],
                    language_code=s["language"],
                    is_generated=s.get("trackKind", "") == "ASR",
                    is_translatable=False,
                )
            )
        return infos


# ── Composite: cache + primary + fallbacks ─────────────────────────────

class FailoverTranscriptProvider(TranscriptProvider):
    """
    Tries cache first, then YouTube Data API, then youtube-transcript-api.

    Successful fetches from live providers are written to cache so
    subsequent calls are instant and resilient to network issues.
    """

    def __init__(self) -> None:
        self._providers: list[TranscriptProvider] = []
        has_api_creds = all([
            config.youtube_client_id,
            config.youtube_client_secret,
            config.youtube_refresh_token,
        ])
        if has_api_creds:
            self._providers.append(YouTubeDataApiTranscriptProvider())
        self._providers.append(YouTubeTranscriptProvider())

    def fetch(
        self,
        video_id: str,
        languages: Optional[List[str]] = None,
    ) -> Transcript:
        # 1. Try cache first
        cached = _load_cached(video_id)
        if cached is not None:
            log.info("Loaded cached transcript for %s", video_id)
            return cached

        # 2. Try live providers
        last_exc = None
        for i, provider in enumerate(self._providers):
            try:
                transcript = provider.fetch(video_id, languages=languages)
                _save_cache(transcript)
                log.info("Cached transcript for %s", video_id)
                return transcript
            except Exception as exc:
                last_exc = exc
                if i < len(self._providers) - 1:
                    log.warning(
                        "%s failed for %s: %s — trying next provider",
                        type(provider).__name__, video_id, exc,
                    )
        raise RuntimeError(
            f"All transcript providers failed for {video_id}: {last_exc}"
        )

    def list_transcripts(self, video_id: str) -> List[TranscriptInfo]:
        for provider in self._providers:
            try:
                return provider.list_transcripts(video_id)
            except Exception:
                continue
        return []


# ── Convenience factory ───────────────────────────────────────────────

def create_transcript_provider() -> TranscriptProvider:
    """
    Return a ``FailoverTranscriptProvider`` that tries:
    - Local cache (``data/cache/<video_id>.json``)
    - YouTube Data API v3 (if OAuth credentials configured)
    - youtube-transcript-api (with proxy support)
    """
    return FailoverTranscriptProvider()
