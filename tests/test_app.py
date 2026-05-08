import base64
import pytest
from unittest.mock import patch


class TestCreateAppAuthValidation:
    def test_create_app_auth_validation_error_missing_user(self):
        with (
            patch("app.AUTH_ENABLED", True),
            patch("app.AUTH_USER", ""),
            patch("app.AUTH_PASSWORD", "secret"),
        ):
            from app import create_app

            with pytest.raises(
                RuntimeError, match="AUTH_USER and AUTH_PASSWORD must both be set"
            ):
                create_app()

    def test_create_app_auth_validation_error_missing_password(self):
        with (
            patch("app.AUTH_ENABLED", True),
            patch("app.AUTH_USER", "admin"),
            patch("app.AUTH_PASSWORD", ""),
        ):
            from app import create_app

            with pytest.raises(
                RuntimeError, match="AUTH_USER and AUTH_PASSWORD must both be set"
            ):
                create_app()

    def test_create_app_auth_validation_error_both_missing(self):
        with (
            patch("app.AUTH_ENABLED", True),
            patch("app.AUTH_USER", ""),
            patch("app.AUTH_PASSWORD", ""),
        ):
            from app import create_app

            with pytest.raises(
                RuntimeError, match="AUTH_USER and AUTH_PASSWORD must both be set"
            ):
                create_app()

    def test_create_app_auth_validation_passes_when_all_set(self):
        with (
            patch("app.AUTH_ENABLED", True),
            patch("app.AUTH_USER", "admin"),
            patch("app.AUTH_PASSWORD", "secret"),
        ):
            from app import create_app

            app = create_app()
            assert app is not None

    def test_create_app_succeeds_without_auth(self):
        with patch("app.AUTH_ENABLED", False):
            from app import create_app

            app = create_app()
            assert app is not None


@pytest.fixture
def auth_app():
    """Create an app with auth enabled for middleware tests."""
    with (
        patch("app.AUTH_ENABLED", True),
        patch("app.AUTH_USER", "admin"),
        patch("app.AUTH_PASSWORD", "secret"),
    ):
        from app import create_app

        app = create_app()
        app.config["TESTING"] = True
        csrf = app.extensions.get("csrf")
        if csrf:
            for func in app.view_functions.values():
                csrf.exempt(func)
        yield app


@pytest.fixture
def auth_client(auth_app):
    return auth_app.test_client()


class TestAuthMiddleware:
    def test_auth_middleware_missing_credentials(self, auth_client):
        resp = auth_client.get("/")
        assert resp.status_code == 401
        assert "WWW-Authenticate" in resp.headers
        assert 'Basic realm="Login Required"' in resp.headers["WWW-Authenticate"]

    def test_auth_middleware_invalid_credentials(self, auth_client):
        creds = base64.b64encode(b"admin:wrongpass").decode()
        resp = auth_client.get("/", headers={"Authorization": f"Basic {creds}"})
        assert resp.status_code == 401

    @patch("models.configs.get_all_configs")
    @patch("services.screen_manager.get_running_version_id")
    @patch("services.screen_manager.get_status")
    def test_auth_middleware_valid_credentials(
        self, mock_status, mock_vid, mock_configs, auth_client
    ):
        mock_configs.return_value = []
        mock_status.return_value = {
            "running": False,
            "state": "stopped",
            "name": None,
            "line": "",
        }
        mock_vid.return_value = None
        creds = base64.b64encode(b"admin:secret").decode()
        resp = auth_client.get("/", headers={"Authorization": f"Basic {creds}"})
        assert resp.status_code == 200

    def test_auth_middleware_wrong_username(self, auth_client):
        creds = base64.b64encode(b"wronguser:secret").decode()
        resp = auth_client.get("/", headers={"Authorization": f"Basic {creds}"})
        assert resp.status_code == 401


class TestContextProcessor:
    @patch("models.configs.get_all_configs")
    @patch("models.configs.get_version")
    @patch("services.screen_manager.get_running_version_id")
    @patch("services.screen_manager.get_status")
    def test_context_processor_injects_keys_stopped(
        self, mock_status, mock_vid, mock_version, mock_configs, auth_client
    ):
        mock_status.return_value = {
            "running": False,
            "state": "stopped",
            "name": None,
            "line": "",
        }
        mock_vid.return_value = None
        mock_configs.return_value = []

        creds = base64.b64encode(b"admin:secret").decode()
        resp = auth_client.get("/", headers={"Authorization": f"Basic {creds}"})
        assert resp.status_code == 200

        ctx = auth_client.application.app_context()
        ctx.push()
        processors = auth_client.application.template_context_processors[None]
        merged = {}
        for proc in processors:
            merged.update(proc())
        assert "server_status" in merged
        assert "running_version_id" in merged
        assert "running_version_info" in merged
        assert "model_dir" in merged
        assert merged["running_version_id"] is None
        ctx.pop()

    @patch("models.configs.get_all_configs")
    @patch("models.configs.get_version")
    @patch("services.screen_manager.get_running_version_id")
    @patch("services.screen_manager.get_status")
    def test_context_processor_injects_keys_running(
        self, mock_status, mock_vid, mock_version, mock_configs, auth_client
    ):
        mock_status.return_value = {
            "running": True,
            "state": "running",
            "name": "Test Model",
            "line": "llama-server -m test.gguf",
        }
        mock_vid.return_value = 5
        mock_version.return_value = {"id": 5, "version_number": 3}
        mock_configs.return_value = []

        creds = base64.b64encode(b"admin:secret").decode()
        resp = auth_client.get("/", headers={"Authorization": f"Basic {creds}"})
        assert resp.status_code == 200

        ctx = auth_client.application.app_context()
        ctx.push()
        processors = auth_client.application.template_context_processors[None]
        merged = {}
        for proc in processors:
            merged.update(proc())
        assert merged["server_status"]["running"] is True
        assert merged["running_version_id"] == 5
        assert merged["running_version_info"]["id"] == 5
        ctx.pop()


class TestBlueprintRegistration:
    def test_all_blueprints_registered(self):
        with patch("app.AUTH_ENABLED", False):
            from app import create_app

            app = create_app()
            registered = list(app.blueprints.keys())
            assert "configs" in registered
            assert "versions" in registered
            assert "server" in registered
            assert "api" in registered
            assert "common" in registered

    def test_index_route_registered(self):
        with patch("app.AUTH_ENABLED", False):
            from app import create_app

            app = create_app()
            assert "index" in app.view_functions
