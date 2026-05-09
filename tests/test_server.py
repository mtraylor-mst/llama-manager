from unittest.mock import patch


class TestStatus:
    @patch("services.screen_manager.get_status")
    def test_status_json(self, mock_status, client):
        mock_status.return_value = {
            "running": False,
            "state": "stopped",
            "name": None,
            "line": "",
        }
        resp = client.get("/server/status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["running"] is False

    @patch("services.screen_manager.get_status")
    def test_status_htmx_stopped(self, mock_status, client):
        mock_status.return_value = {
            "running": False,
            "state": "stopped",
            "name": None,
            "line": "",
        }
        resp = client.get("/server/status", headers={"HX-Request": "true"})
        assert resp.status_code == 200
        assert b"Stopped" in resp.data

    @patch("services.screen_manager.get_running_version_id")
    @patch("services.screen_manager.get_status")
    def test_status_htmx_running(self, mock_status, mock_running, client):
        mock_status.return_value = {
            "running": True,
            "state": "running",
            "name": "test",
            "line": "llama-server",
        }
        mock_running.return_value = 1
        with patch("models.configs.get_version") as mock_ver:
            mock_ver.return_value = {
                "id": 1,
                "version_number": 1,
                "config_name": "Test",
            }
            resp = client.get("/server/status", headers={"HX-Request": "true"})
            assert resp.status_code == 200
            assert b"Running" in resp.data


class TestStop:
    @patch("utils.rate_limit._limiter.is_allowed", return_value=(True, 0))
    @patch("services.screen_manager.stop")
    def test_stop_success_htmx(self, mock_stop, mock_rate, client):
        mock_stop.return_value = {"success": True, "message": "Server stopped"}
        resp = client.post("/server/stop", headers={"HX-Request": "true"})
        assert resp.status_code == 200
        assert b"Server stopped" in resp.data

    @patch("utils.rate_limit._limiter.is_allowed", return_value=(True, 0))
    @patch("services.screen_manager.stop")
    def test_stop_failure_htmx(self, mock_stop, mock_rate, client):
        mock_stop.return_value = {"success": False, "message": "Not running"}
        resp = client.post("/server/stop", headers={"HX-Request": "true"})
        assert resp.status_code == 200
        assert b"Not running" in resp.data

    @patch("utils.rate_limit._limiter.is_allowed", return_value=(True, 0))
    @patch("services.screen_manager.stop")
    def test_stop_success_redirect(self, mock_stop, mock_rate, client):
        mock_stop.return_value = {"success": True, "message": "Server stopped"}
        resp = client.post("/server/stop", follow_redirects=False)
        assert resp.status_code == 302

    @patch("utils.rate_limit._limiter.is_allowed", return_value=(True, 0))
    @patch("services.screen_manager.stop")
    def test_stop_failure_redirect(self, mock_stop, mock_rate, client):
        mock_stop.return_value = {"success": False, "message": "Not running"}
        resp = client.post("/server/stop", follow_redirects=False)
        assert resp.status_code == 302


class TestStart:
    @patch("utils.rate_limit._limiter.is_allowed", return_value=(True, 0))
    @patch("services.screen_manager.start")
    @patch("services.command_builder.build_command")
    def test_start_success_htmx(self, mock_build, mock_start, mock_rate, client):
        mock_build.return_value = ["llama-server", "-m", "model.bin"]
        mock_start.return_value = {"success": True, "message": "Server started"}
        resp = client.post("/server/start/1", headers={"HX-Request": "true"})
        assert resp.status_code == 200
        assert b"Server started" in resp.data
        mock_build.assert_called_once_with(1)
        mock_start.assert_called_once()

    @patch("utils.rate_limit._limiter.is_allowed", return_value=(True, 0))
    @patch("services.screen_manager.start")
    @patch("services.command_builder.build_command")
    def test_start_failure_htmx(self, mock_build, mock_start, mock_rate, client):
        mock_build.return_value = ["llama-server", "-m", "model.bin"]
        mock_start.return_value = {"success": False, "message": "Already running"}
        resp = client.post("/server/start/1", headers={"HX-Request": "true"})
        assert resp.status_code == 200
        assert b"Already running" in resp.data

    @patch("utils.rate_limit._limiter.is_allowed", return_value=(True, 0))
    @patch("services.screen_manager.start")
    @patch("services.command_builder.build_command")
    def test_start_success_redirect(self, mock_build, mock_start, mock_rate, client):
        mock_build.return_value = ["llama-server", "-m", "model.bin"]
        mock_start.return_value = {"success": True, "message": "Server started"}
        resp = client.post("/server/start/1", follow_redirects=False)
        assert resp.status_code == 302


class TestLogs:
    @patch("services.screen_manager.get_logs")
    def test_logs_default_lines(self, mock_logs, client):
        mock_logs.return_value = ["line1", "line2"]
        resp = client.get("/server/logs")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["logs"] == ["line1", "line2"]
        mock_logs.assert_called_once_with(50)

    @patch("services.screen_manager.get_logs")
    def test_logs_custom_lines(self, mock_logs, client):
        mock_logs.return_value = ["line1"]
        resp = client.get("/server/logs?lines=100")
        assert resp.status_code == 200
        mock_logs.assert_called_once_with(100)


class TestBenchmark:
    @patch("utils.rate_limit._limiter.is_allowed", return_value=(True, 0))
    @patch("services.benchmarks.benchmark_version")
    def test_benchmark_success(self, mock_bench, mock_rate, client):
        mock_bench.return_value = {"success": True, "tps": 30.5}
        resp = client.post("/version/1/benchmark")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        mock_bench.assert_called_once_with(1)


class TestStreamLogs:
    @patch("services.screen_manager.is_running", return_value=False)
    def test_stream_logs_response_headers(self, mock_running, client):
        resp = client.get("/server/stream-logs")
        assert resp.status_code == 200
        assert "text/event-stream" in resp.content_type
        assert resp.headers.get("Cache-Control") == "no-cache"
        assert resp.headers.get("X-Accel-Buffering") == "no"

    @patch("services.screen_manager.is_running", return_value=False)
    def test_stream_logs_no_process(self, mock_running, client):
        resp = client.get("/server/stream-logs")
        assert resp.status_code == 200
        assert b"[no process running]" in resp.data


class TestImportConfig:
    @patch("services.config_importer.import_running_config")
    def test_import_config_success_htmx(self, mock_import, client):
        mock_import.return_value = (1, 1, {"flag1": "val1"}, True)
        resp = client.post(
            "/server/import-config",
            data={"config_name": "Test Config"},
            headers={"HX-Request": "true"},
        )
        assert resp.status_code == 200
        assert b"Imported" in resp.data
        assert b"</strong>1</strong>" in resp.data or b"1</strong>" in resp.data

    @patch("services.config_importer.import_running_config")
    def test_import_config_unchanged_htmx(self, mock_import, client):
        mock_import.return_value = (1, 1, {}, False)
        resp = client.post(
            "/server/import-config",
            data={"config_name": "Test Config"},
            headers={"HX-Request": "true"},
        )
        assert resp.status_code == 200
        assert b"unchanged" in resp.data

    @patch("services.config_importer.import_running_config")
    def test_import_config_success_redirect(self, mock_import, client):
        mock_import.return_value = (1, 1, {"flag1": "val1"}, True)
        resp = client.post(
            "/server/import-config",
            data={"config_name": "Test Config"},
            follow_redirects=False,
        )
        assert resp.status_code == 302

    @patch("services.config_importer.import_running_config")
    def test_import_config_failure_htmx(self, mock_import, client):
        mock_import.side_effect = Exception("Import failed")
        resp = client.post(
            "/server/import-config",
            data={"config_name": "Test Config"},
            headers={"HX-Request": "true"},
        )
        assert resp.status_code == 200
        assert b"Import failed" in resp.data

    @patch("services.config_importer.import_running_config")
    def test_import_config_failure_redirect(self, mock_import, client):
        mock_import.side_effect = Exception("Import failed")
        resp = client.post(
            "/server/import-config",
            data={"config_name": "Test Config"},
            follow_redirects=False,
        )
        assert resp.status_code == 302
