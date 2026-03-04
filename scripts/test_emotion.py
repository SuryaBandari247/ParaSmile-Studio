"""Quick CLI test: same sentence, two emotions, direct to local Fish Speech server."""

import os
import requests
import sys

BASE_URL = os.getenv("FISH_SPEECH_URL", "http://localhost:8080")
REF_ID = os.getenv("FISH_REFERENCE_ID", "narrator")
OUTPUT_DIR = "output/emotion_test"

VARIANTS = [
    ("multi_emotion", "(excited) Welcome back to the channel! (neutral) Today we are diving into the M4 Pro benchmarks. (whispering) You won't believe how fast this thing actually is. (serious) But first, we need to talk about the cooling."),
]

os.makedirs(OUTPUT_DIR, exist_ok=True)

for emotion, text in VARIANTS:
    print(f"\n{'='*60}")
    print(f"Emotion: {emotion}")
    print(f"Text: {text[:80]}...")
    print(f"{'='*60}")

    payload = {
        "text": text,
        "format": "wav",
        "chunk_length": 150,
        "normalize": True,
        "temperature": 0.9,
        "top_p": 0.9,
        "repetition_penalty": 1.2,
        "max_new_tokens": 2048,
        "seed": 0,
        # No reference voice — let the model pick its own voice freely
        # so emotion conditioning isn't overridden by the reference timbre
        "use_memory_cache": "off",
    }

    out_path = os.path.join(OUTPUT_DIR, f"emotion_{emotion}.wav")

    try:
        resp = requests.post(f"{BASE_URL}/v1/tts", json=payload, stream=True, timeout=120)
        if resp.status_code != 200:
            print(f"  ERROR: HTTP {resp.status_code} — {resp.text[:200]}")
            continue

        with open(out_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        size = os.path.getsize(out_path)
        # Quick WAV duration calc (PCM 24kHz 16-bit mono)
        duration = max(0, (size - 44)) / (24000 * 2)
        print(f"  ✓ Saved: {out_path} ({size:,} bytes, ~{duration:.1f}s)")

    except requests.exceptions.ConnectionError:
        print(f"  ERROR: Can't connect to Fish Speech at {BASE_URL}")
        print(f"  Is the server running? Start it with: bash dev.sh")
        sys.exit(1)
    except Exception as e:
        print(f"  ERROR: {e}")

print(f"\nDone. Listen to the files in {OUTPUT_DIR}/ and compare.")
