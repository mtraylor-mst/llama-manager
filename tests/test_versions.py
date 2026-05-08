from datetime import datetime
from unittest.mock import patch, MagicMock


def _make_version_data():
    """Return a properly structured version data dict for template rendering."""
    return {
        "model_loading": {},
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


def _make_version(version_id=1, config_id=1):
    """Return a properly structured version dict."""
    return {
        "id": version_id,
        "config_id": config_id,
        "config_name": "Test",
        "version_number": version_id,
        "comments": "",
        "status": None,
        "created_at": datetime.now(),
    }


class TestHistory:
    @patch("services.screen_manager.get_running_version_id")
    @patch("models.configs.get_latest_version")
    @patch("models.configs.get_all_versions")
    @patch("models.configs.get_config")
    def test_history_success(
        self, mock_config, mock_versions, mock_latest, mock_running, client
    ):
        mock_config.return_value = {"id": 1, "name": "Test"}
        mock_versions.return_value = [_make_version(1)]
        mock_latest.return_value = {"id": 1}
        mock_running.return_value = None
        resp = client.get("/config/1/versions")
        assert resp.status_code == 200

    @patch("models.configs.get_config")
    def test_history_config_not_found(self, mock_config, client):
        mock_config.return_value = None
        resp = client.get("/config/999/versions", follow_redirects=False)
        assert resp.status_code == 302

    @patch("models.configs.get_version")
    @patch("services.screen_manager.get_running_version_id")
    @patch("models.configs.get_latest_version")
    @patch("models.configs.get_all_versions")
    @patch("models.configs.get_config")
    def test_history_running_is_this_config(
        self,
        mock_config,
        mock_versions,
        mock_latest,
        mock_running,
        mock_get_ver,
        client,
    ):
        mock_config.return_value = {"id": 1, "name": "Test"}
        mock_versions.return_value = [_make_version(1), _make_version(2)]
        mock_latest.return_value = {"id": 2}
        mock_running.return_value = 1
        mock_get_ver.return_value = _make_version(1)
        resp = client.get("/config/1/versions")
        assert resp.status_code == 200
        assert b"running" in resp.data.lower()

    @patch("models.configs.get_version")
    @patch("services.screen_manager.get_running_version_id")
    @patch("models.configs.get_latest_version")
    @patch("models.configs.get_all_versions")
    @patch("models.configs.get_config")
    def test_history_running_is_different_config(
        self,
        mock_config,
        mock_versions,
        mock_latest,
        mock_running,
        mock_get_ver,
        client,
    ):
        mock_config.return_value = {"id": 1, "name": "Test"}
        mock_versions.return_value = [_make_version(1)]
        mock_latest.return_value = {"id": 1}
        mock_running.return_value = 999
        mock_get_ver.return_value = _make_version(999, config_id=999)
        resp = client.get("/config/1/versions")
        assert resp.status_code == 200


class TestEditLatest:
    @patch("models.configs.get_config")
    def test_edit_latest_config_not_found(self, mock_config, client):
        mock_config.return_value = None
        resp = client.get("/config/999/version/latest/edit", follow_redirects=False)
        assert resp.status_code == 302

    @patch("models.configs.get_latest_version")
    @patch("models.configs.get_config")
    def test_edit_latest_no_versions(self, mock_config, mock_latest, client):
        mock_config.return_value = {"id": 1, "name": "Test"}
        mock_latest.return_value = None
        resp = client.get("/config/1/version/latest/edit", follow_redirects=False)
        assert resp.status_code == 302

    @patch("models.configs.get_all_versions")
    @patch("services.screen_manager.get_running_version_id")
    @patch("models.configs.get_all_version_data")
    @patch("models.configs.get_latest_version")
    @patch("models.configs.get_config")
    def test_edit_latest_success(
        self, mock_config, mock_latest, mock_data, mock_running, mock_versions, client
    ):
        mock_config.return_value = {"id": 1, "name": "Test"}
        mock_latest.return_value = _make_version(1)
        mock_data.return_value = _make_version_data()
        mock_running.return_value = None
        mock_versions.return_value = []
        resp = client.get("/config/1/version/latest/edit")
        assert resp.status_code == 200


class TestEdit:
    @patch("models.configs.get_version")
    def test_edit_version_not_found(self, mock_version, client):
        mock_version.return_value = None
        resp = client.get("/version/999/edit", follow_redirects=False)
        assert resp.status_code == 302

    @patch("models.configs.get_all_versions")
    @patch("services.screen_manager.get_running_version_id")
    @patch("models.configs.get_all_version_data")
    @patch("models.configs.get_version")
    def test_edit_success(
        self, mock_version, mock_data, mock_running, mock_versions, client
    ):
        mock_version.return_value = _make_version(1)
        mock_data.return_value = _make_version_data()
        mock_running.return_value = None
        mock_versions.return_value = []
        resp = client.get("/version/1/edit")
        assert resp.status_code == 200


class TestForkEdit:
    @patch("models.configs.get_version")
    def test_fork_edit_version_not_found(self, mock_version, client):
        mock_version.return_value = None
        resp = client.get("/version/999/fork-edit", follow_redirects=False)
        assert resp.status_code == 302

    @patch("models.configs.get_all_versions")
    @patch("services.screen_manager.get_running_version_id")
    @patch("models.configs.get_all_version_data")
    @patch("models.configs.get_version")
    def test_fork_edit_success(
        self, mock_version, mock_data, mock_running, mock_versions, client
    ):
        mock_version.return_value = _make_version(1)
        mock_data.return_value = _make_version_data()
        mock_running.return_value = None
        mock_versions.return_value = []
        resp = client.get("/version/1/fork-edit")
        assert resp.status_code == 200
        assert b"Fork" in resp.data


class TestDelete:
    @patch("models.configs.get_version")
    def test_delete_version_not_found(self, mock_version, client):
        mock_version.return_value = None
        resp = client.post("/version/999/delete", follow_redirects=False)
        assert resp.status_code == 302

    @patch("services.screen_manager.get_running_version_id")
    @patch("models.configs.get_version")
    def test_delete_running_version(self, mock_version, mock_running, client):
        mock_version.return_value = {"id": 1, "config_id": 1, "version_number": 1}
        mock_running.return_value = 1
        resp = client.post("/version/1/delete", follow_redirects=False)
        assert resp.status_code == 302

    @patch("models.configs.delete_version")
    @patch("services.screen_manager.get_running_version_id")
    @patch("models.configs.get_version")
    def test_delete_failure(self, mock_version, mock_running, mock_delete, client):
        mock_version.return_value = {"id": 1, "config_id": 1, "version_number": 1}
        mock_running.return_value = None
        mock_delete.return_value = False
        resp = client.post("/version/1/delete", follow_redirects=False)
        assert resp.status_code == 302

    @patch("models.configs.delete_version")
    @patch("services.screen_manager.get_running_version_id")
    @patch("models.configs.get_version")
    def test_delete_success(self, mock_version, mock_running, mock_delete, client):
        mock_version.return_value = {"id": 1, "config_id": 1, "version_number": 1}
        mock_running.return_value = None
        mock_delete.return_value = True
        resp = client.post("/version/1/delete", follow_redirects=False)
        assert resp.status_code == 302


class TestDuplicate:
    @patch("models.configs.get_version")
    def test_duplicate_version_not_found(self, mock_version, client):
        mock_version.return_value = None
        resp = client.post("/version/999/duplicate", follow_redirects=False)
        assert resp.status_code == 302

    @patch("models.configs.duplicate_version")
    @patch("models.configs.get_version")
    def test_duplicate_success(self, mock_version, mock_dup, client):
        mock_version.return_value = {"id": 1, "config_id": 1, "version_number": 1}
        mock_dup.return_value = 2
        resp = client.post("/version/1/duplicate", follow_redirects=False)
        assert resp.status_code == 302
        assert "version/2/edit" in resp.location


class TestCommand:
    @patch("services.command_builder.build_command_string")
    def test_command_success(self, mock_build, client):
        mock_build.return_value = "llama-server -m model.gguf"
        resp = client.get("/version/1/command")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["command"] == "llama-server -m model.gguf"


class TestCommonOptionsHelpers:
    @patch("models.configs.get_common_options")
    def test_get_common_option_set(self, mock_opts):
        mock_opts.return_value = [
            {"category": "model_loading", "column_name": "n_gpu_layers"},
            {"category": "server", "column_name": "host"},
        ]
        from routes.versions import get_common_option_set

        result = get_common_option_set()
        assert ("model_loading", "n_gpu_layers") in result
        assert ("server", "host") in result

    @patch("models.configs.get_common_options")
    def test_get_common_option_set_db_error(self, mock_opts):
        mock_opts.side_effect = Exception("DB error")
        from routes.versions import get_common_option_set

        result = get_common_option_set()
        assert result == set()

    @patch("models.configs.get_common_options")
    def test_get_common_options_list(self, mock_opts):
        mock_opts.return_value = [
            {
                "id": 1,
                "category": "model_loading",
                "column_name": "n_gpu_layers",
                "custom_label": "GPU Layers",
            },
        ]
        from routes.versions import get_common_options_list

        result = get_common_options_list()
        assert len(result) == 1
        assert result[0]["label"] == "GPU Layers"

    @patch("models.configs.get_common_options")
    def test_get_common_options_list_no_custom_label(self, mock_opts):
        mock_opts.return_value = [
            {
                "id": 1,
                "category": "model_loading",
                "column_name": "n_gpu_layers",
                "custom_label": None,
            },
        ]
        from routes.versions import get_common_options_list

        result = get_common_options_list()
        assert result[0]["label"] == "n_gpu_layers"

    @patch("models.configs.get_common_options")
    def test_get_common_options_list_db_error(self, mock_opts):
        mock_opts.side_effect = Exception("DB error")
        from routes.versions import get_common_options_list

        result = get_common_options_list()
        assert result == []

    @patch("models.configs.get_common_options")
    def test_get_common_options_grouped(self, mock_opts):
        mock_opts.return_value = [
            {
                "id": 1,
                "category": "model_loading",
                "column_name": "n_gpu_layers",
                "custom_label": None,
            },
            {
                "id": 2,
                "category": "model_loading",
                "column_name": "mmproj",
                "custom_label": None,
            },
            {
                "id": 3,
                "category": "server",
                "column_name": "host",
                "custom_label": None,
            },
        ]
        from routes.versions import get_common_options_grouped

        result = get_common_options_grouped()
        groups = {g["label"]: g for g in result}
        assert "Model Loading" in groups
        assert len(groups["Model Loading"]["fields"]) == 2
        assert "Server" in groups
        assert len(groups["Server"]["fields"]) == 1

    @patch("models.configs.get_common_options")
    def test_get_common_options_grouped_db_error(self, mock_opts):
        mock_opts.side_effect = Exception("DB error")
        from routes.versions import get_common_options_grouped

        result = get_common_options_grouped()
        assert result == []


class TestEditFormPostFork:
    @patch("models.configs.save_complex_table")
    @patch("models.configs.save_category")
    @patch("models.configs.create_version")
    @patch("models.configs.get_all_version_data")
    @patch("models.base.get_conn")
    @patch("models.configs.get_version")
    def test_fork_post_creates_new_version(
        self,
        mock_version,
        mock_get_conn,
        mock_data,
        mock_create_ver,
        mock_save_cat,
        mock_save_complex,
        client,
    ):
        mock_version.return_value = _make_version(1)
        mock_data.return_value = _make_version_data()
        mock_create_ver.return_value = 99
        mock_conn = MagicMock()
        mock_conn.return_value.__enter__.return_value = mock_conn.return_value
        mock_conn.return_value.cursor.return_value.__enter__.return_value = MagicMock()
        mock_get_conn.return_value = mock_conn

        resp = client.post(
            "/version/1/fork-edit",
            data={"comments": "forked version"},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert "config/1" in resp.location
        mock_create_ver.assert_called_once()


class TestSaveVersionData:
    @patch("models.configs.save_complex_table")
    @patch("models.configs.save_category")
    @patch("models.base.get_conn")
    def test_save_version_data_basic(
        self, mock_get_conn, mock_save_cat, mock_save_complex
    ):
        from routes.versions import _save_version_data

        mock_conn = MagicMock()
        mock_conn.return_value.__enter__.return_value = mock_conn.return_value
        mock_conn.return_value.cursor.return_value.__enter__.return_value = MagicMock()
        mock_get_conn.return_value = mock_conn

        form_data = {
            "comments": "test comments",
            "status": "tested",
            "model_loading_model_path": "/models/test.gguf",
            "sampling_temperature": "0.8",
        }
        _save_version_data(10, 1, form_data)

        mock_save_cat.assert_called()
        calls = mock_save_cat.call_args_list
        cats_saved = [c[0][1] for c in calls]
        assert "model_loading" in cats_saved
        assert "sampling" in cats_saved

    @patch("models.configs.save_complex_table")
    @patch("models.configs.save_category")
    @patch("models.base.get_conn")
    def test_save_version_data_tristate(
        self, mock_get_conn, mock_save_cat, mock_save_complex
    ):
        from routes.versions import _save_version_data

        mock_conn = MagicMock()
        mock_conn.return_value.__enter__.return_value = mock_conn.return_value
        mock_conn.return_value.cursor.return_value.__enter__.return_value = MagicMock()
        mock_get_conn.return_value = mock_conn

        form_data = {
            "comments": "",
            "status": None,
            "memory_mmap": "enable",
            "memory_mlock": "1",
        }
        _save_version_data(10, 1, form_data)

        calls = mock_save_cat.call_args_list
        mem_call = [c for c in calls if c[0][1] == "memory"][0]
        data = mem_call[0][2]
        assert data["mmap"] == 1
        assert data["mlock"] == 1

    @patch("models.configs.save_complex_table")
    @patch("models.configs.save_category")
    @patch("models.base.get_conn")
    def test_save_version_data_complex_table(
        self, mock_get_conn, mock_save_cat, mock_save_complex
    ):
        from routes.versions import _save_version_data

        mock_conn = MagicMock()
        mock_conn.return_value.__enter__.return_value = mock_conn.return_value
        mock_conn.return_value.cursor.return_value.__enter__.return_value = MagicMock()
        mock_get_conn.return_value = mock_conn

        form_data = {
            "comments": "",
            "status": None,
            "lora_adapters_ids": "0",
            "lora_adapters_0_path": "/lora/test.gguf",
            "lora_adapters_0_scale": "0.5",
        }
        _save_version_data(10, 1, form_data)

        mock_save_complex.assert_called()
        lora_call = [
            c for c in mock_save_complex.call_args_list if c[0][1] == "lora_adapters"
        ][0]
        rows = lora_call[0][2]
        assert len(rows) == 1
        assert rows[0]["path"] == "/lora/test.gguf"
