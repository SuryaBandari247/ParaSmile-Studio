#!/usr/bin/env bash
# Start all dev servers. Ctrl+C kills everything.
# Services: FastAPI backend, Vite frontend, Fish Speech TTS server

trap 'kill 0' EXIT

# Resolve paths relative to this script's directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FISH_SPEECH_DIR="${FISH_SPEECH_DIR:-$SCRIPT_DIR/../fish-speech}"
VENV_DIR="$SCRIPT_DIR/venv"
VENV_PYTHON="$VENV_DIR/bin/python"

# Activate venv if not already active
if [ -z "$VIRTUAL_ENV" ]; then
    source "$VENV_DIR/bin/activate"
    echo "Activated venv at $VENV_DIR"
fi

echo "Starting FastAPI backend on :8000..."
uvicorn studio_api.main:app --reload --port 8000 &

echo "Starting Vite frontend on :5173..."
(cd "$SCRIPT_DIR/frontend" && npm run dev) &

# Start Fish Speech local TTS server if the repo exists
if [ -d "$FISH_SPEECH_DIR" ]; then
    echo "Starting Fish Speech TTS server on :8080..."
    (cd "$FISH_SPEECH_DIR" && "$VENV_PYTHON" -m tools.api_server \
        --listen 0.0.0.0:8080 \
        --llama-checkpoint-path checkpoints/openaudio-s1-mini \
        --decoder-checkpoint-path checkpoints/openaudio-s1-mini/codec.pth \
        --decoder-config-name modded_dac_vq \
        --device mps) &

    # Upload reference voice once server is ready (runs in background)
    if [ -f "$SCRIPT_DIR/output/ref_voice.wav" ]; then
        (cd "$SCRIPT_DIR" && "$VENV_PYTHON" scripts/upload_reference_voice.py) &
    fi
else
    echo "⚠ Fish Speech not found at $FISH_SPEECH_DIR — TTS server not started."
    echo "  Clone it: git clone https://github.com/fishaudio/fish-speech.git $FISH_SPEECH_DIR"
fi

wait
