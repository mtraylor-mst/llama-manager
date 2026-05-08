import os
from unittest.mock import patch


class TestGenerateSecretKey:
    def test_returns_hex_string(self):
        from config import _generate_secret_key

        result = _generate_secret_key()
        assert len(result) == 64
        int(result, 16)

    def test_returns_unique_keys(self):
        from config import _generate_secret_key

        a = _generate_secret_key()
        b = _generate_secret_key()
        assert a != b


class TestDebugParsing:
    @patch.dict(os.environ, {"DEBUG": "true"}, clear=True)
    def test_debug_true(self):
        import importlib

        import config

        importlib.reload(config)
        assert config.DEBUG is True

    @patch.dict(os.environ, {"DEBUG": "1"}, clear=True)
    def test_debug_1(self):
        import importlib

        import config

        importlib.reload(config)
        assert config.DEBUG is True

    @patch.dict(os.environ, {"DEBUG": "yes"}, clear=True)
    def test_debug_yes(self):
        import importlib

        import config

        importlib.reload(config)
        assert config.DEBUG is True

    @patch.dict(os.environ, {"DEBUG": "false"}, clear=True)
    def test_debug_false(self):
        import importlib

        import config

        importlib.reload(config)
        assert config.DEBUG is False

    @patch.dict(os.environ, {"DEBUG": "0"}, clear=True)
    def test_debug_0(self):
        import importlib

        import config

        importlib.reload(config)
        assert config.DEBUG is False

    @patch.dict(os.environ, {"DEBUG": ""}, clear=True)
    def test_debug_empty(self):
        import importlib

        import config

        importlib.reload(config)
        assert config.DEBUG is False


class TestAuthEnabledParsing:
    @patch.dict(os.environ, {"AUTH_ENABLED": "true"}, clear=True)
    def test_auth_enabled_true(self):
        import importlib

        import config

        importlib.reload(config)
        assert config.AUTH_ENABLED is True

    @patch.dict(os.environ, {"AUTH_ENABLED": "false"}, clear=True)
    def test_auth_enabled_false(self):
        import importlib

        import config

        importlib.reload(config)
        assert config.AUTH_ENABLED is False


class TestDefaultValues:
    @patch.dict(os.environ, {}, clear=True)
    def test_defaults(self):
        import importlib

        import config

        importlib.reload(config)
        assert config.DB_HOST == "127.0.0.1"
        assert config.DB_USER == "username"
        assert config.DB_PASS == "password"
        assert config.DB_NAME == "llama_configs"
        assert config.MODEL_DIR == "/home/mtraylor/.cache/huggingface/hub/"
        assert config.SERVER_BINARY == "/usr/local/bin/llama-server"
        assert config.AUTH_USER == ""
        assert config.AUTH_PASSWORD == ""
        assert config.DEFAULT_API_HOST == "127.0.0.1"
        assert config.DEFAULT_API_PORT == 8080


class TestEnvVarOverrides:
    @patch.dict(
        os.environ,
        {
            "LLAMA_DB_HOST": "db.example.com",
            "LLAMA_DB_USER": "admin",
            "LLAMA_DB_PASS": "secret",
            "LLAMA_DB_NAME": "testdb",
            "LLAMA_MODEL_DIR": "/custom/models",
            "LLAMA_SERVER_BINARY": "/opt/llama-server",
            "AUTH_USER": "testuser",
            "AUTH_PASSWORD": "testpass",
            "LLAMA_SECRET_KEY": "my-custom-key",
        },
        clear=True,
    )
    def test_env_overrides(self):
        import importlib

        import config

        importlib.reload(config)
        assert config.DB_HOST == "db.example.com"
        assert config.DB_USER == "admin"
        assert config.DB_PASS == "secret"
        assert config.DB_NAME == "testdb"
        assert config.MODEL_DIR == "/custom/models"
        assert config.SERVER_BINARY == "/opt/llama-server"
        assert config.AUTH_USER == "testuser"
        assert config.AUTH_PASSWORD == "testpass"
        assert config.SECRET_KEY == "my-custom-key"


class TestSecretKeyFallback:
    @patch.dict(os.environ, {}, clear=True)
    def test_secret_key_fallback(self):
        import importlib

        import config

        importlib.reload(config)
        assert len(config.SECRET_KEY) == 64
        int(config.SECRET_KEY, 16)
