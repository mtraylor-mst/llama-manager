from datetime import datetime
from unittest.mock import patch


class TestNew:
    def test_new_get(self, client, mock_screen_manager):
        resp = client.get("/config/new")
        assert resp.status_code == 200

    @patch("models.configs.create_version")
    @patch("models.configs.create_config")
    def test_new_post_success(
        self, mock_create_cfg, mock_create_ver, client, mock_screen_manager
    ):
        mock_create_cfg.return_value = 1
        mock_create_ver.return_value = None

        resp = client.post(
            "/config/new",
            data={"name": "Test Config", "description": "Test", "model_dir": "/models"},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert "latest/edit" in resp.location
        mock_create_cfg.assert_called_once_with("Test Config", "Test", "/models")
        mock_create_ver.assert_called_once_with(1)

    def test_new_post_missing_name(self, client, mock_screen_manager):
        resp = client.post(
            "/config/new",
            data={"name": "", "description": "Test", "model_dir": "/models"},
        )
        assert resp.status_code == 200
        assert b"Name is required" in resp.data


class TestView:
    @patch("models.configs.get_performance_metrics")
    @patch("models.configs.get_all_versions")
    @patch("models.configs.get_latest_version")
    @patch("models.configs.get_config")
    def test_view_success(
        self,
        mock_get_cfg,
        mock_get_latest,
        mock_get_versions,
        mock_get_metrics,
        client,
        mock_screen_manager,
    ):
        mock_get_cfg.return_value = {"id": 1, "name": "Test Config"}
        mock_get_latest.return_value = {
            "id": 1,
            "version_number": 1,
            "created_at": datetime.now(),
        }
        mock_get_versions.return_value = [
            {"id": 1, "version_number": 1, "created_at": datetime.now()}
        ]
        mock_get_metrics.return_value = []

        resp = client.get("/config/1")
        assert resp.status_code == 200

    @patch("models.configs.get_config")
    def test_view_not_found(self, mock_get_cfg, client):
        mock_get_cfg.return_value = None

        resp = client.get("/config/999", follow_redirects=False)
        assert resp.status_code == 302

    @patch("models.configs.get_performance_metrics")
    @patch("models.configs.get_all_versions")
    @patch("models.configs.get_latest_version")
    @patch("models.configs.get_version")
    @patch("models.configs.get_config")
    def test_view_with_running_version(
        self,
        mock_get_cfg,
        mock_get_ver,
        mock_get_latest,
        mock_get_versions,
        mock_get_metrics,
        client,
        mock_screen_manager,
    ):
        mock_get_cfg.return_value = {"id": 1, "name": "Test Config"}
        mock_get_latest.return_value = {"id": 2, "version_number": 2}
        mock_get_versions.return_value = [
            {"id": 1, "version_number": 1, "created_at": datetime.now()},
            {"id": 2, "version_number": 2, "created_at": datetime.now()},
        ]
        mock_get_ver.return_value = {
            "id": 2,
            "version_number": 2,
            "config_name": "Test",
            "created_at": datetime.now(),
        }
        mock_get_metrics.return_value = [{"tps": 30}]
        mock_screen_manager["get_status"].return_value = {
            "running": True,
            "state": "running",
            "name": "test",
            "line": "",
        }
        mock_screen_manager["get_running_version_id"].return_value = 2

        resp = client.get("/config/1")
        assert resp.status_code == 200


class TestEdit:
    @patch("models.configs.get_config")
    def test_edit_get(self, mock_get_cfg, client, mock_screen_manager):
        mock_get_cfg.return_value = {"id": 1, "name": "Test Config"}

        resp = client.get("/config/1/edit")
        assert resp.status_code == 200

    @patch("models.configs.get_config")
    def test_edit_not_found(self, mock_get_cfg, client):
        mock_get_cfg.return_value = None

        resp = client.get("/config/999/edit", follow_redirects=False)
        assert resp.status_code == 302

    @patch("models.configs.update_config")
    @patch("models.configs.get_config")
    def test_edit_post_success(self, mock_get_cfg, mock_update, client):
        mock_get_cfg.return_value = {"id": 1, "name": "Test Config"}
        mock_update.return_value = None

        resp = client.post(
            "/config/1/edit",
            data={
                "name": "Updated",
                "description": "Updated desc",
                "model_dir": "/new",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 302
        mock_update.assert_called_once_with(1, "Updated", "Updated desc", "/new")

    @patch("models.configs.get_config")
    def test_edit_post_missing_name(self, mock_get_cfg, client, mock_screen_manager):
        mock_get_cfg.return_value = {"id": 1, "name": "Test Config"}

        resp = client.post(
            "/config/1/edit",
            data={"name": "", "description": "Test", "model_dir": "/models"},
        )
        assert resp.status_code == 200
        assert b"Name is required" in resp.data


class TestDelete:
    @patch("models.configs.delete_config")
    def test_delete_success(self, mock_delete, client):
        mock_delete.return_value = None

        resp = client.post("/config/1/delete", follow_redirects=False)
        assert resp.status_code == 302
        mock_delete.assert_called_once_with(1)
