"""Unit tests for the VoiceSynthesizer orchestrator."""

import os
from dataclasses import dataclass
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from voice_synthesizer.config import VoiceConfig
from voice_synthesizer.exceptions import AuthenticationError, SynthesisError
from voice_synthesizer.synthesizer import VoiceSynthesizer


# Minimal stand-in for SceneBlock / VideoScript to avoid importing script_generator
@dataclass
class FakeSceneBlock:
    scene_number: int
    narration_text: str
    visual_instruction: dict = None
    emotion: str = "neutral"


@dataclass
class FakeVideoScript:
    title: str
    scenes: list
    generated_at: datetime = None
    total_word_count: int = 0
    metadata: dict = None


def _make_fish_config(**overrides) -> VoiceConfig:
    defaults = dict(
        tts_backend="fishaudio",
        fish_api_key="test-fish-key",
        filler_enabled=False,
        output_dir="/tmp/test_audio",
        filler_seed=42,
    )
    defaults.update(overrides)
    return VoiceConfig(**defaults)


def _make_elevenlabs_config(**overrides) -> VoiceConfig:
    defaults = dict(
        tts_backend="elevenlabs",
        elevenlabs_api_key="test-key-123",
        filler_enabled=False,
        output_dir="/tmp/test_audio",
        output_format="mp3_44100_128",
        filler_seed=42,
    )
    defaults.update(overrides)
    return VoiceConfig(**defaults)


def _make_fishspeech_config(**overrides) -> VoiceConfig:
    defaults = dict(
        tts_backend="fishspeech",
        fish_speech_url="http://localhost:8080",
        filler_enabled=False,
        output_dir="/tmp/test_audio",
        filler_seed=42,
    )
    defaults.update(overrides)
    return VoiceConfig(**defaults)


class TestVoiceSynthesizerInit:
    """Initialization tests."""

    @patch("voice_synthesizer.synthesizer.FishSpeechClient")
    def test_fishspeech_backend_initializes(self, mock_client_cls):
        config = _make_fishspeech_config()
        vs = VoiceSynthesizer(config=config)
        assert vs.config.tts_backend == "fishspeech"
        mock_client_cls.assert_called_once()

    @patch("voice_synthesizer.synthesizer.FishAudioClient")
    def test_fishaudio_backend_initializes(self, mock_client_cls):
        config = _make_fish_config()
        vs = VoiceSynthesizer(config=config)
        assert vs.config.tts_backend == "fishaudio"
        mock_client_cls.assert_called_once()

    @patch("voice_synthesizer.synthesizer.ElevenLabsClient")
    @patch("voice_synthesizer.synthesizer.SSMLBuilder")
    def test_elevenlabs_backend_initializes(self, mock_ssml_cls, mock_client_cls):
        config = _make_elevenlabs_config()
        vs = VoiceSynthesizer(config=config)
        assert vs.config.tts_backend == "elevenlabs"

    def test_elevenlabs_missing_key_raises(self, monkeypatch):
        monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
        monkeypatch.delenv("FISH_API_KEY", raising=False)
        # Prevent load_dotenv from re-loading .env values
        monkeypatch.setattr("voice_synthesizer.config.load_dotenv", lambda: None)
        config = VoiceConfig(tts_backend="elevenlabs", elevenlabs_api_key="")
        with pytest.raises(AuthenticationError, match="missing"):
            VoiceSynthesizer(config=config)

    def test_fishaudio_missing_key_raises(self, monkeypatch):
        monkeypatch.delenv("FISH_API_KEY", raising=False)
        monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
        monkeypatch.setattr("voice_synthesizer.config.load_dotenv", lambda: None)
        config = VoiceConfig(tts_backend="fishaudio", fish_api_key="")
        with pytest.raises(AuthenticationError, match="FISH_API_KEY"):
            VoiceSynthesizer(config=config)


