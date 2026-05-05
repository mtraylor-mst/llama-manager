import time
from utils.rate_limit import RateLimiter


class TestRateLimiter:
    def test_first_call_allowed(self):
        limiter = RateLimiter()
        allowed, retry_after = limiter.is_allowed("test_key", max_calls=1, period=60)
        assert allowed is True
        assert retry_after == 0

    def test_second_call_blocked(self):
        limiter = RateLimiter()
        limiter.is_allowed("test_key", max_calls=1, period=60)
        allowed, retry_after = limiter.is_allowed("test_key", max_calls=1, period=60)
        assert allowed is False
        assert retry_after > 0

    def test_different_keys_independent(self):
        limiter = RateLimiter()
        limiter.is_allowed("key_a", max_calls=1, period=60)
        allowed, _ = limiter.is_allowed("key_b", max_calls=1, period=60)
        assert allowed is True

    def test_multiple_calls_allowed(self):
        limiter = RateLimiter()
        for i in range(5):
            allowed, _ = limiter.is_allowed("test_key", max_calls=5, period=60)
            assert allowed is True

    def test_expires_after_period(self):
        limiter = RateLimiter()
        limiter.is_allowed("test_key", max_calls=1, period=1)
        time.sleep(1.1)
        allowed, _ = limiter.is_allowed("test_key", max_calls=1, period=1)
        assert allowed is True

    def test_retry_after_value(self):
        limiter = RateLimiter()
        limiter.is_allowed("test_key", max_calls=1, period=60)
        _, retry_after = limiter.is_allowed("test_key", max_calls=1, period=60)
        assert 59 <= retry_after <= 61
