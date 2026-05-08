from unittest.mock import patch


class TestAPIRoutes:
    @patch("services.command_builder.get_models_in_dir")
    def test_list_models_default(self, mock_models, client):
        mock_models.return_value = [
            {"path": "/models/test.gguf", "name": "test.gguf", "rel": "test.gguf"}
        ]
        resp = client.get("/api/models")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 1
        assert data[0]["name"] == "test.gguf"

    @patch("services.command_builder.get_models_in_dir")
    def test_list_models_with_dir(self, mock_models, client):
        mock_models.return_value = []
        resp = client.get("/api/models?dir=subfolder")
        assert resp.status_code == 200

    @patch("models.configs.get_all_version_data")
    def test_version_data(self, mock_data, client):
        mock_data.return_value = {
            "model_loading": {"model_path": "/test.gguf"},
            "context_batching": {},
            "cpu_threading": {},
            "gpu_device": {},
            "memory": {},
            "sampling": {},
            "server": {},
            "speculative": {},
            "chat_templates": {},
            "checkpoints": {},
            "logging": {},
            "advanced": {},
            "lora_adapters": [],
            "control_vectors": [],
            "logit_biases": [],
            "override_kv": [],
            "override_tensors": [],
            "dry_sequence_breakers": [],
        }
        resp = client.get("/api/version/1/data")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "categories" in data
        assert "complex" in data


class TestServerRoutes:
    @patch("services.screen_manager.get_running_version_id")
    @patch("services.screen_manager.get_status")
    def test_status_stopped(self, mock_status, mock_vid, client):
        mock_status.return_value = {
            "running": False,
            "state": "stopped",
            "name": None,
            "line": "",
        }
        mock_vid.return_value = None
        resp = client.get("/server/status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["running"] is False

    @patch("services.screen_manager.stop")
    def test_stop(self, mock_stop, client):
        mock_stop.return_value = {"success": True, "message": "Server stopped"}
        resp = client.post("/server/stop", follow_redirects=False)
        assert resp.status_code in (200, 302)

    @patch("services.screen_manager.start")
    @patch("services.command_builder.build_command")
    def test_start(self, mock_cmd, mock_start, client):
        mock_cmd.return_value = ["llama-server", "-m", "model.gguf"]
        mock_start.return_value = {"success": True, "message": "Started (PID 12345)"}
        resp = client.post("/server/start/1", follow_redirects=False)
        assert resp.status_code in (200, 302)

    @patch("services.screen_manager.get_logs")
    def test_logs(self, mock_logs, client):
        mock_logs.return_value = "line1\nline2\n"
        resp = client.get("/server/logs?lines=10")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "logs" in data

    @patch("services.benchmarks.benchmark_version")
    def test_benchmark(self, mock_bench, client):
        mock_bench.return_value = {
            "success": True,
            "tps": 50.0,
            "tokens_generated": 128,
            "duration_sec": 2.56,
            "vram_used_mb": 4096,
            "peak_cpu_pct": 85.0,
            "error": None,
        }
        resp = client.post("/version/1/benchmark")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["tps"] == 50.0


class TestIndexRoute:
    @patch("models.configs.get_all_configs")
    @patch("models.configs.get_version")
    def test_index(self, mock_version, mock_configs, client):
        mock_configs.return_value = [
            {"id": 1, "name": "Test Config", "description": "", "model_dir": ""}
        ]
        mock_version.return_value = None
        resp = client.get("/")
        assert resp.status_code == 200
