#!/usr/bin/env python3
"""Generate reference audio from ElevenLabs, then extract the best segment for voice cloning.

Usage:
    python scripts/generate_ref_from_elevenlabs.py

This will:
1. Generate the full reference script via ElevenLabs
2. Save the full recording to output/ref_voice_full.mp3
3. Extract multiple 8-second candidate segments
4. Convert the best segment to 24kHz mono WAV for Fish Audio voice cloning

After running, listen to the candidates in output/ref_candidates/ and pick
the one that sounds most natural. Then set in .env:
    FISH_REF_AUDIO_PATH=output/ref_voice.wav
    FISH_REF_AUDIO_TEXT=<exact transcript of the chosen segment>
"""

import os
import subprocess
import sys

from dotenv import load_dotenv

load_dotenv()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
if not ELEVENLABS_API_KEY:
    print("Set ELEVENLABS_API_KEY in .env first")
    sys.exit(1)

# The reference script — just the narration part (no metadata)
SCRIPT = """So here's the thing about modern software architecture. It's not just about writing code — it's about designing systems that scale, that fail gracefully, and that your team can actually maintain six months from now.

Let's break this down. First: microservices. Are they always the answer? No. Absolutely not. But when you're dealing with teams of fifty-plus engineers? They start to make a lot of sense.

Now, consider this example. You have a monolith processing ten thousand requests per second. That's... actually impressive. But what happens when your authentication module needs an update? You redeploy everything. The database, the API layer, the caching — all of it.

Here's where it gets interesting. With event-driven architecture, you can decouple these components entirely. Think Kafka, think RabbitMQ, think pub-sub patterns. The result? Each service evolves independently.

But wait — and this is crucial — don't over-engineer it. I've seen teams spend months building distributed systems when a simple PostgreSQL database would have been perfectly fine. Seriously. Sometimes the boring solution is the right solution.

The numbers tell the story: seventy-three percent of startups that adopted microservices too early ended up reverting. That's nearly three out of four. Let that sink in for a moment.

So what's the takeaway? Start simple. Measure everything. And only add complexity when the data — not your ego — tells you it's time."""

# Candidate segments with their transcripts (for FISH_REF_AUDIO_TEXT)
# These are timed to land on good sections of the narration
CANDIDATES = [
    {
        "name": "confident_opener",
        "start": 0,
        "transcript": "So here's the thing about modern software architecture. It's not just about writing code — it's about designing systems that scale.",
    },
    {
        "name": "emphatic_denial",
        "start": 12,
        "transcript": "Are they always the answer? No. Absolutely not. But when you're dealing with teams of fifty-plus engineers? They start to make a lot of sense.",
    },
    {
        "name": "building_excitement",
        "start": 35,
        "transcript": "Here's where it gets interesting. With event-driven architecture, you can decouple these components entirely. Think Kafka, think RabbitMQ.",
    },
    {
        "name": "cautionary_casual",
        "start": 47,
        "transcript": "But wait — and this is crucial — don't over-engineer it. I've seen teams spend months building distributed systems when a simple PostgreSQL database would have been perfectly fine.",
    },
    {
        "name": "analytical_reflective",
        "start": 62,
        "transcript": "The numbers tell the story: seventy-three percent of startups that adopted microservices too early ended up reverting. That's nearly three out of four. Let that sink in.",
    },
]

SEGMENT_DURATION = 8  # seconds


def generate_full_audio():
    """Call ElevenLabs API to generate the full narration."""
    import requests

    os.makedirs("output", exist_ok=True)
    output_path = "output/ref_voice_full.mp3"

    # Use the voice ID from config (Rachel default) or override
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")

    print(f"Generating full reference audio via ElevenLabs (voice: {voice_id})...")

    resp = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        headers={
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json",
        },
        json={
            "text": SCRIPT,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 0.15,
                "use_speaker_boost": True,
            },
        },
        timeout=120,
    )
    resp.raise_for_status()

    with open(output_path, "wb") as f:
        f.write(resp.content)

    print(f"Full audio saved: {output_path}")
    return output_path


def extract_candidates(full_audio_path: str):
    """Extract candidate segments and convert to 24kHz mono WAV."""
    os.makedirs("output/ref_candidates", exist_ok=True)

    for c in CANDIDATES:
        wav_path = f"output/ref_candidates/{c['name']}.wav"
        cmd = [
            "ffmpeg", "-y",
            "-i", full_audio_path,
            "-ss", str(c["start"]),
            "-t", str(SEGMENT_DURATION),
            "-ar", "24000",
            "-ac", "1",
            "-acodec", "pcm_s16le",
            wav_path,
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"  {c['name']}: {wav_path}")
        print(f"    Transcript: {c['transcript'][:80]}...")

    # Default: use the "cautionary_casual" segment (good emotional range)
    default = "output/ref_candidates/cautionary_casual.wav"
    final = "output/ref_voice.wav"
    subprocess.run(["cp", default, final], check=True)
    default_transcript = next(c["transcript"] for c in CANDIDATES if c["name"] == "cautionary_casual")

    print(f"\nDefault reference copied to: {final}")
    print(f"\nAdd to .env:")
    print(f"  FISH_REF_AUDIO_PATH={final}")
    print(f"  FISH_REF_AUDIO_TEXT={default_transcript}")
    print(f"\nListen to all candidates in output/ref_candidates/ and swap if you prefer another.")


def main():
    full_path = generate_full_audio()
    extract_candidates(full_path)


if __name__ == "__main__":
    main()
