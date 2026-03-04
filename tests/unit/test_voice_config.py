"""Unit tests for VoiceConfig."""

import pytest

from voice_synthesizer.config import VoiceConfig
from voice_synthesizer.exceptions import ValidationError


class TestVoiceConfigDefaults:
    """Default value tests."""

    def test_default_tts_backend(self):
        config = VoiceConfig()
        assert config.tts_backend == "fishspeech"

    def test_default_fish_speed(self, monkeypatch):
        monkeypatch.delenv("FISH_SPEED", raising=False)
        monkeypatch.setattr("voice_synthesizer.config.load_dotenv", lambda: None)
        config = VoiceConfig()
        assert config.fish_speed == 1.0

    def test_default_fish_volume(self):
        config = VoiceConfig()
        assert config.fish_volume == 0.0

    def test_default_fish_format(self):
        config = VoiceConfig()
        assert config.fish_format == "mp3"

    def test_default_fish_temperature(self):
        config = VoiceConfig()
        assert config.fish_temperature == 0.7

    def test_default_fish_top_p(self):
        config = VoiceConfig()
        assert config.fish_top_p == 0.7

    def test_default_fish_chunk_length(self):
        config = VoiceConfig()
        assert config.fish_chunk_length == 200

    def test_default_fish_reference_id_none(self, monkeypatch):
        monkeypatch.delenv("FISH_REFERENCE_ID", raising=False)
        monkeypatch.setattr("voice_synthesizer.config.load_dotenv", lambda: None)
        config = VoiceConfig()
        assert config.fish_reference_id is None

    def test_default_voice_id(self, monkeypatch):
        monkeypatch.delenv("ELEVENLABS_VOICE_ID", raising=False)
        monkeypatch.setattr("voice_synthesizer.config.load_dotenv", lambda: None)
        config = VoiceConfig()
        assert config.voice_id == "21m00Tcm4TlvDq8ikWAM"

    def test_default_model_id(self):
        config = VoiceConfig()
        assert config.model_id == "eleven_multilingual_v2"

    def test_default_stability(self):
        config = VoiceConfig()
        assert config.stability == 0.5

    def test_default_filler_enabled(self):
        config = VoiceConfig()
        assert config.filler_enabled is True

    def test_default_filler_density(self):
        config = VoiceConfig()
        assert config.filler_density == 0.15

    def test_default_output_dir(self):
        config = VoiceConfig()
        assert config.output_dir == "output/audio"

    def test_default_speaking_rate(self):
        config = VoiceConfig()
        assert config.speaking_rate == "medium"

    def test_default_sentence_pause(self):
        config = VoiceConfig()
        assert config.sentence_pause_ms == 500

    def test_default_paragraph_pause(self):
        config = VoiceConfig()
        assert config.paragraph_pause_ms == 1000


