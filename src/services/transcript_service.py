"""
Transcript service layer.

Provides an abstract base class (``TranscriptProvider``) and one concrete
implementation (``YouTubeTranscriptProvider``) that fetches subtitles via
the ``youtube-transcript-api`` library.

Why abstract?
-------------
- **Dependency Inversion**: callers depend on the interface, not on YouTube.
- **Open/Closed**: add Deepgram, Whisper, or local files by subclassing
  ``TranscriptProvider`` without touching existing code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

# Third-party
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import GenericProxyConfig, WebshareProxyConfig

# Local
from src.config import config
from src.models.transcript import Transcript, TranscriptInfo, TranscriptSnippet


# ── Abstract interface ────────────────────────────────────────────────

class TranscriptProvider(ABC):
    """
    Interface that any transcript source must implement.

    Methods
    -------
    fetch(video_id, languages)
        Retrieve the full transcript for a video.
    list_transcripts(video_id)
        List all available transcripts (metadata only) for a video.
    """

    @abstractmethod
    def fetch(
        self,
        video_id: str,
        languages: Optional[List[str]] = None,
    ) -> Transcript:
        """
        Fetch a transcript for *video_id*.

        Parameters
        ----------
        video_id : str
            YouTube video ID (not the full URL).
        languages : list[str] or None
            Language codes in priority order.  Defaults to ``["en"]``.

        Returns
        -------
        Transcript
        """
        ...

    @abstractmethod
    def list_transcripts(self, video_id: str) -> List[TranscriptInfo]:
        """
        List available transcripts for *video_id*.

        Returns
        -------
        list[TranscriptInfo]
        """
        ...


# ── Concrete implementation: YouTube ─────────────────────────────────

class YouTubeTranscriptProvider(TranscriptProvider):
    """
    Fetches transcript data from YouTube using ``youtube-transcript-api``.

    Usage::

        provider = YouTubeTranscriptProvider()
        transcript = provider.fetch("Rni7Fz7208c")

    The provider can optionally route traffic through proxies
    to avoid IP bans (see ``config`` for proxy settings).
    """

    def __init__(self) -> None:
        """Initialise the underlying YouTube API client."""

        # Build proxy configuration if credentials are provided in env
        proxy_config = None
        if config.proxy_url:
            proxy_config = GenericProxyConfig(http_url=config.proxy_url, https_url=config.proxy_url)
        elif config.youtube_proxy_username and config.youtube_proxy_password:
            proxy_config = WebshareProxyConfig(
                proxy_username=config.youtube_proxy_username,
                proxy_password=config.youtube_proxy_password,
            )

        # Instantiate the library's client
        self._client = YouTubeTranscriptApi(proxy_config=proxy_config)

    # ── Public API ────────────────────────────────────────────────────

    def fetch(
        self,
        video_id: str,
        languages: Optional[List[str]] = None,
    ) -> Transcript:
        """
        Fetch and return a ``Transcript`` domain model.

        Steps
        -----
        1. Call the underlying library to get raw snippet data.
        2. Map each raw snippet to our ``TranscriptSnippet`` model.
        3. Wrap in a ``Transcript`` with metadata.

        Raises
        ------
        youtube_transcript_api._errors.TranscriptsDisabled
            If the video has no captions available.
        youtube_transcript_api._errors.NoTranscriptFound
            If none of the requested languages are available.
        """
        if languages is None:
            languages = config.transcript_languages

        # Step 1: fetch raw data from the YouTube API
        raw_data = self._client.fetch(video_id, languages=languages)

        # Step 2: normalise into domain models
        snippets = [
            TranscriptSnippet(
                text=snippet.text,
                start=snippet.start,
                duration=snippet.duration,
            )
            for snippet in raw_data
        ]

        # Step 3: build and return the domain Transcript
        return Transcript(
            video_id=raw_data.video_id,
            language=raw_data.language,
            language_code=raw_data.language_code,
            snippets=snippets,
        )

    def list_transcripts(self, video_id: str) -> List[TranscriptInfo]:
        """
        Return metadata about every available transcript for *video_id*.

        This is useful for debugging or for letting users pick a language.
        """
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


# ── Convenience factory ───────────────────────────────────────────────

def create_transcript_provider() -> TranscriptProvider:
    """
    Factory that returns a configured ``TranscriptProvider``.

    In future, this could inspect a setting and return a different
    implementation (e.g. LocalFileProvider) without callers changing.
    """
    return YouTubeTranscriptProvider()
