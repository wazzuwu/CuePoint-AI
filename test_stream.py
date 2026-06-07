"""
Test script to verify backend SSE streaming works.

Usage:
  1. Start the backend: python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
  2. First, load a video and create a session:
     python test_stream.py --load Rni7Fz7208c
  3. Then test streaming:
     python test_stream.py --ask "what is first principles thinking?"
"""

import argparse
import json
import sys
import time
import urllib.request

API = "http://localhost:8000"


def _load(session_id: str | None, video_id: str) -> str:
    """Load a video and create a session. Returns session_id."""
    if session_id:
        # Check session still exists
        return session_id

    print(f"\n=== Loading video: {video_id} ===")
    req = urllib.request.Request(
        f"{API}/api/load",
        data=json.dumps({"video_id": video_id}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read())
        print(f"  Status: {data.get('status')}")

    print(f"\n=== Creating session ===")
    req = urllib.request.Request(
        f"{API}/api/session",
        data=json.dumps({"video_id": video_id}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read())
        sid = data["session_id"]
        print(f"  Session ID: {sid}")
    return sid


def test_stream(session_id: str, question: str):
    """Hit the streaming endpoint and print token arrivals."""
    print(f"\n=== Asking: {question} ===")
    print(f"  Session: {session_id}")
    print()

    body = json.dumps({"session_id": session_id, "question": question}).encode()
    req = urllib.request.Request(
        f"{API}/api/ask/stream",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    t0 = time.time()
    token_count = 0
    full_text = ""
    last_log = t0

    with urllib.request.urlopen(req) as r:
        buffer = b""
        while True:
            chunk = r.read(1)  # Read ONE BYTE at a time
            if not chunk:
                break
            buffer += chunk

            # Check if we have a complete SSE message
            text = buffer.decode()
            if not text.endswith("\n"):
                continue

            for line in text.strip().split("\n"):
                if not line.startswith("data: "):
                    continue

                payload = line[6:]
                if payload == "[DONE]":
                    print(f"\n[DONE] — total tokens: {token_count}, time: {time.time() - t0:.2f}s")
                    return

                try:
                    parsed = json.loads(payload)
                except json.JSONDecodeError:
                    continue

                if parsed.get("type") == "sources":
                    src_count = len(parsed.get("sources", []))
                    print(f"\n[SOURCES] {src_count} timestamps received")
                    continue

                token = parsed.get("token", "")
                if not token:
                    continue

                token_count += 1
                full_text += token
                now = time.time()

                # Log every token with timing
                elapsed = now - t0
                gap = now - last_log
                last_log = now
                print(f"  +{gap:.3f}s @ {elapsed:.2f}s | token #{token_count}: {repr(token)}")

            buffer = b""

    print(f"\n=== Full answer ({len(full_text)} chars) ===")
    print(full_text)
    print()


def main():
    parser = argparse.ArgumentParser(description="Test backend SSE streaming")
    parser.add_argument("--load", help="Video ID to load first", default="Rni7Fz7208c")
    parser.add_argument("--ask", help="Question to ask", default="what is first principles thinking?")
    parser.add_argument("--session", help="Existing session ID (skip load)", default=None)
    args = parser.parse_args()

    session_id = _load(args.session, args.load) if args.load else args.session
    if not session_id:
        print("ERROR: No session available. Use --load or --session")
        sys.exit(1)

    test_stream(session_id, args.ask)


if __name__ == "__main__":
    main()
