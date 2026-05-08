import time
from utils.rate_limit import RateLimiter, rate_limit, _limiter


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


class TestRateLimitDecorator:
    def _make_app(self):
        from flask import Flask

        app = Flask(__name__)
        app.config["TESTING"] = True
        app.config["SECRET_KEY"] = "test"

        @app.route("/")
        def index():
            return "Index"

        @app.route("/test")
        @rate_limit(max_calls=1, period=60)
        def test_route():
            return "OK"

        @app.route("/json", methods=["GET"])
        @rate_limit(max_calls=1, period=60)
        def json_route():
            from flask import jsonify

            return jsonify({"status": "ok"})

        return app

    def test_htmx_response(self):
        app = self._make_app()
        client = app.test_client()

        # Reset limiter state
        _limiter._calls.clear()

        client.get("/test", headers={"HX-Request": "True"})
        resp = client.get("/test", headers={"HX-Request": "True"})
        assert resp.status_code == 429
        assert b"alert-warning" in resp.data
        assert b"Too frequent" in resp.data

    def test_json_response(self):
        app = self._make_app()
        client = app.test_client()

        _limiter._calls.clear()

        client.get("/json", headers={"Accept": "application/json"})
        resp = client.get("/json", headers={"Accept": "application/json"})
        assert resp.status_code == 429
        assert resp.content_type.startswith("application/json")
        data = resp.get_json()
        assert "error" in data
        assert "Too frequent" in data["error"]

    def test_redirect_fallback(self):
        app = self._make_app()
        client = app.test_client()

        _limiter._calls.clear()

        client.get("/test")
        resp = client.get("/test", follow_redirects=False)
        assert resp.status_code == 302

    def test_custom_key_func(self):
        from flask import Flask

        app = Flask(__name__)
        app.config["TESTING"] = True
        app.config["SECRET_KEY"] = "test"

        @app.route("/")
        def index():
            return "Index"

        @app.route("/a")
        @app.route("/b")
        @rate_limit(key_func=lambda req: "shared", max_calls=1, period=60)
        def shared_route():
            return "OK"

        client = app.test_client()
        _limiter._calls.clear()

        resp_a = client.get("/a")
        assert resp_a.status_code == 200

        resp_b = client.get("/b", follow_redirects=False)
        assert resp_b.status_code == 302  # Rate limited
