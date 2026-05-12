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


class TestAPIPathTraversal:
    @patch("os.path.realpath")
    def test_list_models_path_traversal_denied(self, mock_realpath, client):
        def resolve_path(p):
            if "../../etc" in p or "../etc" in p:
                return "/etc/passwd"
            return p

        mock_realpath.side_effect = resolve_path
        resp = client.get("/api/models?dir=../../etc")
        assert resp.status_code == 403
        data = resp.get_json()
        assert "error" in data


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


class TestBenchmarkRoutes:
    @patch("services.screen_manager.get_running_version_id")
    @patch("services.screen_manager.get_status")
    @patch("models.configs.get_all_config_benchmarks")
    @patch("models.configs.get_all_versions")
    @patch("models.configs.get_config")
    def test_benchmarks_view(
        self, mock_config, mock_versions, mock_benchmarks, mock_status, mock_vid, client
    ):
        mock_config.return_value = {"id": 1, "name": "Test Config"}
        mock_versions.return_value = [{"id": 1, "version_number": 1}]
        mock_benchmarks.return_value = [
            {"id": 1, "tps": 30.0, "version_id": 1, "version_number": 1}
        ]
        mock_status.return_value = {
            "running": False,
            "state": "stopped",
            "name": None,
            "line": "",
        }
        mock_vid.return_value = None
        resp = client.get("/config/1/benchmarks")
        assert resp.status_code == 200

    @patch("services.screen_manager.get_running_version_id")
    @patch("services.screen_manager.get_status")
    @patch("models.configs.get_all_config_benchmarks")
    @patch("models.configs.get_all_versions")
    @patch("models.configs.get_config")
    def test_benchmarks_config_not_found(
        self, mock_config, mock_versions, mock_benchmarks, mock_status, mock_vid, client
    ):
        mock_config.return_value = None
        mock_status.return_value = {
            "running": False,
            "state": "stopped",
            "name": None,
            "line": "",
        }
        mock_vid.return_value = None
        resp = client.get("/config/999/benchmarks", follow_redirects=False)
        assert resp.status_code == 302

    @patch("services.screen_manager.get_running_version_id")
    @patch("services.screen_manager.get_status")
    @patch("models.configs.get_all_model_benchmarks")
    @patch("models.configs.get_all_configs")
    def test_compare_benchmarks_no_selection(
        self, mock_configs, mock_benchmarks, mock_status, mock_vid, client
    ):
        mock_configs.return_value = [
            {"id": 1, "name": "Alpha"},
            {"id": 2, "name": "Beta"},
        ]
        mock_status.return_value = {
            "running": False,
            "state": "stopped",
            "name": None,
            "line": "",
        }
        mock_vid.return_value = None
        resp = client.get("/benchmarks/compare")
        assert resp.status_code == 200
        mock_benchmarks.assert_not_called()

    @patch("services.screen_manager.get_running_version_id")
    @patch("services.screen_manager.get_status")
    @patch("models.configs.get_all_model_benchmarks")
    @patch("models.configs.get_all_configs")
    def test_compare_benchmarks_with_selection(
        self, mock_configs, mock_benchmarks, mock_status, mock_vid, client
    ):
        mock_configs.return_value = [
            {"id": 1, "name": "Alpha"},
            {"id": 2, "name": "Beta"},
        ]
        mock_benchmarks.return_value = [
            {
                "id": 1,
                "tps": 30.0,
                "config_id": 1,
                "config_name": "Alpha",
                "version_id": 10,
                "version_number": 1,
            },
            {
                "id": 2,
                "tps": 50.0,
                "config_id": 2,
                "config_name": "Beta",
                "version_id": 20,
                "version_number": 1,
            },
        ]
        mock_status.return_value = {
            "running": False,
            "state": "stopped",
            "name": None,
            "line": "",
        }
        mock_vid.return_value = None
        resp = client.get("/benchmarks/compare?config_id=1&config_id=2")
        assert resp.status_code == 200
        mock_benchmarks.assert_called_once_with([1, 2])

    @patch("services.command_diff.diff_commands")
    def test_benchmark_diff_success(self, mock_diff, client):
        mock_diff.return_value = {
            "added": [],
            "removed": [{"flag": "--mmap", "value": None}],
            "changed": [{"flag": "-c", "old_value": "4096", "new_value": "8192"}],
        }
        resp = client.get("/api/benchmarks/diff?v1=1&v2=2")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["removed"]) == 1
        assert len(data["changed"]) == 1
        mock_diff.assert_called_once_with(1, 2)

    @patch("services.command_diff.diff_commands")
    def test_benchmark_diff_missing_v1(self, mock_diff, client):
        resp = client.get("/api/benchmarks/diff?v2=2")
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data
        mock_diff.assert_not_called()

    @patch("services.command_diff.diff_commands")
    def test_benchmark_diff_missing_both(self, mock_diff, client):
        resp = client.get("/api/benchmarks/diff")
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data
        mock_diff.assert_not_called()

    @patch("services.command_diff.diff_commands")
    def test_benchmark_diff_invalid_type(self, mock_diff, client):
        resp = client.get("/api/benchmarks/diff?v1=abc&v2=2")
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data
        mock_diff.assert_not_called()

    @patch("models.configs.delete_performance_metric")
    def test_delete_benchmark_success(self, mock_delete, client):
        mock_delete.return_value = True
        resp = client.post("/config/1/benchmark/5/delete", follow_redirects=False)
        assert resp.status_code == 302
        mock_delete.assert_called_once_with(5)

    @patch("models.configs.delete_performance_metric")
    def test_delete_benchmark_not_found(self, mock_delete, client):
        mock_delete.return_value = False
        resp = client.post("/config/1/benchmark/999/delete", follow_redirects=False)
        assert resp.status_code == 302
        mock_delete.assert_called_once_with(999)
