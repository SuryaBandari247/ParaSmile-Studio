# Design Document: F5-TTS MLX Migration

## Overview

Replace ElevenLabs cloud TTS with local F5-TTS MLX inference. The voice_synthesizer module keeps its architecture but swaps the TTS backend and adds a PacingProcessor to handle pause insertion at the audio waveform level (since F5-TTS doesn't support SSML).

### Before (ElevenLabs)
```
narration → FillerInjector → SSMLBuilder → ElevenLabsClient (HTTP) → MP3 bytes → disk
```

### After (F5-TTS MLX)
```
narration → FillerInjector → PacingProcessor.prepare() → F5TTSClient (local) → WAV → PacingProcessor.apply() → WAV with pauses → disk
```

## Architecture

### Data Flow

```
VoiceSynthesizer.synthesize(video_script)
  │
  ├─ For each scene:
  │   │
  │   ├─ 1. FillerInjector.inject(narration_text)
  │   │      → text with filler words + {{pause:Nms}} markers
  │   │
  │   ├─ 2. PacingProcessor.prepare(fillered_text)
  │   │      → returns (clean_text, pause_map)
  │   │      clean_text: plain text with all markers/SSML stripped
  │   │      pause_map: list of (position, duration_ms) for silence insertion
  │   │
  │   ├─ 3. F5TTSClient.synthesize(clean_text, scene_number)
  │   │      → generates WAV via f5_tts_mlx.generate.generate()
  │   │      → returns file_path to raw WAV
  │   │
  │   ├─ 4. PacingProcessor.apply_pauses(wav_path, pause_map)
  │   │      → reads WAV, inserts silence at sentence/paragraph boundaries
  │   │      → overwrites WAV with paced version
  │   │
  │   └─ 5. Calculate duration, create SceneAudio entry
  │
  └─ Build AudioManifest
```

## Components

### F5TTSClient (`voice_synthesizer/f5tts_client.py`)

```python
class F5TTSClient:
    """Local TTS using F5-TTS MLX."""

    def __init__(
        self,
        ref_audio_path: str | None = None,
        ref_audio_text: str | None = None,
        speed: float = 1.0,
        steps: int = 8,
        method: str = "rk4",
        cfg_strength: float = 2.0,
        sway_sampling_coef: float = -1.0,
        seed: int | None = None,
        quantization_bits: int | None = None,
        output_dir: str = "output/audio",
    ):
        """Load F5-TTS model once. Reuse for all scenes."""

    def synthesize(self, text: str, scene_number: int = 0) -> str:
        """Generate speech from plain text.
        
        Returns:
            Absolute path to generated WAV file.
        """
```

Key implementation details:
- Calls `f5_tts_mlx.generate.generate()` with `output_path` set to the scene WAV file
- Model is loaded once via `F5TTS.from_pretrained()` at init (the generate function handles this internally, but we call it per-scene)
- Reference audio defaults to F5-TTS's bundled sample if not configured
- Output is always 24kHz mono WAV (F5-TTS native format)

### PacingProcessor (`voice_synthesizer/pacing_processor.py`)

```python
@dataclass
class PauseInstruction:
    """A pause to insert at a text position."""
    char_position: int      # position in original text
    duration_ms: int        # silence duration
    pause_type: str         # "sentence", "paragraph", "filler", "thinking"

class PacingProcessor:
    """Converts text with pause markers into clean text + pause map,
    then applies pauses as silence in the audio waveform."""

    SAMPLE_RATE = 24_000

    def __init__(
        self,
        sentence_pause_ms: int = 400,
        paragraph_pause_ms: int = 800,
    ):
        pass

    def prepare(self, text: str) -> tuple[str, list[PauseInstruction]]:
        """Extract pause markers and sentence/paragraph boundaries.
        
        Returns:
            (clean_text, pause_instructions)
            clean_text: plain text ready for F5-TTS
            pause_instructions: ordered list of pauses to insert
        """

    def apply_pauses(self, wav_path: str, pauses: list[PauseInstruction]) -> None:
        """Insert silence segments into the WAV file at proportional positions.
        
        Since we can't map character positions to exact audio timestamps,
        we distribute pauses proportionally based on character position
        relative to total text length.
        """
```

Pause insertion strategy:
- Character positions from `prepare()` are mapped to audio timestamps proportionally: `audio_position = (char_position / total_chars) * audio_duration`
- Silence is generated as zero-valued samples at 24kHz
- The WAV is read with `soundfile`, silence arrays are inserted, and the result is written back

### Updated VoiceConfig

```python
@dataclass
class VoiceConfig:
    # F5-TTS settings (primary)
    ref_audio_path: str | None = None       # Path to reference WAV (24kHz mono)
    ref_audio_text: str | None = None       # Transcript of reference audio
    f5_speed: float = 1.0                   # Speed factor (0.5-2.0)
    f5_steps: int = 8                       # Diffusion steps
    f5_method: str = "rk4"                  # ODE method: euler, midpoint, rk4
    f5_cfg_strength: float = 2.0            # Classifier-free guidance strength
    f5_sway_coef: float = -1.0              # Sway sampling coefficient
    f5_seed: int | None = None              # Seed for reproducibility
    f5_quantization_bits: int | None = None  # None, 4, or 8

    # ElevenLabs settings (optional, backward compat)
    elevenlabs_api_key: str = ""
    voice_id: str = "21m00Tcm4TlvDq8ikWAM"
    model_id: str = "eleven_multilingual_v2"
    stability: float = 0.5
    similarity_boost: float = 0.75
    style: float = 0.0

    # TTS backend selection
    tts_backend: str = "f5tts"  # "f5tts" or "elevenlabs"

    # SSML/pacing (shared)
    sentence_pause_ms: int = 400
    paragraph_pause_ms: int = 800
    speaking_rate: str = "medium"

    # Filler injection (unchanged)
    filler_enabled: bool = True
    filler_density: float = 0.15
    restart_probability: float = 0.05
    min_thinking_pause_ms: int = 150
    max_thinking_pause_ms: int = 500
    filler_seed: int | None = None
    filler_vocabulary: list[str] | None = None

    # Output
    output_format: str = "wav_24000"  # Changed default from mp3_44100_128
    output_dir: str = "output/audio"
    log_level: str = "INFO"
```

### Updated VoiceSynthesizer

The synthesizer selects the TTS backend based on `config.tts_backend`:

```python
class VoiceSynthesizer:
    def __init__(self, config: VoiceConfig | None = None):
        self.config = config or VoiceConfig()
        
        # Initialize filler injector (unchanged)
        self.filler_injector = FillerInjector(...) if config.filler_enabled else None
        
        # Initialize TTS backend
        if self.config.tts_backend == "f5tts":
            self.client = F5TTSClient(
                ref_audio_path=self.config.ref_audio_path,
                ref_audio_text=self.config.ref_audio_text,
                speed=self.config.f5_speed,
                steps=self.config.f5_steps,
                method=self.config.f5_method,
                cfg_strength=self.config.f5_cfg_strength,
                sway_sampling_coef=self.config.f5_sway_coef,
                seed=self.config.f5_seed,
                quantization_bits=self.config.f5_quantization_bits,
                output_dir=self.config.output_dir,
            )
            self.pacing = PacingProcessor(
                sentence_pause_ms=self.config.sentence_pause_ms,
                paragraph_pause_ms=self.config.paragraph_pause_ms,
            )
            self.ssml_builder = None
        else:
            # ElevenLabs path (backward compat)
            self.client = ElevenLabsClient(...)
            self.ssml_builder = SSMLBuilder(...)
            self.pacing = None
```

### Updated Synthesis Loop (F5-TTS path)

```python
# For each scene:
text = narration
if self.filler_injector:
    text = self.filler_injector.inject(text)

if self.pacing:  # F5-TTS path
    clean_text, pauses = self.pacing.prepare(text)
    file_path = self.client.synthesize(clean_text, scene_number=sn)
    self.pacing.apply_pauses(file_path, pauses)
else:  # ElevenLabs path
    ssml = self.ssml_builder.build(text)
    audio_bytes = self.client.synthesize(ssml, scene_number=sn)
    file_path = self._write_audio(audio_bytes, sn)
```

## File Changes Summary

| File | Change |
|------|--------|
| `voice_synthesizer/f5tts_client.py` | NEW — F5-TTS MLX client |
| `voice_synthesizer/pacing_processor.py` | NEW — Pause extraction + silence insertion |
| `voice_synthesizer/config.py` | MODIFY — Add F5-TTS fields, tts_backend selector, change defaults |
| `voice_synthesizer/synthesizer.py` | MODIFY — Support both backends, F5-TTS pacing path |
| `voice_synthesizer/__init__.py` | MODIFY — Export new classes |
| `voice_synthesizer/exceptions.py` | MODIFY — Update AuthenticationError to be ElevenLabs-specific |
| `requirements.txt` | MODIFY — Add f5-tts-mlx, soundfile |
| `.env.example` | MODIFY — Add F5-TTS config, mark ElevenLabs as optional |
| `pipeline_ui/panels/synthesize_panel.py` | MODIFY — Update status text |
| `run_pipeline.py` | MODIFY — Update status text |
| `.kiro/steering/product.md` | MODIFY — Update engineering standards |

## Key Design Decisions

1. **Dual backend support**: Both F5-TTS and ElevenLabs are supported via `tts_backend` config. F5-TTS is the default. This avoids breaking existing setups.

2. **PacingProcessor instead of SSML**: F5-TTS takes plain text, so pacing is achieved by inserting silence into the generated audio waveform. The FillerInjector's `{{pause:Nms}}` markers are consumed by PacingProcessor instead of SSMLBuilder.

3. **WAV output**: F5-TTS outputs 24kHz mono WAV natively. Converting to MP3 would add a dependency (lame/ffmpeg) for no benefit — the Asset Orchestrator's FFmpeg compositor can handle WAV input.

4. **Model loaded once**: The F5-TTS model is loaded at `F5TTSClient.__init__()` and reused for all scenes. On M4 Pro 48GB, the full model fits comfortably in memory.

5. **Proportional pause mapping**: Since we can't know exact character-to-timestamp mapping from F5-TTS output, pauses are inserted at proportional positions in the audio. This is approximate but effective for sentence/paragraph boundaries.
