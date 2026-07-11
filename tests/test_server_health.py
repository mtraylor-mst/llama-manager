"""Tests for services/server_health.py."""

import json
from unittest.mock import patch, MagicMock


class TestGetServerUrl:
    def test_default_url(self):
        from services.server_health import get_server_url

        url = get_server_url()
        assert url == "http://127.0.0.1:8080"

    @patch("models.configs.get_all_version_data")
    def test_url_from_version_id(self, mock_data):
        from services.server_health import get_server_url

        mock_data.return_value = {
            "server": {"host": "0.0.0.0", "port": 9000},
        }
        url = get_server_url(version_id=42)
        assert url == "http://0.0.0.0:9000"

    def test_url_from_version_data(self):
        from services.server_health import get_server_url

        url = get_server_url(version_data={
            "server": {"host": "192.168.1.1", "port": 7800},
        })
        assert url == "http://192.168.1.1:7800"

    def test_url_fallback_defaults(self):
        from services.server_health import get_server_url

        url = get_server_url(version_data={"server": {}})
        assert url == "http://127.0.0.1:8080"


class TestCheckHealthHealthy:
    def test_healthy_response(self):
        from services.server_health import check_health

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"status": "ok"}).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = lambda s, *a: None

        with patch("services.server_health.urllib.request.urlopen", return_value=mock_resp):
            result = check_health(version_data={"server": {"host": "127.0.0.1", "port": 8080}})

        assert result["healthy"] is True
        assert result["status"] == "ok"
        assert result["error"] is None
        assert result["response_time_ms"] >= 0


class TestCheckHealthConnectionRefused:
    def test_connection_refused(self):
        from services.server_health import check_health
        import urllib.error
        import socket

        with patch("services.server_health.urllib.request.urlopen") as mock_open:
            mock_open.side_effect = urllib.error.URLError(
                socket.error("Connection refused")
            )
            result = check_health(version_data={"server": {"host": "127.0.0.1", "port": 8080}})

        assert result["healthy"] is False
        assert result["status"] is None
        assert result["error"] is not None
        assert "Connection failed" in result["error"]


class TestCheckHealthTimeout:
    def test_timeout(self):
        from services.server_health import check_health
        import socket

        with patch("services.server_health.urllib.request.urlopen") as mock_open:
            mock_open.side_effect = socket.timeout()
            result = check_health(version_data={"server": {"host": "127.0.0.1", "port": 8080}})

        assert result["healthy"] is False
        assert result["error"] is not None


class TestCheckHealthBadResponse:
    def test_invalid_json(self):
        from services.server_health import check_health

        mock_resp = MagicMock()
        mock_resp.read.return_value = b"not json"
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = lambda s, *a: None

        with patch("services.server_health.urllib.request.urlopen", return_value=mock_resp):
            result = check_health(version_data={"server": {"host": "127.0.0.1", "port": 8080}})

        assert result["healthy"] is False
        assert result["error"] is not None


class TestCheckHealthViaVersionId:
    @patch("models.configs.get_all_version_data")
    def test_fetches_data_from_db(self, mock_data):
        from services.server_health import check_health

        mock_data.return_value = {
            "server": {"host": "0.0.0.0", "port": 9000},
        }

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"status": "ok"}).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = lambda s, *a: None

        with patch("services.server_health.urllib.request.urlopen", return_value=mock_resp):
            result = check_health(version_id=42)

        assert result["healthy"] is True
        mock_data.assert_called_once_with(42)


class TestCheckHealthResponseTime:
    def test_response_time_calculated(self):
        from services.server_health import check_health

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"status": "ok"}).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = lambda s, *a: None

        with patch("services.server_health.urllib.request.urlopen", return_value=mock_resp):
            with patch("services.server_health.time.monotonic") as mock_time:
                mock_time.side_effect = [0.0, 0.025]
                result = check_health(version_data={"server": {"host": "127.0.0.1", "port": 8080}})

        assert result["response_time_ms"] == 25


class TestHealthEndpoint:
    def test_health_no_server_running(self, client):
        with patch("services.screen_manager.get_running_version_id") as mock_vid:
            mock_vid.return_value = None
            resp = client.get("/server/health")
            data = resp.get_json()
            assert data["healthy"] is False
            assert "No server running" in data["error"]

    def test_health_server_healthy(self, client):
        with patch("services.screen_manager.get_running_version_id") as mock_vid:
            mock_vid.return_value = 1
            with patch("services.server_health.check_health") as mock_check:
                mock_check.return_value = {
                    "healthy": True,
                    "response_time_ms": 5,
                    "status": "ok",
                    "error": None,
                }
                resp = client.get("/server/health")
                data = resp.get_json()
                assert data["healthy"] is True
                assert data["response_time_ms"] == 5

    def test_health_server_unresponsive(self, client):
        with patch("services.screen_manager.get_running_version_id") as mock_vid:
            mock_vid.return_value = 1
            with patch("services.server_health.check_health") as mock_check:
                mock_check.return_value = {
                    "healthy": False,
                    "response_time_ms": 1000,
                    "status": None,
                    "error": "Connection failed",
                }
                resp = client.get("/server/health")
                data = resp.get_json()
                assert data["healthy"] is False
                assert data["error"] == "Connection failed"