class TestVoiceSynthesizerFishAudio:
    """Fish Audio synthesis pipeline tests."""

    @patch("voice_synthesizer.synthesizer.VoiceSynthesizer._calculate_duration")
    @patch("voice_synthesizer.synthesizer.FishAudioClient")
    def test_full_pipeline(self, mock_client_cls, mock_duration):
        mock_client = MagicMock()
        mock_client.synthesize.return_value = "/tmp/test_audio/scene_001.mp3"
        mock_client_cls.return_value = mock_client

        mock_duration.return_value = 5.5

        config = _make_fish_config()
        vs = VoiceSynthesizer(config=config)

        script = FakeVideoScript(
            title="Test",
            scenes=[
                FakeSceneBlock(scene_number=1, narration_text="Hello world."),
                FakeSceneBlock(scene_number=2, narration_text="Second scene."),
            ],
        )

        manifest = vs.synthesize(script)

        assert manifest.total_scenes_synthesized == 2
        assert manifest.total_scenes_failed == 0
        assert len(manifest.entries) == 2
        assert manifest.entries[0].scene_number == 1
        assert manifest.entries[1].scene_number == 2
        assert manifest.total_duration_seconds == 11.0

    @patch("voice_synthesizer.synthesizer.FishAudioClient")
    def test_empty_narration_skipped(self, mock_client_cls):
        mock_client_cls.return_value = MagicMock()
        config = _make_fish_config()
        vs = VoiceSynthesizer(config=config)

        script = FakeVideoScript(
            title="Test",
            scenes=[
                FakeSceneBlock(scene_number=1, narration_text=""),
                FakeSceneBlock(scene_number=2, narration_text="   "),
            ],
        )

        manifest = vs.synthesize(script)

        assert len(manifest.entries) == 0
        assert manifest.total_scenes_synthesized == 0

    @patch("voice_synthesizer.synthesizer.VoiceSynthesizer._calculate_duration")
    @patch("voice_synthesizer.synthesizer.FishAudioClient")
    def test_partial_failure(self, mock_client_cls, mock_duration):
        mock_client = MagicMock()
        mock_client.synthesize.side_effect = [
            "/tmp/test_audio/scene_001.mp3",
            SynthesisError(2, "Fish Audio error"),
        ]
        mock_client_cls.return_value = mock_client

        mock_duration.return_value = 3.0

        config = _make_fish_config()
        vs = VoiceSynthesizer(config=config)

        script = FakeVideoScript(
            title="Test",
            scenes=[
                FakeSceneBlock(scene_number=1, narration_text="Scene one."),
                FakeSceneBlock(scene_number=2, narration_text="Scene two."),
            ],
        )

        manifest = vs.synthesize(script)

        assert manifest.total_scenes_synthesized == 1
        assert manifest.total_scenes_failed == 1
        assert len(manifest.entries) == 2
        assert manifest.entries[0].file_path is not None
        assert manifest.entries[1].file_path is None
        assert manifest.entries[1].error is not None

    @patch("voice_synthesizer.synthesizer.VoiceSynthesizer._calculate_duration")
    @patch("voice_synthesizer.synthesizer.FishAudioClient")
    def test_scenes_processed_in_order(self, mock_client_cls, mock_duration):
        mock_client = MagicMock()
        mock_client.synthesize.return_value = "/tmp/test_audio/scene_001.mp3"
        mock_client_cls.return_value = mock_client

        mock_duration.return_value = 1.0

        config = _make_fish_config()
        vs = VoiceSynthesizer(config=config)

        script = FakeVideoScript(
            title="Test",
            scenes=[
                FakeSceneBlock(scene_number=3, narration_text="Third."),
                FakeSceneBlock(scene_number=1, narration_text="First."),
                FakeSceneBlock(scene_number=2, narration_text="Second."),
            ],
        )

        manifest = vs.synthesize(script)

        scene_numbers = [e.scene_number for e in manifest.entries]
        assert scene_numbers == [1, 2, 3]

    @patch("voice_synthesizer.synthesizer.VoiceSynthesizer._calculate_duration")
    @patch("voice_synthesizer.synthesizer.FishAudioClient")
    def test_manifest_metadata(self, mock_client_cls, mock_duration):
        mock_client = MagicMock()
        mock_client.synthesize.return_value = "/tmp/test_audio/scene_001.mp3"
        mock_client_cls.return_value = mock_client

        mock_duration.return_value = 2.5

        config = _make_fish_config()
        vs = VoiceSynthesizer(config=config)

        script = FakeVideoScript(
            title="Test",
            scenes=[
                FakeSceneBlock(scene_number=1, narration_text="Hello world."),
            ],
        )

        manifest = vs.synthesize(script)

        assert manifest.total_characters_processed == len("Hello world.")
        assert manifest.generated_at is not None
        d = manifest.to_dict()
        assert "entries" in d
        assert "generated_at" in d

    @patch("voice_synthesizer.synthesizer.VoiceSynthesizer._calculate_duration")
    @patch("voice_synthesizer.synthesizer.FishAudioClient")
    def test_pause_markers_stripped(self, mock_client_cls, mock_duration):
        """Fish Audio path should strip {{pause:Nms}} markers from text."""
        mock_client = MagicMock()
        mock_client.synthesize.return_value = "/tmp/test_audio/scene_001.mp3"
        mock_client_cls.return_value = mock_client

        mock_duration.return_value = 2.0

        config = _make_fish_config(filler_enabled=False)
        vs = VoiceSynthesizer(config=config)

        script = FakeVideoScript(
            title="Test",
            scenes=[
                FakeSceneBlock(
                    scene_number=1,
                    narration_text="Hello {{pause:250ms}} world.",
                ),
            ],
        )

        manifest = vs.synthesize(script)

        # Verify the text sent to client has markers stripped
        call_args = mock_client.synthesize.call_args
        sent_text = call_args[0][0] if call_args[0] else call_args[1].get("text", "")
        assert "{{pause:" not in sent_text
        assert manifest.total_scenes_synthesized == 1

    @patch("voice_synthesizer.synthesizer.VoiceSynthesizer._calculate_duration")
    @patch("voice_synthesizer.synthesizer.FishAudioClient")
    def test_emotion_tag_prepended_cloud(self, mock_client_cls, mock_duration):
        """Fish Audio cloud (full S1 model) should prepend emotion tags."""
        mock_client = MagicMock()
        mock_client.synthesize.return_value = "/tmp/test_audio/scene_001.mp3"
        mock_client_cls.return_value = mock_client

        mock_duration.return_value = 2.0

        config = _make_fish_config(filler_enabled=False)
        vs = VoiceSynthesizer(config=config)

        script = FakeVideoScript(
            title="Test",
            scenes=[
                FakeSceneBlock(
                    scene_number=1,
                    narration_text="This is amazing news!",
                    emotion="excited",
                ),
            ],
        )

        manifest = vs.synthesize(script)

        call_args = mock_client.synthesize.call_args
        sent_text = call_args[0][0] if call_args[0] else call_args[1].get("text", "")
        assert sent_text.startswith("(excited)")
        assert "amazing news" in sent_text

    @patch("voice_synthesizer.synthesizer.VoiceSynthesizer._calculate_duration")
    @patch("voice_synthesizer.synthesizer.FishAudioClient")
    def test_neutral_emotion_not_prepended(self, mock_client_cls, mock_duration):
        """Neutral emotion should not add a tag prefix (cloud or local)."""
        mock_client = MagicMock()
        mock_client.synthesize.return_value = "/tmp/test_audio/scene_001.mp3"
        mock_client_cls.return_value = mock_client

        mock_duration.return_value = 2.0

        config = _make_fish_config(filler_enabled=False)
        vs = VoiceSynthesizer(config=config)

        script = FakeVideoScript(
            title="Test",
            scenes=[
                FakeSceneBlock(
                    scene_number=1,
                    narration_text="Just a normal statement.",
                    emotion="neutral",
                ),
            ],
        )

        manifest = vs.synthesize(script)

        call_args = mock_client.synthesize.call_args
        sent_text = call_args[0][0] if call_args[0] else call_args[1].get("text", "")
        assert not sent_text.startswith("(")


