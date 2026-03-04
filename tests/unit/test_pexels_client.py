"""Unit tests for PexelsClient."""

import os
from unittest.mock import MagicMock, patch, mock_open

import pytest

from asset_orchestrator.pexels_client import PexelsClient
from asset_orchestrator.exceptions import ConfigurationError, StockFootageError


class TestPexelsClientInit:
    """Test PexelsClient initialization."""

    def test_missing_api_key_raises_configuration_error(self):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ConfigurationError, match="PEXELS_API_KEY"):
                PexelsClient(api_key="")

    def test_env_var_api_key(self, tmp_path):
        with patch.dict(os.environ, {"PEXELS_API_KEY": "test-key"}):
            client = PexelsClient(cache_dir=str(tmp_path / "cache"))
            assert client._api_key == "test-key"

    def test_explicit_api_key_overrides_env(self, tmp_path):
        with patch.dict(os.environ, {"PEXELS_API_KEY": "env-key"}):
            client = PexelsClient(api_key="explicit-key", cache_dir=str(tmp_path / "cache"))
            assert client._api_key == "explicit-key"

    def test_cache_dir_created(self, tmp_path):
        cache = tmp_path / "stock_cache"
        PexelsClient(api_key="test-key", cache_dir=str(cache))
        assert cache.is_dir()


class TestSearchVideos:
    """Test PexelsClient.search_videos."""

    @pytest.fixture
    def client(self, tmp_path):
        return PexelsClient(api_key="test-key", cache_dir=str(tmp_path / "cache"))

    def test_search_returns_parsed_results(self, client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "videos": [
                {
                    "id": 123,
                    "url": "https://pexels.com/video/123",
                    "duration": 10,
                    "width": 1920,
                    "height": 1080,
                    "video_files": [{"link": "https://dl.pexels.com/123.mp4", "height": 1080}],
                },
            ]
        }
        mock_resp.raise_for_status = MagicMock()
        client._session.get = MagicMock(return_value=mock_resp)

        results = client.search_videos("taxes finance")
        assert len(results) == 1
        assert results[0]["id"] == 123
        assert results[0]["duration"] == 10

    def test_search_empty_results(self, client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"videos": []}
        mock_resp.raise_for_status = MagicMock()
        client._session.get = MagicMock(return_value=mock_resp)

        results = client.search_videos("xyznonexistent")
        assert results == []

    def test_search_filters_by_min_duration(self, client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "videos": [
                {"id": 1, "duration": 3, "width": 1920, "height": 1080, "video_files": []},
                {"id": 2, "duration": 10, "width": 1920, "height": 1080, "video_files": []},
            ]
        }
        mock_resp.raise_for_status = MagicMock()
        client._session.get = MagicMock(return_value=mock_resp)

        results = client.search_videos("test", min_duration=5)
        assert len(results) == 1
        assert results[0]["id"] == 2

    def test_search_handles_api_error(self, client):
        import requests as req
        client._session.get = MagicMock(side_effect=req.ConnectionError("timeout"))
        results = client.search_videos("test")
        assert results == []


class TestDownloadVideo:
    """Test PexelsClient.download_video."""

    @pytest.fixture
    def client(self, tmp_path):
        return PexelsClient(api_key="test-key", cache_dir=str(tmp_path / "cache"))

    def test_download_selects_best_quality(self, client):
        video_result = {
            "id": 42,
            "video_files": [
                {"link": "https://dl.pexels.com/42_720.mp4", "height": 720, "width": 1280},
                {"link": "https://dl.pexels.com/42_1080.mp4", "height": 1080, "width": 1920},
                {"link": "https://dl.pexels.com/42_4k.mp4", "height": 2160, "width": 3840},
            ],
        }
        mock_resp = MagicMock()
        mock_resp.iter_content = MagicMock(return_value=[b"fake video data"])
        mock_resp.raise_for_status = MagicMock()
        client._session.get = MagicMock(return_value=mock_resp)

        path = client.download_video(video_result)
        assert path.endswith("pexels_42.mp4")
        assert os.path.isfile(path)

    def test_download_uses_cache(self, client):
        # Pre-create cached file
        cached = os.path.join(client._cache_dir, "pexels_99.mp4")
        with open(cached, "wb") as f:
            f.write(b"cached")

        video_result = {
            "id": 99,
            "video_files": [{"link": "https://dl.pexels.com/99.mp4", "height": 1080}],
        }
        # Should NOT call session.get for download
        client._session.get = MagicMock(side_effect=AssertionError("should not download"))
        path = client.download_video(video_result)
        assert path == os.path.abspath(cached)

    def test_download_no_video_files_raises(self, client):
        with pytest.raises(StockFootageError, match="No video files"):
            client.download_video({"id": 1, "video_files": []})


class TestSelectBestFile:
    """Test PexelsClient._select_best_file."""

    def test_prefers_1080p(self):
        files = [
            {"height": 720, "link": "720.mp4"},
            {"height": 1080, "link": "1080.mp4"},
            {"height": 2160, "link": "4k.mp4"},
        ]
        best = PexelsClient._select_best_file(files)
        assert best["height"] == 1080

    def test_falls_back_to_largest(self):
        files = [
            {"height": 360, "link": "360.mp4"},
            {"height": 720, "link": "720.mp4"},
        ]
        best = PexelsClient._select_best_file(files)
        assert best["height"] == 720


class TestSearchAndDownload:
    """Test PexelsClient.search_and_download."""

    @pytest.fixture
    def client(self, tmp_path):
        return PexelsClient(api_key="test-key", cache_dir=str(tmp_path / "cache"))

    def test_returns_none_when_no_results(self, client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"videos": []}
        mock_resp.raise_for_status = MagicMock()
        client._session.get = MagicMock(return_value=mock_resp)

        result = client.search_and_download("nonexistent")
        assert result is None

    def test_returns_path_on_success(self, client):
        search_resp = MagicMock()
        search_resp.json.return_value = {
            "videos": [
                {
                    "id": 7,
                    "duration": 10,
                    "width": 1920,
                    "height": 1080,
                    "video_files": [{"link": "https://dl.pexels.com/7.mp4", "height": 1080}],
                }
            ]
        }
        search_resp.raise_for_status = MagicMock()

        dl_resp = MagicMock()
        dl_resp.iter_content = MagicMock(return_value=[b"video"])
        dl_resp.raise_for_status = MagicMock()

        client._session.get = MagicMock(side_effect=[search_resp, dl_resp])
        path = client.search_and_download("finance")
        assert path is not None
        assert path.endswith(".mp4")
