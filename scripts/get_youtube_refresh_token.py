"""
One-time OAuth 2.0 setup script for YouTube Data API v3.

This script opens a browser for you to sign in to your Google account
and grants access to read YouTube captions. At the end it prints a
refresh token that never expires (unless revoked).

Usage
-----
1. Go to https://console.cloud.google.com/apis/credentials
2. Create an OAuth client ID (Desktop application type)
3. Download the JSON and place it as ``client_secret.json`` in this
   directory, or pass the path with ``--secrets``
4. Run::

       pip install google-auth-oauthlib
       python scripts/get_youtube_refresh_token.py

5. Copy the printed refresh token into your Render env vars as
   ``YOUTUBE_REFRESH_TOKEN`` (and also set ``YOUTUBE_CLIENT_ID``
   and ``YOUTUBE_CLIENT_SECRET`` from the downloaded JSON).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]


def main(secrets_path: str) -> None:
    # Load client credentials
    with open(secrets_path) as f:
        secrets = json.load(f)

    client_id = secrets.get("installed", secrets.get("web", {})).get("client_id")
    client_secret = secrets.get("installed", secrets.get("web", {})).get("client_secret")

    if not client_id or not client_secret:
        print("ERROR: Could not find client_id/client_secret in the JSON file.")
        print("Make sure you downloaded the OAuth client ID (Desktop app) JSON.")
        sys.exit(1)

    print(f"Using client_id:     {client_id[:15]}...")
    print(f"Using client_secret: {client_secret[:5]}...")
    print()

    from google_auth_oauthlib.flow import InstalledAppFlow

    flow = InstalledAppFlow.from_client_config(
        {"installed": {"client_id": client_id, "client_secret": client_secret,
                       "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                       "token_uri": "https://oauth2.googleapis.com/token",
                       "redirect_uris": ["http://localhost"]}},
        scopes=SCOPES,
    )

    creds = flow.run_local_server(port=0, open_browser=True)

    print("\n" + "=" * 60)
    print("SUCCESS! Add these to your Render env vars:\n")
    print(f"  YOUTUBE_CLIENT_ID={client_id}")
    print(f"  YOUTUBE_CLIENT_SECRET={client_secret}")
    print(f"  YOUTUBE_REFRESH_TOKEN={creds.refresh_token}")
    print()
    print("This refresh token does not expire unless you revoke it.")
    print("=" * 60)


if __name__ == "__main__":
    secrets_path = "client_secret.json"
    if len(sys.argv) > 2 and sys.argv[1] == "--secrets":
        secrets_path = sys.argv[2]
    elif Path("client_secret.json").exists():
        pass  # use default
    elif Path("scripts/client_secret.json").exists():
        secrets_path = "scripts/client_secret.json"

    if not os.path.exists(secrets_path):
        print(f"ERROR: {secrets_path} not found.")
        print("Download your OAuth client ID JSON from Google Cloud Console")
        print("and save it as 'client_secret.json' in this directory.")
        print("Or pass: python get_youtube_refresh_token.py --secrets /path/to/file.json")
        sys.exit(1)

    main(secrets_path)