class TestVoiceSynthesizerFishSpeech:
    """Fish Speech local backend tests."""

    @patch("voice_synthesizer.synthesizer.VoiceSynthesizer._calculate_duration")
    @patch("voice_synthesizer.synthesizer.FishSpeechClient")
    def test_full_pipeline(self, mock_client_cls, mock_duration):
        mock_client = MagicMock()
        mock_client.synthesize.return_value = "/tmp/test_audio/scene_001.wav"
        mock_client_cls.return_value = mock_client
        mock_duration.return_value = 5.0

        config = _make_fishspeech_config()
        vs = VoiceSynthesizer(config=config)

        script = FakeVideoScript(
            title="Test",
            scenes=[
                FakeSceneBlock(scene_number=1, narration_text="Hello world."),
                FakeSceneBlock(scene_number=2, narration_text="Second scene."),
            ],
        )

        manifest = vs.synthesize(script)
        assert manifest.total_scenes_synthesized == 2
        assert manifest.total_scenes_failed == 0

    @patch("voice_synthesizer.synthesizer.VoiceSynthesizer._calculate_duration")
    @patch("voice_synthesizer.synthesizer.FishSpeechClient")
    def test_emotion_tag_prepended_local(self, mock_client_cls, mock_duration):
        """Fish Speech local (s1-mini) should prepend emotion tags — model supports them."""
        mock_client = MagicMock()
        mock_client.synthesize.return_value = "/tmp/test_audio/scene_001.wav"
        mock_client_cls.return_value = mock_client
        mock_duration.return_value = 2.0

        config = _make_fishspeech_config(filler_enabled=False)
        vs = VoiceSynthesizer(config=config)

        script = FakeVideoScript(
            title="Test",
            scenes=[
                FakeSceneBlock(scene_number=1, narration_text="Wow!", emotion="excited"),
            ],
        )

        vs.synthesize(script)
        call_args = mock_client.synthesize.call_args
        sent_text = call_args[0][0] if call_args[0] else call_args[1].get("text", "")
        assert sent_text.startswith("(excited)")
        assert "Wow" in sent_text