class TestVoiceConfigValidation:
    """Validation tests."""

    def test_fish_speed_too_high(self):
        with pytest.raises(ValidationError, match="fish_speed"):
            VoiceConfig(fish_speed=2.5)

    def test_fish_speed_too_low(self):
        with pytest.raises(ValidationError, match="fish_speed"):
            VoiceConfig(fish_speed=0.3)

    def test_fish_speed_valid_edges(self):
        config = VoiceConfig(fish_speed=0.5)
        assert config.fish_speed == 0.5
        config = VoiceConfig(fish_speed=2.0)
        assert config.fish_speed == 2.0

    def test_fish_volume_too_high(self):
        with pytest.raises(ValidationError, match="fish_volume"):
            VoiceConfig(fish_volume=25.0)

    def test_fish_volume_too_low(self):
        with pytest.raises(ValidationError, match="fish_volume"):
            VoiceConfig(fish_volume=-25.0)

    def test_fish_temperature_too_high(self):
        with pytest.raises(ValidationError, match="fish_temperature"):
            VoiceConfig(fish_temperature=1.5)

    def test_fish_top_p_too_high(self):
        with pytest.raises(ValidationError, match="fish_top_p"):
            VoiceConfig(fish_top_p=1.5)

    def test_fish_chunk_length_too_low(self):
        with pytest.raises(ValidationError, match="fish_chunk_length"):
            VoiceConfig(fish_chunk_length=50)

    def test_fish_chunk_length_too_high(self):
        with pytest.raises(ValidationError, match="fish_chunk_length"):
            VoiceConfig(fish_chunk_length=500)

    def test_fish_format_invalid(self):
        with pytest.raises(ValidationError, match="fish_format"):
            VoiceConfig(fish_format="flac")

    def test_fish_format_valid_options(self):
        for fmt in ("mp3", "wav", "pcm", "opus"):
            config = VoiceConfig(fish_format=fmt)
            assert config.fish_format == fmt

    def test_stability_too_high(self):
        with pytest.raises(ValidationError, match="stability"):
            VoiceConfig(stability=1.5)

    def test_stability_too_low(self):
        with pytest.raises(ValidationError, match="stability"):
            VoiceConfig(stability=-0.1)

    def test_similarity_boost_too_high(self):
        with pytest.raises(ValidationError, match="similarity_boost"):
            VoiceConfig(similarity_boost=2.0)

    def test_style_too_high(self):
        with pytest.raises(ValidationError, match="style"):
            VoiceConfig(style=1.1)

    def test_filler_density_too_high(self):
        with pytest.raises(ValidationError, match="filler_density"):
            VoiceConfig(filler_density=1.5)

    def test_filler_density_too_low(self):
        with pytest.raises(ValidationError, match="filler_density"):
            VoiceConfig(filler_density=-0.1)

    def test_restart_probability_too_high(self):
        with pytest.raises(ValidationError, match="restart_probability"):
            VoiceConfig(restart_probability=1.1)

    def test_valid_edge_values(self):
        config = VoiceConfig(
            stability=0.0,
            similarity_boost=1.0,
            style=0.0,
            filler_density=0.0,
            restart_probability=1.0,
        )
        assert config.stability == 0.0
        assert config.similarity_boost == 1.0
        assert config.restart_probability == 1.0


class TestVoiceConfigEnvLoading:
    """Environment variable loading tests."""

    def test_fish_api_key_from_constructor(self):
        config = VoiceConfig(fish_api_key="direct-key")
        assert config.fish_api_key == "direct-key"

    def test_fish_api_key_from_env(self, monkeypatch):
        monkeypatch.setenv("FISH_API_KEY", "env-key")
        config = VoiceConfig(fish_api_key="")
        assert config.fish_api_key == "env-key"

    def test_elevenlabs_api_key_from_constructor(self):
        config = VoiceConfig(elevenlabs_api_key="direct-key")
        assert config.elevenlabs_api_key == "direct-key"

    def test_elevenlabs_api_key_from_env(self, monkeypatch):
        monkeypatch.setenv("ELEVENLABS_API_KEY", "env-key")
        config = VoiceConfig(elevenlabs_api_key="")
        assert config.elevenlabs_api_key == "env-key"

    def test_tts_backend_from_env(self, monkeypatch):
        monkeypatch.setenv("TTS_BACKEND", "elevenlabs")
        config = VoiceConfig()
        assert config.tts_backend == "elevenlabs"

    def test_fish_speed_from_env(self, monkeypatch):
        monkeypatch.setenv("FISH_SPEED", "1.5")
        config = VoiceConfig()
        assert config.fish_speed == 1.5

    def test_fish_reference_id_from_env(self, monkeypatch):
        monkeypatch.setenv("FISH_REFERENCE_ID", "voice-abc-123")
        config = VoiceConfig()
        assert config.fish_reference_id == "voice-abc-123"

    def test_fish_temperature_from_env(self, monkeypatch):
        monkeypatch.setenv("FISH_TEMPERATURE", "0.3")
        config = VoiceConfig()
        assert config.fish_temperature == 0.3
