#!/usr/bin/env python3
"""Upload a reference voice to the local Fish Speech server.

Usage:
    python scripts/upload_reference_voice.py

Waits for the server to be ready, then registers the reference audio
so Fish Speech uses a consistent voice across all scenes.
"""

import os
import sys
import time

import requests

FISH_SPEECH_URL = os.getenv("FISH_SPEECH_URL", "http://localhost:8080")
REFERENCE_ID = "narrator"
AUDIO_PATH = "output/ref_voice.wav"
REFERENCE_TEXT = "So here's the thing about modern software architecture."
MAX_WAIT = 60  # seconds to wait for server


def wait_for_server():
    """Poll the health endpoint until the server is ready."""
    print(f"Waiting for Fish Speech server at {FISH_SPEECH_URL}...")
    start = time.time()
    while time.time() - start < MAX_WAIT:
        try:
            resp = requests.get(f"{FISH_SPEECH_URL}/v1/health", timeout=3)
            if resp.status_code == 200:
                print("Server is ready.")
                return True
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(2)
    print(f"Server not ready after {MAX_WAIT}s.")
    return False


def main():
    if not os.path.exists(AUDIO_PATH):
        print(f"Reference audio not found: {AUDIO_PATH}")
        sys.exit(1)

    if not wait_for_server():
        sys.exit(1)

    print(f"Uploading reference voice '{REFERENCE_ID}'...")

    with open(AUDIO_PATH, "rb") as f:
        resp = requests.post(
            f"{FISH_SPEECH_URL}/v1/references/add",
            data={"id": REFERENCE_ID, "text": REFERENCE_TEXT},
            files={"audio": (os.path.basename(AUDIO_PATH), f, "audio/wav")},
            timeout=30,
        )

    if resp.status_code == 200:
        print(f"Reference '{REFERENCE_ID}' uploaded successfully.")
    elif resp.status_code == 409:
        print(f"Reference '{REFERENCE_ID}' already exists (OK).")
    else:
        print(f"Upload failed: HTTP {resp.status_code}")
        print(resp.text)
        sys.exit(1)


if __name__ == "__main__":
    main()
