from unittest.mock import patch


class TestCommonOptionsIndex:
    @patch("services.screen_manager.get_running_version_id")
    @patch("services.screen_manager.get_status")
    @patch("models.configs.get_all_configs")
    @patch("models.configs.get_common_options")
    def test_index_success(
        self, mock_opts, mock_configs, mock_status, mock_running, client
    ):
        mock_opts.return_value = [
            {
                "id": 1,
                "category": "model_loading",
                "column_name": "n_gpu_layers",
                "custom_label": "GPU Layers",
                "display_order": 0,
            }
        ]
        mock_configs.return_value = []
        mock_status.return_value = {
            "running": False,
            "state": "stopped",
            "name": None,
            "line": "",
        }
        mock_running.return_value = None
        resp = client.get("/common-options")
        assert resp.status_code == 200

    @patch("services.screen_manager.get_running_version_id")
    @patch("services.screen_manager.get_status")
    @patch("models.configs.get_all_configs")
    @patch("models.configs.get_common_options")
    def test_index_empty_options(
        self, mock_opts, mock_configs, mock_status, mock_running, client
    ):
        mock_opts.return_value = []
        mock_configs.return_value = []
        mock_status.return_value = {
            "running": False,
            "state": "stopped",
            "name": None,
            "line": "",
        }
        mock_running.return_value = None
        resp = client.get("/common-options")
        assert resp.status_code == 200

    @patch("services.screen_manager.get_running_version_id")
    @patch("services.screen_manager.get_status")
    @patch("models.configs.get_all_configs")
    @patch("models.configs.get_common_options")
    def test_index_db_error(
        self, mock_opts, mock_configs, mock_status, mock_running, client
    ):
        mock_opts.side_effect = Exception("DB error")
        mock_configs.return_value = []
        mock_status.return_value = {
            "running": False,
            "state": "stopped",
            "name": None,
            "line": "",
        }
        mock_running.return_value = None
        resp = client.get("/common-options")
        assert resp.status_code == 200
        assert b"Error loading common options" in resp.data


class TestToggle:
    def test_toggle_missing_params(self, client):
        resp = client.post(
            "/common-options/toggle",
            data="{}",
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_toggle_missing_category(self, client):
        resp = client.post(
            "/common-options/toggle",
            data='{"column_name": "n_gpu_layers"}',
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_toggle_missing_column_name(self, client):
        resp = client.post(
            "/common-options/toggle",
            data='{"category": "model_loading"}',
            content_type="application/json",
        )
        assert resp.status_code == 400

    @patch("models.configs.add_common_option")
    @patch("models.configs.is_common_option")
    def test_toggle_add_success(self, mock_is_common, mock_add, client):
        mock_is_common.return_value = False
        mock_add.return_value = True
        resp = client.post(
            "/common-options/toggle",
            data='{"category": "model_loading", "column_name": "n_gpu_layers", "add": true}',
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["added"] is True
        assert data["common"] is True

    @patch("models.configs.add_common_option")
    @patch("models.configs.is_common_option")
    def test_toggle_add_failure(self, mock_is_common, mock_add, client):
        mock_is_common.return_value = False
        mock_add.return_value = False
        resp = client.post(
            "/common-options/toggle",
            data='{"category": "model_loading", "column_name": "n_gpu_layers", "add": true}',
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["added"] is False

    @patch("models.configs.remove_common_option")
    @patch("models.configs.get_common_options")
    @patch("models.configs.is_common_option")
    def test_toggle_remove_success(
        self, mock_is_common, mock_opts, mock_remove, client
    ):
        mock_is_common.return_value = True
        mock_opts.return_value = [
            {
                "id": 1,
                "category": "model_loading",
                "column_name": "n_gpu_layers",
                "custom_label": None,
                "display_order": 0,
            }
        ]
        mock_remove.return_value = True
        resp = client.post(
            "/common-options/toggle",
            data='{"category": "model_loading", "column_name": "n_gpu_layers", "add": false}',
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["removed"] is True
        assert data["common"] is False

    @patch("models.configs.get_common_options")
    @patch("models.configs.is_common_option")
    def test_toggle_remove_not_found(self, mock_is_common, mock_opts, client):
        mock_is_common.return_value = True
        mock_opts.return_value = []
        resp = client.post(
            "/common-options/toggle",
            data='{"category": "model_loading", "column_name": "n_gpu_layers", "add": false}',
            content_type="application/json",
        )
        assert resp.status_code == 404

    @patch("models.configs.is_common_option")
    def test_toggle_already_common(self, mock_is_common, client):
        mock_is_common.return_value = True
        resp = client.post(
            "/common-options/toggle",
            data='{"category": "model_loading", "column_name": "n_gpu_layers", "add": true}',
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["common"] is True

    @patch("models.configs.is_common_option")
    def test_toggle_already_not_common(self, mock_is_common, client):
        mock_is_common.return_value = False
        resp = client.post(
            "/common-options/toggle",
            data='{"category": "model_loading", "column_name": "n_gpu_layers", "add": false}',
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["common"] is False

    @patch("models.configs.is_common_option")
    def test_toggle_db_error(self, mock_is_common, client):
        mock_is_common.side_effect = Exception("DB error")
        resp = client.post(
            "/common-options/toggle",
            data='{"category": "model_loading", "column_name": "n_gpu_layers"}',
            content_type="application/json",
        )
        assert resp.status_code == 500
        data = resp.get_json()
        assert "error" in data


class TestReorder:
    def test_reorder_empty_list(self, client):
        resp = client.post(
            "/common-options/reorder",
            data='{"order": []}',
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_reorder_no_data(self, client):
        resp = client.post(
            "/common-options/reorder",
            data="{}",
            content_type="application/json",
        )
        assert resp.status_code == 400

    @patch("models.configs.reorder_common_options")
    def test_reorder_success(self, mock_reorder, client):
        mock_reorder.return_value = None
        resp = client.post(
            "/common-options/reorder",
            data='{"order": [1, 3, 2]}',
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        mock_reorder.assert_called_once_with([1, 3, 2])


class TestRemove:
    @patch("models.configs.remove_common_option")
    def test_remove_success(self, mock_remove, client):
        mock_remove.return_value = True
        resp = client.post("/common-options/remove/1", follow_redirects=False)
        assert resp.status_code == 302
        assert "common-options" in resp.location

    @patch("models.configs.remove_common_option")
    def test_remove_failure(self, mock_remove, client):
        mock_remove.return_value = False
        resp = client.post("/common-options/remove/1", follow_redirects=False)
        assert resp.status_code == 302
        assert "common-options" in resp.location


class TestUpdateLabel:
    @patch("models.base.get_conn")
    def test_update_label_success(self, mock_conn, client):
        mock_cursor = mock_conn.return_value.cursor.return_value
        mock_cursor.__enter__.return_value = mock_cursor
        mock_conn.return_value.__enter__.return_value = mock_conn.return_value
        resp = client.post(
            "/common-options/update-label/1",
            data={"custom_label": "New Label"},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert "common-options" in resp.location

    @patch("models.base.get_conn")
    def test_update_label_empty_clears(self, mock_conn, client):
        mock_cursor = mock_conn.return_value.cursor.return_value
        mock_cursor.__enter__.return_value = mock_cursor
        mock_conn.return_value.__enter__.return_value = mock_conn.return_value
        resp = client.post(
            "/common-options/update-label/1",
            data={"custom_label": ""},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert "common-options" in resp.location
