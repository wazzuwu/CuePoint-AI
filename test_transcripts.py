"""
Tests and inspection script for the transcript service.

Prints the transcript in a readable format so you can judge the quality
of the data we're working with, and validates the domain models.

Usage:
    python test_transcripts.py
"""

from src.models.transcript import Transcript, TranscriptInfo, TranscriptSnippet
from src.services.transcript_service import create_transcript_provider


def inspect_transcript():
    """Fetch the transcript and print it in full for quality inspection."""
    provider = create_transcript_provider()
    transcript: Transcript = provider.fetch("Rni7Fz7208c")

    # ── Summary ───────────────────────────────────────────────────────
    print("=" * 60)
    print("TRANSCRIPT SUMMARY")
    print("=" * 60)
    print(f"  Video ID:       {transcript.video_id}")
    print(f"  Language:       {transcript.language} ({transcript.language_code})")
    print(f"  Total snippets: {len(transcript)}")
    print(f"  Duration:       {transcript.duration_seconds / 60:.1f} min")
    print(f"  Total chars:    {len(transcript.full_text)}")
    print()

    # ── Full transcript content ──────────────────────────────────────
    print("=" * 60)
    print("FULL TRANSCRIPT")
    print("=" * 60)
    for i, snippet in enumerate(transcript.snippets):
        print(f"  [{snippet.start:7.2f}s - {snippet.end:7.2f}s]  {snippet.text.strip()}")

    # ── Model validation ─────────────────────────────────────────────
    print()
    print("=" * 60)
    print("MODEL VALIDATION")
    print("=" * 60)

    # TranscriptSnippet: verify all fields are populated
    sample: TranscriptSnippet = transcript.snippets[0]
    print(f"  TranscriptSnippet fields: text={sample.text!r}, "
          f"start={sample.start}, duration={sample.duration}, end={sample.end}")

    # Transcript: verify helper properties
    print(f"  Transcript.full_text length:        {len(transcript.full_text)} chars")
    print(f"  Transcript.duration_seconds:         {transcript.duration_seconds:.1f}s")
    print(f"  Transcript.len (snippets):           {len(transcript)}")
    print(f"  Transcript.to_raw_list() length:     {len(transcript.to_raw_list())}")

    # TranscriptInfo: verify list_transcripts returns proper metadata
    provider = create_transcript_provider()
    infos = provider.list_transcripts("Rni7Fz7208c")
    info: TranscriptInfo = infos[0]
    print(f"  TranscriptInfo fields: video_id={info.video_id}, "
          f"language={info.language}, lang_code={info.language_code}, "
          f"is_generated={info.is_generated}, is_translatable={info.is_translatable}")


def test_snippet_end_property():
    """end should always equal start + duration."""
    provider = create_transcript_provider()
    transcript = provider.fetch("Rni7Fz7208c")
    for snippet in transcript.snippets:
        assert snippet.end == snippet.start + snippet.duration, (
            f"end mismatch at {snippet.start}"
        )
    print("[PASS] snippet.end == snippet.start + snippet.duration")


def test_transcript_full_text():
    """full_text should concatenate all snippet texts."""
    provider = create_transcript_provider()
    transcript = provider.fetch("Rni7Fz7208c")
    expected = " ".join(s.text.strip() for s in transcript.snippets)
    assert transcript.full_text == expected
    print("[PASS] transcript.full_text matches concatenation")


def test_to_raw_list_structure():
    """to_raw_list should return serialisable dicts."""
    provider = create_transcript_provider()
    transcript = provider.fetch("Rni7Fz7208c")
    raw = transcript.to_raw_list()
    assert len(raw) == len(transcript)
    for entry in raw:
        assert set(entry.keys()) == {"text", "start", "duration"}
        assert isinstance(entry["start"], float)
        assert isinstance(entry["duration"], float)
    print(f"[PASS] to_raw_list: {len(raw)} dicts, all keys correct")


def test_list_transcripts_model():
    """list_transcripts should return TranscriptInfo instances."""
    provider = create_transcript_provider()
    infos = provider.list_transcripts("Rni7Fz7208c")
    assert len(infos) > 0
    for info in infos:
        assert isinstance(info, TranscriptInfo)
        assert isinstance(info.is_generated, bool)
        assert isinstance(info.is_translatable, bool)
        assert info.language_code
    print(f"[PASS] list_transcripts: {len(infos)} TranscriptInfo objects")


if __name__ == "__main__":
    inspect_transcript()
    print()
    test_snippet_end_property()
    test_transcript_full_text()
    test_to_raw_list_structure()
    test_list_transcripts_model()
    print("\nAll checks passed.")
