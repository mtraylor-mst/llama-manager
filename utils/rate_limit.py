import time
from functools import wraps
from flask import jsonify


class RateLimiter:
    """Simple in-memory rate limiter."""

    def __init__(self):
        self._calls = {}  # key -> list of timestamps

    def is_allowed(self, key, max_calls=1, period=60):
        """Check if a call is allowed. Returns (allowed, retry_after_seconds)."""
        now = time.time()
        window_start = now - period

        if key not in self._calls:
            self._calls[key] = []

        # Remove expired entries
        self._calls[key] = [t for t in self._calls[key] if t > window_start]

        if len(self._calls[key]) >= max_calls:
            retry_after = self._calls[key][0] - window_start
            return False, retry_after

        self._calls[key].append(now)
        return True, 0


_limiter = RateLimiter()


def rate_limit(key_func=None, max_calls=1, period=60):
    """Decorator that rate-limits a route.

    Args:
        key_func: Callable(request) -> str. Defaults to request.path.
        max_calls: Maximum calls allowed within the period.
        period: Time window in seconds.
    """
    if key_func is None:

        def key_func(req):
            return req.path

    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            from flask import request

            key = f"{request.method}:{key_func(request)}"
            allowed, retry_after = _limiter.is_allowed(key, max_calls, period)

            if not allowed:
                is_htmx = request.headers.get("HX-Request")
                msg = f"Too frequent. Try again in {retry_after:.0f}s."
                if is_htmx:
                    return f'<div class="alert alert-warning">{msg}</div>', 429
                if request.accept_mimetypes.best.startswith("application/json"):
                    return jsonify({"error": msg}), 429
                from flask import flash, redirect, url_for

                flash(msg, "warning")
                return redirect(request.referrer or url_for("index"))

            return f(*args, **kwargs)

        return wrapped

    return decorator
