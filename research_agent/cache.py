"""
Topic cache module for storing and retrieving trending topic data.

This module implements TTL-based caching to reduce YouTube API calls.
Uses atomic file writes to prevent corruption and handles JSON decode errors gracefully.
"""

import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from research_agent.exceptions import CacheCorruptionError


class TopicCache:
    """
    Manages caching of trending topic data to reduce API calls.
    Implements TTL-based invalidation and atomic writes.
    
    The cache stores data in JSON format with timestamps. Data is considered
    fresh if it's less than the TTL (time-to-live) old. Atomic writes prevent
    corruption during concurrent access or system failures.
    """
    
    def __init__(self, cache_file: str = ".cache/topics.json", ttl_hours: int = 6):
        """
        Initialize topic cache.
        
        Args:
            cache_file: Path to cache file (default: .cache/topics.json)
            ttl_hours: Time-to-live for cached data in hours (default: 6)
        """
        self.cache_file = Path(cache_file)
        self.ttl_hours = ttl_hours
        self.ttl_delta = timedelta(hours=ttl_hours)
        
        # Ensure cache directory exists
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize cache structure if file doesn't exist
        if not self.cache_file.exists():
            self._write_cache({})
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached topic data if fresh.
        
        Args:
            key: Cache key (e.g., query parameters hash)
            
        Returns:
            Cached data if fresh (< TTL), None otherwise
        """
        try:
            cache_data = self._read_cache()
            
            if key not in cache_data:
                return None
            
            entry = cache_data[key]
            
            # Check if entry has required fields
            if "timestamp" not in entry or "data" not in entry:
                return None
            
            # Parse timestamp and check freshness
            timestamp = datetime.fromisoformat(entry["timestamp"])
            age = datetime.now() - timestamp
            
            if age < self.ttl_delta:
                return entry["data"]
            
            # Data is stale
            return None
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            # Cache is corrupted, delete and return None
            self._handle_corruption(e)
            return None
    
    def set(self, key: str, data: Dict[str, Any]) -> None:
        """
        Store topic data in cache with timestamp.
        
        Args:
            key: Cache key
            data: Topic data to cache
        """
        try:
            cache_data = self._read_cache()
        except (json.JSONDecodeError, ValueError):
            # If cache is corrupted, start fresh
            cache_data = {}
        
        # Store data with current timestamp
        cache_data[key] = {
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        
        self._write_cache(cache_data)
    
    def invalidate(self, key: str) -> None:
        """
        Remove specific entry from cache.
        
        Args:
            key: Cache key to invalidate
        """
        try:
            cache_data = self._read_cache()
            
            if key in cache_data:
                del cache_data[key]
                self._write_cache(cache_data)
                
        except (json.JSONDecodeError, ValueError):
            # If cache is corrupted, clear it
            self.clear()
    
    def clear(self) -> None:
        """
        Clear entire cache (used when corruption detected).
        """
        self._write_cache({})
    
    def _read_cache(self) -> Dict[str, Any]:
        """
        Read cache data from file.
        
        Returns:
            Cache data dictionary
            
        Raises:
            json.JSONDecodeError: If cache file is corrupted
        """
        if not self.cache_file.exists():
            return {}
        
        with open(self.cache_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _write_cache(self, data: Dict[str, Any]) -> None:
        """
        Write cache data to file using atomic write.
        
        Atomic write prevents corruption by writing to a temporary file
        first, then renaming it to the target file. This ensures the
        cache file is never in a partially written state.
        
        Args:
            data: Cache data to write
        """
        # Write to temporary file in the same directory
        temp_fd, temp_path = tempfile.mkstemp(
            dir=self.cache_file.parent,
            prefix='.tmp_cache_',
            suffix='.json'
        )
        
        try:
            with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Atomic rename (on POSIX systems, this is atomic)
            os.replace(temp_path, self.cache_file)
            
        except Exception:
            # Clean up temp file if something goes wrong
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise
    
    def _handle_corruption(self, error: Exception) -> None:
        """
        Handle cache corruption by deleting the cache file.
        
        Args:
            error: The exception that indicated corruption
        """
        try:
            if self.cache_file.exists():
                self.cache_file.unlink()
            # Recreate empty cache
            self._write_cache({})
        except OSError:
            # If we can't delete the file, just continue
            pass
