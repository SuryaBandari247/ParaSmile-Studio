"""
API Rate Limiter for YouTube Data API quota management.

This module implements quota tracking and circuit breaker pattern to prevent
API quota exhaustion. Quota state is persisted to disk to track consumption
across application restarts.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from research_agent.exceptions import QuotaExceededError


logger = logging.getLogger(__name__)


class APIRateLimiter:
    """
    Manages YouTube API quota consumption and rate limiting.
    Implements circuit breaker pattern for quota exhaustion.
    
    The YouTube Data API has a default quota of 10,000 units per day.
    Different operations have different costs:
    - search.list: 100 units
    - videos.list: 1 unit per video
    
    This rate limiter tracks consumption, logs warnings at 80% usage,
    and implements a circuit breaker at 95% to prevent quota exhaustion.
    """
    
    def __init__(self, daily_quota: int = 10000, state_file: Optional[str] = None):
        """
        Initialize rate limiter with daily quota.
        
        Args:
            daily_quota: Maximum API units per day (default: 10000)
            state_file: Path to quota state persistence file (default: .cache/quota_state.json)
        """
        self.daily_quota = daily_quota
        self.state_file = Path(state_file) if state_file else Path(".cache/quota_state.json")
        
        # Thresholds
        self.warning_threshold = 0.80  # 80%
        self.circuit_breaker_threshold = 0.95  # 95%
        
        # Load persisted state or initialize new state
        self._load_state()
        
        logger.info(
            f"APIRateLimiter initialized: daily_quota={self.daily_quota}, "
            f"consumed={self.consumed}, remaining={self.get_remaining_quota()}"
        )
    
    def _load_state(self) -> None:
        """Load quota state from disk or initialize new state."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                
                # Parse the reset timestamp
                reset_at = datetime.fromisoformat(state['reset_at'])
                
                # Check if quota should be reset (new day)
                if datetime.now(timezone.utc) >= reset_at:
                    logger.info("Quota period expired, resetting quota")
                    self._initialize_new_state()
                else:
                    # Load existing state
                    self.consumed = state['consumed']
                    self.reset_at = reset_at
                    self.last_updated = datetime.fromisoformat(state['last_updated'])
                    
                    logger.info(
                        f"Loaded quota state: consumed={self.consumed}, "
                        f"reset_at={self.reset_at.isoformat()}"
                    )
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.warning(f"Failed to load quota state: {e}. Initializing new state.")
                self._initialize_new_state()
        else:
            self._initialize_new_state()
    
    def _initialize_new_state(self) -> None:
        """Initialize a new quota state."""
        self.consumed = 0
        self.reset_at = self._calculate_next_reset()
        self.last_updated = datetime.now(timezone.utc)
        self._persist_state()
    
    def _calculate_next_reset(self) -> datetime:
        """
        Calculate the next quota reset time (midnight Pacific Time).
        
        YouTube API quota resets at midnight Pacific Time (PT).
        
        Returns:
            datetime: Next reset timestamp in UTC
        """
        # For simplicity, we'll reset 24 hours from now
        # In production, this should calculate midnight PT
        from datetime import timedelta
        return datetime.now(timezone.utc) + timedelta(days=1)
    
    def _persist_state(self) -> None:
        """Persist quota state to disk."""
        # Ensure cache directory exists
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        
        state = {
            'consumed': self.consumed,
            'reset_at': self.reset_at.isoformat(),
            'last_updated': self.last_updated.isoformat(),
            'daily_quota': self.daily_quota
        }
        
        # Atomic write: write to temp file then rename
        temp_file = self.state_file.with_suffix('.tmp')
        try:
            with open(temp_file, 'w') as f:
                json.dump(state, f, indent=2)
            temp_file.replace(self.state_file)
        except Exception as e:
            logger.error(f"Failed to persist quota state: {e}")
            if temp_file.exists():
                temp_file.unlink()
    
    def check_quota(self, cost: int) -> bool:
        """
        Check if sufficient quota available for operation.
        
        Args:
            cost: API units required for operation
            
        Returns:
            True if quota available, False otherwise
        """
        remaining = self.get_remaining_quota()
        
        # Check if we've hit the circuit breaker threshold
        usage_percentage = (self.consumed / self.daily_quota)
        if usage_percentage >= self.circuit_breaker_threshold:
            logger.error(
                f"Circuit breaker activated: quota usage at {usage_percentage:.1%}. "
                f"Blocking new API calls until reset at {self.reset_at.isoformat()}"
            )
            return False
        
        # Check if this operation would exceed quota
        if remaining < cost:
            logger.warning(
                f"Insufficient quota: need {cost} units, only {remaining} remaining"
            )
            return False
        
        return True
    
    def consume_quota(self, cost: int) -> None:
        """
        Consume quota for completed operation.
        
        Args:
            cost: API units consumed
            
        Raises:
            QuotaExceededError: If quota limit reached
        """
        if cost < 0:
            raise ValueError(f"Cost must be non-negative, got {cost}")
        
        # Update consumed quota
        self.consumed += cost
        self.last_updated = datetime.now(timezone.utc)
        
        # Persist state
        self._persist_state()
        
        # Calculate usage percentage
        usage_percentage = (self.consumed / self.daily_quota)
        remaining = self.get_remaining_quota()
        
        # Log quota consumption
        logger.debug(
            f"Consumed {cost} quota units. "
            f"Total: {self.consumed}/{self.daily_quota} ({usage_percentage:.1%}), "
            f"Remaining: {remaining}"
        )
        
        # Check warning threshold (80%)
        if usage_percentage >= self.warning_threshold and usage_percentage < self.circuit_breaker_threshold:
            logger.warning(
                f"Quota warning: {usage_percentage:.1%} of daily quota consumed. "
                f"Remaining: {remaining} units. Reset at {self.reset_at.isoformat()}"
            )
        
        # Check circuit breaker threshold (95%)
        if usage_percentage >= self.circuit_breaker_threshold:
            logger.error(
                f"Quota circuit breaker activated: {usage_percentage:.1%} consumed. "
                f"Blocking new API calls until reset at {self.reset_at.isoformat()}"
            )
            raise QuotaExceededError(self.reset_at)
    
    def get_remaining_quota(self) -> int:
        """
        Get remaining quota units for current day.
        
        Returns:
            Remaining API units
        """
        return max(0, self.daily_quota - self.consumed)
    
    def reset_quota(self) -> None:
        """
        Reset quota counter (called at midnight Pacific Time).
        
        This method can be called manually for testing or will be
        automatically triggered when loading state after reset time.
        """
        logger.info(
            f"Resetting quota. Previous consumption: {self.consumed}/{self.daily_quota}"
        )
        self._initialize_new_state()
    
    def get_usage_percentage(self) -> float:
        """
        Calculate quota usage as percentage.
        
        Returns:
            Usage percentage (0.0 to 1.0)
        """
        return (self.consumed / self.daily_quota) if self.daily_quota > 0 else 0.0
