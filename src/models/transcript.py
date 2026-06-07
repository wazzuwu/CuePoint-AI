"""
Data models for transcript representation.

These plain dataclasses ensure a consistent shape for transcript data
as it flows through the pipeline.  They are intentionally decoupled from
any external library so that swapping providers (e.g. Deepgram, Whisper)
requires no changes downstream.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class TranscriptSnippet:
    """
    A single piece of transcribed text with temporal metadata.

    Attributes
    ----------
    text : str
        The transcribed words.
    start : float
        Start time in seconds from the beginning of the video.
    duration : float
        Duration of this snippet in seconds.
    """

    text: str
    start: float
    duration: float

    @property
    def end(self) -> float:
        """End time in seconds (convenience property)."""
        return self.start + self.duration


@dataclass(frozen=True)
class TranscriptInfo:
    """
    Lightweight metadata about an *available* transcript before fetching it.

    Attributes
    ----------
    video_id : str
    language : str
        Human-readable language name, e.g. "English".
    language_code : str
        BCP-47 language code, e.g. "en".
    is_generated : bool
        ``True`` if YouTube auto-generated the captions.
    is_translatable : bool
        Whether this transcript can be machine-translated.
    translation_languages : list[str]
        Language codes this transcript can be translated into.
    """

    video_id: str
    language: str
    language_code: str
    is_generated: bool
    is_translatable: bool
    translation_languages: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Transcript:
    """
    A fully fetched transcript for a single video.

    Attributes
    ----------
    video_id : str
    language : str
    language_code : str
    snippets : list[TranscriptSnippet]
        Ordered list of text snippets with timing info.
    """

    video_id: str
    language: str
    language_code: str
    snippets: List[TranscriptSnippet] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        """Concatenated plain text of all snippets, space-separated."""
        return " ".join(s.text.strip() for s in self.snippets)

    @property
    def duration_seconds(self) -> float:
        """Total duration covered by the transcript."""
        if not self.snippets:
            return 0.0
        return self.snippets[-1].end

    def __len__(self) -> int:
        return len(self.snippets)

    def to_raw_list(self) -> list[dict]:
        """
        Serialise to the plain-dict format consumed by serialisers.

        This is useful when you need JSON, CSV, etc. output.
        """
        return [
            {"text": s.text, "start": s.start, "duration": s.duration}
            for s in self.snippets
        ]