class TestStatusEndpointIncludesHealth:
    def test_status_json_includes_health(self, client):
        with patch("services.screen_manager.get_status") as mock_st:
            mock_st.return_value = {"running": True, "state": "running", "name": "PID 1234", "line": ""}
            with patch("services.screen_manager.get_running_version_id") as mock_vid:
                mock_vid.return_value = 1
                with patch("services.server_health.check_health") as mock_check:
                    mock_check.return_value = {
                        "healthy": True,
                        "response_time_ms": 3,
                        "status": "ok",
                        "error": None,
                    }
                    with patch("models.configs.get_version") as mock_ver:
                        mock_ver.return_value = {"id": 1, "version_number": 2, "config_name": "Test"}
                        resp = client.get("/server/status")
                        data = resp.get_json()
                        assert "health" in data
                        assert data["health"]["healthy"] is True

    def test_status_htmx_includes_health_badge(self, client):
        with patch("services.screen_manager.get_status") as mock_st:
            mock_st.return_value = {"running": True, "state": "running", "name": "PID 1234", "line": ""}
            with patch("services.screen_manager.get_running_version_id") as mock_vid:
                mock_vid.return_value = 1
                with patch("services.server_health.check_health") as mock_check:
                    mock_check.return_value = {
                        "healthy": True,
                        "response_time_ms": 12,
                        "status": "ok",
                        "error": None,
                    }
                    with patch("models.configs.get_version") as mock_ver:
                        mock_ver.return_value = {"id": 1, "version_number": 2, "config_name": "Test"}
                        resp = client.get("/server/status", headers={"HX-Request": "true"})
                        assert b"health-ok" in resp.data
                        assert b"(12ms)" in resp.data

    def test_status_htmx_unresponsive_badge(self, client):
        with patch("services.screen_manager.get_status") as mock_st:
            mock_st.return_value = {"running": True, "state": "running", "name": "PID 1234", "line": ""}
            with patch("services.screen_manager.get_running_version_id") as mock_vid:
                mock_vid.return_value = 1
                with patch("services.server_health.check_health") as mock_check:
                    mock_check.return_value = {
                        "healthy": False,
                        "response_time_ms": 1000,
                        "status": None,
                        "error": "Connection failed",
                    }
                    with patch("models.configs.get_version") as mock_ver:
                        mock_ver.return_value = {"id": 1, "version_number": 2, "config_name": "Test"}
                        resp = client.get("/server/status", headers={"HX-Request": "true"})
                        assert b"health-fail" in resp.data
                        assert b"Unresponsive" in resp.data


class TestContextProcessor:
    def test_includes_health_when_running(self, client):
        with patch("services.screen_manager.get_status") as mock_st:
            mock_st.return_value = {"running": True, "state": "running", "name": "PID 1234", "line": ""}
            with patch("services.screen_manager.get_running_version_id") as mock_vid:
                mock_vid.return_value = 1
                with patch("services.server_health.check_health") as mock_check:
                    mock_check.return_value = {
                        "healthy": True,
                        "response_time_ms": 7,
                        "status": "ok",
                        "error": None,
                    }
                    with patch("models.configs.get_version") as mock_ver:
                        mock_ver.return_value = {"id": 1, "version_number": 2, "config_name": "Test"}
                        with patch("models.configs.get_all_configs") as mock_configs:
                            mock_configs.return_value = []
                            resp = client.get("/")
                            assert b"health-ok" in resp.data
                            assert b"(7ms)" in resp.data

    def test_no_health_when_stopped(self, client):
        with patch("services.screen_manager.get_status") as mock_st:
            mock_st.return_value = {"running": False, "state": "stopped", "name": None, "line": ""}
            with patch("services.screen_manager.get_running_version_id") as mock_vid:
                mock_vid.return_value = None
                with patch("models.configs.get_all_configs") as mock_configs:
                    mock_configs.return_value = []
                    resp = client.get("/")
                    assert b"health-ok" not in resp.data
                    assert b"health-fail" not in resp.data
