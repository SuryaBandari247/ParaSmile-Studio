"""
Unit tests for configuration management.

Tests configuration loading from YAML/JSON files, environment variable overrides,
validation, and default value handling.
"""

import pytest
import os
import json
import tempfile
from pathlib import Path

from research_agent.config import ConfigManager, ConfigValidationError
from research_agent.models import ResearchAgentConfig


class TestConfigManager:
    """Test suite for ConfigManager class."""
    
    def test_default_configuration_applied(self):
        """Test that default configuration is applied when no file provided."""
        manager = ConfigManager()
        
        # Set API key via environment for validation
        os.environ["YOUTUBE_API_KEY"] = "test_api_key_12345"
        
        try:
            config = manager.load_config()
            
            # Verify default values
            assert config.youtube_api_key == "test_api_key_12345"
            assert config.daily_quota_limit == 10000
            assert config.cache_ttl_hours == 6
            assert config.cache_file_path == ".cache/topics.json"
            assert config.min_trend_score == 30
            assert config.min_view_count == 1000
            assert config.search_days_back == 7
            assert config.max_videos_per_query == 50
            assert config.log_level == "INFO"
            assert config.structured_logging is False
            assert len(config.default_keywords) > 0
            assert "python tutorial" in config.default_keywords
        finally:
            del os.environ["YOUTUBE_API_KEY"]
    
    def test_yaml_configuration_file_parsing(self):
        """Test loading configuration from YAML file."""
        yaml_content = """
youtube_api_key: yaml_test_key
daily_quota_limit: 5000
cache_ttl_hours: 12
min_trend_score: 40
log_level: DEBUG
structured_logging: true
default_keywords:
  - rust programming
  - golang tutorial
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name
        
        try:
            manager = ConfigManager()
            config = manager.load_config(temp_path)
            
            assert config.youtube_api_key == "yaml_test_key"
            assert config.daily_quota_limit == 5000
            assert config.cache_ttl_hours == 12
            assert config.min_trend_score == 40
            assert config.log_level == "DEBUG"
            assert config.structured_logging is True
            assert "rust programming" in config.default_keywords
            assert "golang tutorial" in config.default_keywords
        finally:
            Path(temp_path).unlink()
    
    def test_json_configuration_file_parsing(self):
        """Test loading configuration from JSON file."""
        json_content = {
            "youtube_api_key": "json_test_key",
            "daily_quota_limit": 8000,
            "cache_ttl_hours": 3,
            "min_view_count": 5000,
            "log_level": "WARNING",
            "default_keywords": ["javascript", "typescript"]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(json_content, f)
            temp_path = f.name
        
        try:
            manager = ConfigManager()
            config = manager.load_config(temp_path)
            
            assert config.youtube_api_key == "json_test_key"
            assert config.daily_quota_limit == 8000
            assert config.cache_ttl_hours == 3
            assert config.min_view_count == 5000
            assert config.log_level == "WARNING"
            assert "javascript" in config.default_keywords
        finally:
            Path(temp_path).unlink()
    
    def test_environment_variable_overrides(self):
        """Test that environment variables override file configuration."""
        json_content = {
            "youtube_api_key": "file_key",
            "daily_quota_limit": 5000,
            "log_level": "INFO"
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(json_content, f)
            temp_path = f.name
        
        # Set environment variables
        os.environ["YOUTUBE_API_KEY"] = "env_override_key"
        os.environ["RESEARCH_AGENT_LOG_LEVEL"] = "DEBUG"
        os.environ["RESEARCH_AGENT_DAILY_QUOTA"] = "7500"
        
        try:
            manager = ConfigManager()
            config = manager.load_config(temp_path)
            
            # Environment variables should override file values
            assert config.youtube_api_key == "env_override_key"
            assert config.log_level == "DEBUG"
            assert config.daily_quota_limit == 7500
        finally:
            Path(temp_path).unlink()
            del os.environ["YOUTUBE_API_KEY"]
            del os.environ["RESEARCH_AGENT_LOG_LEVEL"]
            del os.environ["RESEARCH_AGENT_DAILY_QUOTA"]
    
    def test_invalid_configuration_raises_validation_error(self):
        """Test that invalid configuration raises ConfigValidationError."""
        json_content = {
            "youtube_api_key": "",  # Empty API key
            "daily_quota_limit": -100,  # Negative quota
            "min_trend_score": 150  # Out of range
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(json_content, f)
            temp_path = f.name
        
        try:
            manager = ConfigManager()
            with pytest.raises(ConfigValidationError) as exc_info:
                manager.load_config(temp_path)
            
            # Should contain multiple violations
            error_msg = str(exc_info.value)
            assert "youtube_api_key is required" in error_msg
            assert "daily_quota_limit must be positive" in error_msg
            assert "min_trend_score must be between 0 and 100" in error_msg
        finally:
            Path(temp_path).unlink()
    
    def test_missing_api_key_raises_validation_error(self):
        """Test that missing API key raises ConfigValidationError."""
        json_content = {
            "daily_quota_limit": 10000
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(json_content, f)
            temp_path = f.name
        
        try:
            manager = ConfigManager()
            with pytest.raises(ConfigValidationError, match="youtube_api_key is required"):
                manager.load_config(temp_path)
        finally:
            Path(temp_path).unlink()
    
    def test_invalid_log_level_raises_validation_error(self):
        """Test that invalid log level raises ConfigValidationError."""
        json_content = {
            "youtube_api_key": "test_key",
            "log_level": "INVALID_LEVEL"
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(json_content, f)
            temp_path = f.name
        
        try:
            manager = ConfigManager()
            with pytest.raises(ConfigValidationError, match="log_level must be one of"):
                manager.load_config(temp_path)
        finally:
            Path(temp_path).unlink()
    
    def test_file_not_found_raises_error(self):
        """Test that non-existent config file raises FileNotFoundError."""
        manager = ConfigManager()
        
        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            manager.load_config("/nonexistent/path/config.yaml")
    
    def test_unsupported_file_format_raises_error(self):
        """Test that unsupported file format raises ConfigValidationError."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("some content")
            temp_path = f.name
        
        try:
            manager = ConfigManager()
            with pytest.raises(ConfigValidationError, match="Unsupported configuration file format"):
                manager.load_config(temp_path)
        finally:
            Path(temp_path).unlink()
    
    def test_invalid_yaml_format_raises_error(self):
        """Test that invalid YAML format raises ConfigValidationError."""
        yaml_content = """
youtube_api_key: test_key
invalid_yaml: [unclosed bracket
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name
        
        try:
            manager = ConfigManager()
            with pytest.raises(ConfigValidationError, match="Invalid YAML format"):
                manager.load_config(temp_path)
        finally:
            Path(temp_path).unlink()
    
    def test_invalid_json_format_raises_error(self):
        """Test that invalid JSON format raises ConfigValidationError."""
        json_content = '{"youtube_api_key": "test_key", invalid json}'
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(json_content)
            temp_path = f.name
        
        try:
            manager = ConfigManager()
            with pytest.raises(ConfigValidationError, match="Invalid JSON format"):
                manager.load_config(temp_path)
        finally:
            Path(temp_path).unlink()
    
    def test_default_keywords_validation(self):
        """Test that default_keywords must be a list of strings."""
        json_content = {
            "youtube_api_key": "test_key",
            "default_keywords": "not a list"
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(json_content, f)
            temp_path = f.name
        
        try:
            manager = ConfigManager()
            with pytest.raises(ConfigValidationError, match="default_keywords must be a list"):
                manager.load_config(temp_path)
        finally:
            Path(temp_path).unlink()
    
    def test_structured_logging_boolean_validation(self):
        """Test that structured_logging must be a boolean."""
        json_content = {
            "youtube_api_key": "test_key",
            "structured_logging": "not a boolean"
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(json_content, f)
            temp_path = f.name
        
        try:
            manager = ConfigManager()
            with pytest.raises(ConfigValidationError, match="structured_logging must be a boolean"):
                manager.load_config(temp_path)
        finally:
            Path(temp_path).unlink()
    
    def test_config_property_returns_loaded_config(self):
        """Test that config property returns the loaded configuration."""
        manager = ConfigManager()
        
        # Before loading, config should be None
        assert manager.config is None
        
        # Set API key and load
        os.environ["YOUTUBE_API_KEY"] = "test_key"
        try:
            config = manager.load_config()
            
            # After loading, config property should return the same instance
            assert manager.config is config
            assert manager.config.youtube_api_key == "test_key"
        finally:
            del os.environ["YOUTUBE_API_KEY"]
    
    def test_environment_variable_cache_ttl_override(self):
        """Test RESEARCH_AGENT_CACHE_TTL environment variable override."""
        os.environ["YOUTUBE_API_KEY"] = "test_key"
        os.environ["RESEARCH_AGENT_CACHE_TTL"] = "24"
        
        try:
            manager = ConfigManager()
            config = manager.load_config()
            
            assert config.cache_ttl_hours == 24
        finally:
            del os.environ["YOUTUBE_API_KEY"]
            del os.environ["RESEARCH_AGENT_CACHE_TTL"]
    
    def test_environment_variable_structured_logging_override(self):
        """Test RESEARCH_AGENT_STRUCTURED_LOGGING environment variable override."""
        os.environ["YOUTUBE_API_KEY"] = "test_key"
        os.environ["RESEARCH_AGENT_STRUCTURED_LOGGING"] = "true"
        
        try:
            manager = ConfigManager()
            config = manager.load_config()
            
            assert config.structured_logging is True
        finally:
            del os.environ["YOUTUBE_API_KEY"]
            del os.environ["RESEARCH_AGENT_STRUCTURED_LOGGING"]
    
    def test_invalid_environment_quota_raises_error(self):
        """Test that invalid RESEARCH_AGENT_DAILY_QUOTA raises ConfigValidationError."""
        os.environ["YOUTUBE_API_KEY"] = "test_key"
        os.environ["RESEARCH_AGENT_DAILY_QUOTA"] = "not_a_number"
        
        try:
            manager = ConfigManager()
            with pytest.raises(ConfigValidationError, match="RESEARCH_AGENT_DAILY_QUOTA must be an integer"):
                manager.load_config()
        finally:
            del os.environ["YOUTUBE_API_KEY"]
            del os.environ["RESEARCH_AGENT_DAILY_QUOTA"]
