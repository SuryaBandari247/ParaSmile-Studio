"""
Unit tests for APIRateLimiter edge cases.

Tests specific edge cases for quota thresholds and reset functionality.
"""

import pytest
import logging
from research_agent.rate_limiter import APIRateLimiter
from research_agent.exceptions import QuotaExceededError


def test_quota_at_exactly_80_percent_threshold_logs_warning(quota_state_file, caplog):
    """
    Test quota at exactly 80% threshold (warning logged).
    
    Requirements: 4.2
    
    When quota consumption reaches exactly 80% of daily limit,
    the rate limiter should log a warning with remaining quota.
    """
    # Set up rate limiter with 10,000 quota
    limiter = APIRateLimiter(daily_quota=10000, state_file=quota_state_file)
    
    # Set caplog to capture at DEBUG level to ensure we get everything
    with caplog.at_level(logging.DEBUG):
        # First consume 7900 units (no warning yet - 79%)
        limiter.consume_quota(7900)
        
        # Should not have warning yet (79%)
        warning_messages = [record.message for record in caplog.records if record.levelname == 'WARNING']
        assert len(warning_messages) == 0, "Should not warn before 80% threshold"
        
        # Now consume 100 more units to reach exactly 80% (8000 total)
        limiter.consume_quota(100)
        
        # Should have warning now (from the second consume_quota call)
        warning_messages = [record.message for record in caplog.records if record.levelname == 'WARNING']
        assert len(warning_messages) > 0, f"Should log warning at 80% threshold. Captured records: {[(r.levelname, r.message) for r in caplog.records]}"
        
        # Verify warning contains remaining quota information
        warning_text = ' '.join(warning_messages)
        assert 'Quota warning' in warning_text or 'quota consumed' in warning_text.lower()
        assert '2000' in warning_text or 'Remaining: 2000' in warning_text, "Should mention remaining quota"


def test_quota_at_exactly_95_percent_threshold_blocks_calls(quota_state_file):
    """
    Test quota at exactly 95% threshold (calls blocked).
    
    Requirements: 4.3
    
    When quota consumption reaches 95% of daily limit,
    the rate limiter should prevent new API calls until quota reset.
    """
    # Set up rate limiter with 10,000 quota
    limiter = APIRateLimiter(daily_quota=10000, state_file=quota_state_file)
    
    # Consume quota to reach exactly 95% (9500 units)
    # First consume 9400 units (just below threshold)
    limiter.consume_quota(9400)
    
    # Verify we can still check quota before hitting 95%
    assert limiter.check_quota(50) is True, "Should allow operations before 95% threshold"
    
    # Now consume 100 more units to reach exactly 95% (9500 total)
    # This should raise QuotaExceededError
    with pytest.raises(QuotaExceededError) as exc_info:
        limiter.consume_quota(100)
    
    # Verify the exception contains reset timestamp
    assert exc_info.value.reset_at is not None
    assert "quota exceeded" in str(exc_info.value).lower()
    
    # Verify that check_quota now returns False (circuit breaker activated)
    assert limiter.check_quota(1) is False, "Should block all calls after 95% threshold"
    assert limiter.check_quota(100) is False, "Should block all calls after 95% threshold"


def test_quota_reset_functionality(quota_state_file):
    """
    Test quota reset functionality.
    
    Requirements: 4.3
    
    The reset_quota method should reset the consumed quota to 0
    and allow new API calls to proceed.
    """
    # Set up rate limiter with 10,000 quota
    limiter = APIRateLimiter(daily_quota=10000, state_file=quota_state_file)
    
    # Consume significant quota (e.g., 9000 units)
    limiter.consume_quota(9000)
    
    # Verify quota is consumed
    assert limiter.consumed == 9000
    assert limiter.get_remaining_quota() == 1000
    
    # Reset quota
    limiter.reset_quota()
    
    # Verify quota is reset to 0
    assert limiter.consumed == 0, "Consumed quota should be reset to 0"
    assert limiter.get_remaining_quota() == 10000, "Remaining quota should be full"
    
    # Verify we can now make API calls again
    assert limiter.check_quota(100) is True, "Should allow operations after reset"
    
    # Verify we can consume quota after reset
    limiter.consume_quota(100)
    assert limiter.consumed == 100
    assert limiter.get_remaining_quota() == 9900


def test_quota_reset_after_circuit_breaker_activation(quota_state_file):
    """
    Test that quota reset clears circuit breaker state.
    
    Requirements: 4.3
    
    After hitting the 95% circuit breaker, resetting quota
    should allow new API calls to proceed.
    """
    # Set up rate limiter with 10,000 quota
    limiter = APIRateLimiter(daily_quota=10000, state_file=quota_state_file)
    
    # Consume quota to trigger circuit breaker (9500+ units)
    limiter.consume_quota(9400)
    
    # Trigger circuit breaker
    with pytest.raises(QuotaExceededError):
        limiter.consume_quota(100)
    
    # Verify circuit breaker is active
    assert limiter.check_quota(1) is False, "Circuit breaker should block calls"
    
    # Reset quota
    limiter.reset_quota()
    
    # Verify circuit breaker is cleared
    assert limiter.check_quota(100) is True, "Should allow calls after reset"
    assert limiter.consumed == 0, "Consumed quota should be 0 after reset"
    
    # Verify we can consume quota normally
    limiter.consume_quota(100)
    assert limiter.consumed == 100