class TestVoiceSynthesizerElevenLabs:
    """ElevenLabs backward compatibility tests."""

    @patch("voice_synthesizer.synthesizer.VoiceSynthesizer._calculate_duration")
    @patch("voice_synthesizer.synthesizer.VoiceSynthesizer._write_audio")
    @patch("voice_synthesizer.synthesizer.ElevenLabsClient")
    @patch("voice_synthesizer.synthesizer.SSMLBuilder")
    def test_elevenlabs_pipeline(self, mock_ssml_cls, mock_client_cls, mock_write, mock_duration):
        mock_client = MagicMock()
        mock_client.synthesize.return_value = b"fake-audio"
        mock_client_cls.return_value = mock_client

        mock_ssml = MagicMock()
        mock_ssml.build.return_value = "<speak>Hello</speak>"
        mock_ssml_cls.return_value = mock_ssml

        mock_write.return_value = "/tmp/test_audio/scene_001.mp3"
        mock_duration.return_value = 5.5

        config = _make_elevenlabs_config()
        vs = VoiceSynthesizer(config=config)

        script = FakeVideoScript(
            title="Test",
            scenes=[FakeSceneBlock(scene_number=1, narration_text="Hello world.")],
        )

        manifest = vs.synthesize(script)

        assert manifest.total_scenes_synthesized == 1
        mock_ssml.build.assert_called_once()
        mock_client.synthesize.assert_called_once()


class TestVoiceSynthesizerWithFillers:
    """Tests with filler injection enabled."""

    @patch("voice_synthesizer.synthesizer.VoiceSynthesizer._calculate_duration")
    @patch("voice_synthesizer.synthesizer.FishAudioClient")
    def test_fillers_enabled(self, mock_client_cls, mock_duration):
        mock_client = MagicMock()
        mock_client.synthesize.return_value = "/tmp/test_audio/scene_001.mp3"
        mock_client_cls.return_value = mock_client

        mock_duration.return_value = 5.0

        config = _make_fish_config(filler_enabled=True, filler_density=0.5, filler_seed=42)
        vs = VoiceSynthesizer(config=config)

        script = FakeVideoScript(
            title="Test",
            scenes=[
                FakeSceneBlock(
                    scene_number=1,
                    narration_text="The market is volatile, and investors are worried, but analysts remain calm.",
                ),
            ],
        )

        manifest = vs.synthesize(script)
        assert manifest.total_scenes_synthesized == 1

        # Verify pause markers were stripped before sending to Fish Audio
        call_args = mock_client.synthesize.call_args
        sent_text = call_args[0][0] if call_args[0] else call_args[1].get("text", "")
        assert "{{pause:" not in sent_text
