"""
Configuration management for the Research Agent.

This module provides the ConfigManager class for loading, validating, and managing
configuration from YAML/JSON files with environment variable overrides.
"""

import os
import json
import yaml
from typing import Dict, Any, Optional
from pathlib import Path

from research_agent.models import ResearchAgentConfig
from research_agent.exceptions import ResearchAgentError


class ConfigValidationError(ResearchAgentError):
    """Raised when configuration validation fails."""
    pass


class ConfigManager:
    """
    Manages configuration loading, validation, and environment variable overrides.
    
    Supports loading configuration from YAML or JSON files, with fallback to
    default values. Sensitive values (like API keys) can be overridden via
    environment variables.
    """
    
    def __init__(self):
        """Initialize the configuration manager."""
        self._config: Optional[ResearchAgentConfig] = None
    
    def load_config(self, file_path: Optional[str] = None) -> ResearchAgentConfig:
        """
        Load configuration from file or use defaults.
        
        Configuration priority (highest to lowest):
        1. Environment variables (for sensitive values)
        2. Configuration file (YAML/JSON)
        3. Default values from ResearchAgentConfig
        
        Args:
            file_path: Path to YAML or JSON configuration file.
                      If None, uses default configuration.
        
        Returns:
            ResearchAgentConfig instance with loaded configuration
        
        Raises:
            ConfigValidationError: If configuration is invalid
            FileNotFoundError: If specified config file doesn't exist
        """
        # Start with default configuration
        config_dict = self._get_default_config()
        
        # Load from file if provided
        if file_path:
            file_config = self._load_from_file(file_path)
            config_dict.update(file_config)
        
        # Apply environment variable overrides
        config_dict = self._apply_env_overrides(config_dict)
        
        # Validate configuration
        self._validate_config(config_dict)
        
        # Create ResearchAgentConfig instance
        self._config = ResearchAgentConfig(**config_dict)
        
        return self._config
    
    def load_from_dict(self, config_dict: Dict[str, Any]) -> ResearchAgentConfig:
        """
        Load configuration from a dictionary.
        
        Args:
            config_dict: Configuration dictionary
        
        Returns:
            ResearchAgentConfig instance with loaded configuration
        
        Raises:
            ConfigValidationError: If configuration is invalid
        """
        # Start with default configuration
        full_config = self._get_default_config()
        
        # Update with provided values
        full_config.update(config_dict)
        
        # Apply environment variable overrides
        full_config = self._apply_env_overrides(full_config)
        
        # Validate configuration
        self._validate_config(full_config)
        
        # Create ResearchAgentConfig instance
        self._config = ResearchAgentConfig(**full_config)
        
        return self._config
    
    def _get_default_config(self) -> Dict[str, Any]:
        """
        Get default configuration values.
        
        Returns:
            Dictionary with default configuration values
        """
        # Create a default instance to extract values
        default_config = ResearchAgentConfig(youtube_api_key="")
        
        return {
            "youtube_api_key": default_config.youtube_api_key,
            "daily_quota_limit": default_config.daily_quota_limit,
            "cache_ttl_hours": default_config.cache_ttl_hours,
            "cache_file_path": default_config.cache_file_path,
            "default_keywords": default_config.default_keywords.copy(),
            "min_trend_score": default_config.min_trend_score,
            "min_view_count": default_config.min_view_count,
            "search_days_back": default_config.search_days_back,
            "max_videos_per_query": default_config.max_videos_per_query,
            "log_level": default_config.log_level,
            "structured_logging": default_config.structured_logging,
            # Macro mode configuration
            "macro_mode_enabled": default_config.macro_mode_enabled,
            "authority_channels": default_config.authority_channels.copy(),
            "max_videos_per_authority_channel": default_config.max_videos_per_authority_channel,
            "topic_similarity_threshold": default_config.topic_similarity_threshold,
            "macro_bonus_multiplier": default_config.macro_bonus_multiplier,
            # Multi-source configuration
            "google_trends_geo": default_config.google_trends_geo,
            "reddit_subreddits": default_config.reddit_subreddits.copy(),
            "reddit_posts_per_sub": default_config.reddit_posts_per_sub,
            "reddit_rate_limit_seconds": default_config.reddit_rate_limit_seconds,
            "yahoo_finance_story_trigger_pct": default_config.yahoo_finance_story_trigger_pct,
            "dedup_similarity_threshold": default_config.dedup_similarity_threshold,
            "high_confidence_min_sources": default_config.high_confidence_min_sources,
            "openai_api_key": default_config.openai_api_key,
            "pitch_count": default_config.pitch_count,
        }
    
    def _load_from_file(self, file_path: str) -> Dict[str, Any]:
        """
        Load configuration from YAML or JSON file.
        
        Args:
            file_path: Path to configuration file
        
        Returns:
            Dictionary with configuration values from file
        
        Raises:
            FileNotFoundError: If file doesn't exist
            ConfigValidationError: If file format is invalid
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        
        try:
            with open(path, 'r') as f:
                content = f.read()
                
                # Determine file format by extension
                if path.suffix.lower() in ['.yaml', '.yml']:
                    config = yaml.safe_load(content)
                elif path.suffix.lower() == '.json':
                    config = json.loads(content)
                else:
                    raise ConfigValidationError(
                        f"Unsupported configuration file format: {path.suffix}. "
                        "Use .yaml, .yml, or .json"
                    )
                
                if not isinstance(config, dict):
                    raise ConfigValidationError(
                        "Configuration file must contain a dictionary/object"
                    )
                
                return config
                
        except yaml.YAMLError as e:
            raise ConfigValidationError(f"Invalid YAML format: {e}")
        except json.JSONDecodeError as e:
            raise ConfigValidationError(f"Invalid JSON format: {e}")
        except Exception as e:
            raise ConfigValidationError(f"Error reading configuration file: {e}")
    
    def _apply_env_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply environment variable overrides to configuration.
        
        Environment variables take precedence over file configuration.
        Supported environment variables:
        - YOUTUBE_API_KEY: YouTube Data API key
        - RESEARCH_AGENT_LOG_LEVEL: Logging level
        - RESEARCH_AGENT_DAILY_QUOTA: Daily quota limit
        - RESEARCH_AGENT_CACHE_TTL: Cache TTL in hours
        
        Args:
            config: Configuration dictionary
        
        Returns:
            Updated configuration dictionary with environment overrides
        """
        # YouTube API key (most important - always check environment)
        if os.getenv("YOUTUBE_API_KEY"):
            config["youtube_api_key"] = os.getenv("YOUTUBE_API_KEY")
        
        # Log level
        if os.getenv("RESEARCH_AGENT_LOG_LEVEL"):
            config["log_level"] = os.getenv("RESEARCH_AGENT_LOG_LEVEL")
        
        # Daily quota limit
        if os.getenv("RESEARCH_AGENT_DAILY_QUOTA"):
            try:
                config["daily_quota_limit"] = int(os.getenv("RESEARCH_AGENT_DAILY_QUOTA"))
            except ValueError:
                raise ConfigValidationError(
                    "RESEARCH_AGENT_DAILY_QUOTA must be an integer"
                )
        
        # Cache TTL
        if os.getenv("RESEARCH_AGENT_CACHE_TTL"):
            try:
                config["cache_ttl_hours"] = int(os.getenv("RESEARCH_AGENT_CACHE_TTL"))
            except ValueError:
                raise ConfigValidationError(
                    "RESEARCH_AGENT_CACHE_TTL must be an integer"
                )
        
        # Structured logging
        if os.getenv("RESEARCH_AGENT_STRUCTURED_LOGGING"):
            config["structured_logging"] = os.getenv(
                "RESEARCH_AGENT_STRUCTURED_LOGGING"
            ).lower() in ["true", "1", "yes"]
        
        # OpenAI API key for pitch generation
        if os.getenv("OPENAI_API_KEY"):
            config["openai_api_key"] = os.getenv("OPENAI_API_KEY")
        
        return config
    
    def _validate_config(self, config: Dict[str, Any]) -> None:
        """
        Validate configuration schema and values.
        
        Args:
            config: Configuration dictionary to validate
        
        Raises:
            ConfigValidationError: If configuration is invalid
        """
        violations = []
        
        # Required fields
        if not config.get("youtube_api_key"):
            violations.append("youtube_api_key is required")
        
        # Validate numeric ranges
        if config.get("daily_quota_limit", 0) <= 0:
            violations.append("daily_quota_limit must be positive")
        
        if config.get("cache_ttl_hours", 0) <= 0:
            violations.append("cache_ttl_hours must be positive")
        
        if not (0 <= config.get("min_trend_score", 30) <= 100):
            violations.append("min_trend_score must be between 0 and 100")
        
        if config.get("min_view_count", 0) < 0:
            violations.append("min_view_count must be non-negative")
        
        if config.get("search_days_back", 0) <= 0:
            violations.append("search_days_back must be positive")
        
        if config.get("max_videos_per_query", 0) <= 0:
            violations.append("max_videos_per_query must be positive")
        
        # Validate log level
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if config.get("log_level", "INFO").upper() not in valid_log_levels:
            violations.append(
                f"log_level must be one of: {', '.join(valid_log_levels)}"
            )
        
        # Validate default_keywords is a list
        if "default_keywords" in config:
            if not isinstance(config["default_keywords"], list):
                violations.append("default_keywords must be a list")
            elif not all(isinstance(k, str) for k in config["default_keywords"]):
                violations.append("default_keywords must contain only strings")
        
        # Validate structured_logging is boolean
        if "structured_logging" in config:
            if not isinstance(config["structured_logging"], bool):
                violations.append("structured_logging must be a boolean")
        
        # Validate multi-source configuration fields
        if "reddit_subreddits" in config:
            if not isinstance(config["reddit_subreddits"], list):
                violations.append("reddit_subreddits must be a list")
            elif not all(isinstance(s, str) for s in config["reddit_subreddits"]):
                violations.append("reddit_subreddits must contain only strings")
        
        if "reddit_posts_per_sub" in config:
            if not isinstance(config["reddit_posts_per_sub"], (int, float)) or config["reddit_posts_per_sub"] <= 0:
                violations.append("reddit_posts_per_sub must be a positive number")
        
        if "reddit_rate_limit_seconds" in config:
            if not isinstance(config["reddit_rate_limit_seconds"], (int, float)) or config["reddit_rate_limit_seconds"] < 0:
                violations.append("reddit_rate_limit_seconds must be non-negative")
        
        if "yahoo_finance_story_trigger_pct" in config:
            if not isinstance(config["yahoo_finance_story_trigger_pct"], (int, float)) or config["yahoo_finance_story_trigger_pct"] <= 0:
                violations.append("yahoo_finance_story_trigger_pct must be positive")
        
        if "dedup_similarity_threshold" in config:
            val = config["dedup_similarity_threshold"]
            if not isinstance(val, (int, float)) or not (0 <= val <= 1):
                violations.append("dedup_similarity_threshold must be between 0 and 1")
        
        if "high_confidence_min_sources" in config:
            if not isinstance(config["high_confidence_min_sources"], int) or config["high_confidence_min_sources"] <= 0:
                violations.append("high_confidence_min_sources must be a positive integer")
        
        if "pitch_count" in config:
            if not isinstance(config["pitch_count"], int) or config["pitch_count"] <= 0:
                violations.append("pitch_count must be a positive integer")
        
        if violations:
            raise ConfigValidationError(
                f"Configuration validation failed: {'; '.join(violations)}"
            )
    
    @property
    def config(self) -> Optional[ResearchAgentConfig]:
        """
        Get the current configuration.
        
        Returns:
            Current ResearchAgentConfig instance or None if not loaded
        """
        return self._config
