#!/usr/bin/env python3
"""Prepare a reference audio clip for Fish Audio voice cloning.

Usage:
    # From a YouTube video (downloads and extracts a segment):
    python scripts/prepare_ref_audio.py --youtube "https://youtube.com/watch?v=..." --start 30 --duration 8

    # From an existing audio/video file:
    python scripts/prepare_ref_audio.py --input my_recording.mp3 --start 0 --duration 8

    # Record from microphone (requires sounddevice):
    python scripts/prepare_ref_audio.py --record --duration 8

The output is a 24kHz mono WAV file at output/ref_voice.wav.
After generating, add to your .env:
    FISH_REF_AUDIO_PATH=output/ref_voice.wav
    FISH_REF_AUDIO_TEXT=<exact transcript of the clip>
"""

import argparse
import os
import subprocess
import sys


OUTPUT_PATH = "output/ref_voice.wav"


def from_file(input_path: str, start: float, duration: float) -> None:
    """Extract and convert a segment from an audio/video file."""
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-ss", str(start),
        "-t", str(duration),
        "-ar", "24000",
        "-ac", "1",
        "-acodec", "pcm_s16le",
        OUTPUT_PATH,
    ]
    subprocess.run(cmd, check=True)
    print(f"Reference audio saved to {OUTPUT_PATH}")


def from_youtube(url: str, start: float, duration: float) -> None:
    """Download audio from YouTube and extract a segment."""
    try:
        import yt_dlp
    except ImportError:
        print("yt-dlp required: pip install yt-dlp")
        sys.exit(1)

    tmp = "output/_yt_tmp.wav"
    os.makedirs("output", exist_ok=True)

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": "output/_yt_tmp.%(ext)s",
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "wav"}],
        "quiet": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        print(f"Downloading audio from {url}...")
        ydl.download([url])

    from_file(tmp, start, duration)
    os.remove(tmp)


def from_mic(duration: float) -> None:
    """Record from microphone."""
    try:
        import sounddevice as sd
        import soundfile as sf
    except ImportError:
        print("Required: pip install sounddevice soundfile")
        sys.exit(1)

    sr = 24000
    print(f"Recording {duration}s from microphone... Speak now!")
    audio = sd.rec(int(duration * sr), samplerate=sr, channels=1, dtype="float32")
    sd.wait()
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    sf.write(OUTPUT_PATH, audio, sr)
    print(f"Reference audio saved to {OUTPUT_PATH}")


def main():
    parser = argparse.ArgumentParser(description="Prepare Fish Audio reference audio")
    parser.add_argument("--input", help="Path to existing audio/video file")
    parser.add_argument("--youtube", help="YouTube URL to extract from")
    parser.add_argument("--record", action="store_true", help="Record from microphone")
    parser.add_argument("--start", type=float, default=0, help="Start time in seconds")
    parser.add_argument("--duration", type=float, default=8, help="Duration in seconds (5-10 recommended)")
    args = parser.parse_args()

    if args.record:
        from_mic(args.duration)
    elif args.youtube:
        from_youtube(args.youtube, args.start, args.duration)
    elif args.input:
        from_file(args.input, args.start, args.duration)
    else:
        parser.print_help()
        print("\nTip: Find a YouTube tech narrator you like and extract 5-10s of clean speech.")
        sys.exit(1)

    print(f"\nNext steps:")
    print(f"  1. Listen to {OUTPUT_PATH} and make sure it's clean speech (no music/noise)")
    print(f"  2. Add to .env:")
    print(f"     FISH_REF_AUDIO_PATH={OUTPUT_PATH}")
    print(f"     FISH_REF_AUDIO_TEXT=<exact transcript of the clip>")


if __name__ == "__main__":
    main()
