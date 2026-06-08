"""
Pre-populate the local transcript cache for offline/resilient deploys.

Run this on your local machine (where YouTube API calls work without IP
blocks) to cache transcripts into ``data/cache/<video_id>.json``.

Usage
-----
::

    cd CuePointAI
    python scripts/cache_transcript.py Rni7Fz7208c
    python scripts/cache_transcript.py          # defaults to Rni7Fz7208c
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the repo root is on sys.path so we can import src.*
SRC_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SRC_ROOT))

from src.config import config as _
from src.services.transcript_service import YouTubeTranscriptProvider, _save_cache


def main(video_id: str) -> None:
    print(f"Fetching transcript for {video_id} ...")
    provider = YouTubeTranscriptProvider()
    transcript = provider.fetch(video_id)
    print(f"  Language: {transcript.language} ({transcript.language_code})")
    print(f"  Snippets: {len(transcript.snippets)}")
    _save_cache(transcript)
    print(f"  Cached to data/cache/{video_id}.json")
    print("Done.")


if __name__ == "__main__":
    video_id = sys.argv[1] if len(sys.argv) > 1 else "Rni7Fz7208c"
    main(video_id)
