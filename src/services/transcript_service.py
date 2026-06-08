"""
Transcript service layer.

Provides an abstract base class (``TranscriptProvider``) and concrete
implementations that fetch YouTube subtitles via yt-dlp (primary) or
``youtube-transcript-api`` (fallback).

Why abstract?
-------------
- **Dependency Inversion**: callers depend on the interface, not on YouTube.
- **Open/Closed**: add Deepgram, Whisper, or local files by subclassing
  ``TranscriptProvider`` without touching existing code.
"""

from __future__ import annotations

import logging
import os
import re
import tempfile
from abc import ABC, abstractmethod
from typing import List, Optional

# Third-party
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import GenericProxyConfig, WebshareProxyConfig

# Local
from src.config import config
from src.models.transcript import Transcript, TranscriptInfo, TranscriptSnippet

log = logging.getLogger("transcript_service")


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


# ── yt-dlp implementation (primary) ──────────────────────────────────

VTT_TIME_RE = re.compile(r"(\d{2}):(\d{2}):(\d{2})\.(\d{3})")


def _vtt_seconds(ts: str) -> float:
    """Convert a VTT timestamp (HH:MM:SS.mmm) to float seconds."""
    m = VTT_TIME_RE.match(ts)
    if not m:
        return 0.0
    h, mi, s, ms = int(m[1]), int(m[2]), int(m[3]), int(m[4])
    return h * 3600 + mi * 60 + s + ms / 1000


def _parse_vtt(text: str) -> list[dict]:
    """Parse VTT caption text into list of {start, end, text} dicts."""
    snippets = []
    lines = text.strip().splitlines()

    i = 0
    while i < len(lines):
        # Skip header lines and blank lines
        if " --> " not in lines[i]:
            i += 1
            continue

        # Parse timestamp line: 00:00:00.000 --> 00:00:04.000
        ts_part = lines[i]
        i += 1
        start_str, end_str = ts_part.split(" --> ", 1)
        start = _vtt_seconds(start_str)
        end = _vtt_seconds(end_str)

        # Collect text lines until blank line or next cue
        text_parts = []
        while i < len(lines) and lines[i].strip() and " --> " not in lines[i]:
            text_parts.append(lines[i].strip())
            i += 1

        text = " ".join(text_parts)
        if text:
            snippets.append({
                "start": start,
                "end": end,
                "text": text,
            })

    return snippets


class YtDlpTranscriptProvider(TranscriptProvider):
    """
    Fetches transcripts by extracting YouTube subtitles via yt-dlp.

    yt-dlp is more resilient to IP blocks (better headers, retries,
    workarounds) than ``youtube-transcript-api``.
    """

    def __init__(self) -> None:
        proxy_url = config.proxy_url or ""
        self._ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitlesformat": "vtt",
            "extractor_retries": 3,
        }
        if proxy_url:
            self._ydl_opts["proxy"] = proxy_url

    def fetch(
        self,
        video_id: str,
        languages: Optional[List[str]] = None,
    ) -> Transcript:
        if languages is None:
            languages = config.transcript_languages

        url = f"https://www.youtube.com/watch?v={video_id}"
        opts = dict(self._ydl_opts)
        opts["subtitleslangs"] = languages

        with tempfile.TemporaryDirectory() as tmpdir:
            opts["outtmpl"] = os.path.join(tmpdir, "%(id)s.%(ext)s")

            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)

                # Try downloading subtitles
                ydl.download([url])

            # Find the downloaded VTT file
            vtt_path = None
            for f in os.listdir(tmpdir):
                if f.endswith(".vtt"):
                    vtt_path = os.path.join(tmpdir, f)
                    break

            if not vtt_path:
                raise RuntimeError(
                    f"No subtitle file downloaded for {video_id} "
                    f"(yt-dlp could not extract captions)"
                )

            with open(vtt_path, encoding="utf-8") as f:
                raw = f.read()

        snippets_raw = _parse_vtt(raw)

        # Determine language from info dict
        lang_name = info.get("language", "English")
        lang_code = info.get("language_code", languages[0] if languages else "en")

        # Build transcript model (convert start/end to start/duration)
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
            language=lang_name,
            language_code=lang_code,
            snippets=snippets,
        )

    def list_transcripts(self, video_id: str) -> List[TranscriptInfo]:
        url = f"https://www.youtube.com/watch?v={video_id}"
        with yt_dlp.YoutubeDL(dict(self._ydl_opts)) as ydl:
            info = ydl.extract_info(url, download=False)

        infos: List[TranscriptInfo] = []
        subs = info.get("subtitles") or info.get("automatic_captions") or {}
        for lang_code, lang_data in subs.items():
            infos.append(
                TranscriptInfo(
                    video_id=video_id,
                    language=lang_code,
                    language_code=lang_code,
                    is_generated=lang_code in (info.get("automatic_captions") or {}),
                    is_translatable=False,
                )
            )
        return infos


# ── Fallback: youtube-transcript-api ──────────────────────────────────

class YouTubeTranscriptProvider(TranscriptProvider):
    """
    Fetches transcript data from YouTube using ``youtube-transcript-api``.

    This is the fallback provider used when yt-dlp fails. It supports
    proxy configuration (see ``config`` for proxy settings).
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


# ── Composite: primary + fallback ──────────────────────────────────────

class FailoverTranscriptProvider(TranscriptProvider):
    """Tries yt-dlp first; falls back to youtube-transcript-api on failure."""

    def __init__(self) -> None:
        self._primary = YtDlpTranscriptProvider()
        self._fallback = YouTubeTranscriptProvider()

    def fetch(
        self,
        video_id: str,
        languages: Optional[List[str]] = None,
    ) -> Transcript:
        try:
            return self._primary.fetch(video_id, languages=languages)
        except Exception as exc:
            log.warning(
                "yt-dlp failed for %s: %s — falling back to youtube-transcript-api",
                video_id, exc,
            )
            return self._fallback.fetch(video_id, languages=languages)

    def list_transcripts(self, video_id: str) -> List[TranscriptInfo]:
        try:
            return self._primary.list_transcripts(video_id)
        except Exception:
            return self._fallback.list_transcripts(video_id)


# ── Convenience factory ───────────────────────────────────────────────

def create_transcript_provider() -> TranscriptProvider:
    """
    Return a ``FailoverTranscriptProvider`` that tries yt-dlp first,
    then falls back to ``youtube-transcript-api``.
    """
    return FailoverTranscriptProvider()
