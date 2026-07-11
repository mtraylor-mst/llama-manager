"""Tests for models/templates.py and routes/configs.py template endpoints."""

from unittest.mock import patch, MagicMock


class MockDictRow(dict):
    """A dict that also supports attribute access like DB rows."""
    def __getitem__(self, key):
        return super().get(key)


class TestCreateTemplate:
    @patch("models.templates.get_conn")
    def test_create_template(self, mock_get_conn):
        from models.templates import create_template

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.lastrowid = 1
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        result = create_template("Test Template", "A test", 42)
        assert result == 1
        mock_cur.execute.assert_called_once()


class TestGetAllTemplates:
    @patch("models.templates.get_conn")
    def test_get_all_templates(self, mock_get_conn):
        from models.templates import get_all_templates

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.fetchall.return_value = [
            MockDictRow({"id": 1, "name": "Template 1"}),
        ]
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        result = get_all_templates()
        assert len(result) == 1
        assert result[0]["name"] == "Template 1"


class TestGetTemplate:
    @patch("models.templates.get_conn")
    def test_get_template_found(self, mock_get_conn):
        from models.templates import get_template

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = MockDictRow({"id": 1, "name": "Test"})
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        result = get_template(1)
        assert result is not None
        assert result["name"] == "Test"

    @patch("models.templates.get_conn")
    def test_get_template_not_found(self, mock_get_conn):
        from models.templates import get_template

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = None
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        result = get_template(999)
        assert result is None


class TestDeleteTemplate:
    @patch("models.templates.get_conn")
    def test_delete_success(self, mock_get_conn):
        from models.templates import delete_template

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.rowcount = 1
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        result = delete_template(1)
        assert result is True

    @patch("models.templates.get_conn")
    def test_delete_not_found(self, mock_get_conn):
        from models.templates import delete_template

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.rowcount = 0
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        result = delete_template(999)
        assert result is False


class TestTemplateVariables:
    @patch("models.templates.get_conn")
    def test_save_and_get_variables(self, mock_get_conn):
        from models.templates import save_template_variables, get_template_variables

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.fetchall.return_value = [
            MockDictRow({"variable_name": "model_path", "default_value": "/models/test.gguf"}),
        ]
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        save_template_variables(1, [
            {"variable_name": "model_path", "display_label": "Model Path",
             "default_value": "/models/test.gguf", "hint": "Path to model"},
        ])

        result = get_template_variables(1)
        assert len(result) == 1
        assert result[0]["variable_name"] == "model_path"


class TestInstantiateTemplate:
    @patch("models.templates.save_complex_table")
    @patch("models.templates.save_category")
    @patch("models.templates.create_version")
    @patch("models.templates.create_config")
    @patch("models.templates.get_all_version_data")
    @patch("models.templates.get_template")
    def test_instantiate_basic(
        self, mock_get_template, mock_get_data, mock_create_config,
        mock_create_version, mock_save_cat, mock_save_complex
    ):
        from models.templates import instantiate_template

        mock_get_template.return_value = MockDictRow({
            "id": 1,
            "source_version_id": 42,
        })
        mock_get_data.return_value = {
            "model_loading": {"version_id": 42, "model_path": "{{model_path}}"},
            "context_batching": {"version_id": 42, "ctx_size": 8192},
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
        }

        # Complex tables empty
        for _ in range(6):
            mock_get_data.return_value.update({"some_complex": []})

        mock_create_config.return_value = 10
        mock_create_version.return_value = 20

        config_id, version_id = instantiate_template(
            1, "New Config", {"model_path": "/models/new.gguf"}
        )

        assert config_id == 10
        assert version_id == 20
        # Verify model_loading was saved with substitution
        call_args = mock_save_cat.call_args_list
        model_call = [c for c in call_args if "model_loading" in str(c)]
        assert len(model_call) == 1
        saved_data = model_call[0][0][2]  # Third arg is data dict
        assert saved_data["model_path"] == "/models/new.gguf"

    @patch("models.templates.get_template")
    def test_instantiate_no_template(self, mock_get_template):
        from models.templates import instantiate_template

        mock_get_template.return_value = None
        config_id, version_id = instantiate_template(999, "Test", {})
        assert config_id is None
        assert version_id is None


class TestInstantiateNoVariables:
    @patch("models.templates.save_complex_table")
    @patch("models.templates.save_category")
    @patch("models.templates.create_version")
    @patch("models.templates.create_config")
    @patch("models.templates.get_all_version_data")
    @patch("models.templates.get_template")
    def test_no_variables_static_copy(
        self, mock_get_template, mock_get_data, mock_create_config,
        mock_create_version, mock_save_cat, mock_save_complex
    ):
        """Template with no variables creates exact copy."""
        from models.templates import instantiate_template

        mock_get_template.return_value = MockDictRow({
            "id": 1,
            "source_version_id": 42,
        })
        mock_get_data.return_value = {
            "model_loading": {"version_id": 42, "model_path": "/models/fixed.gguf"},
            "context_batching": {"version_id": 42, "ctx_size": 4096},
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
        }
        mock_create_config.return_value = 10
        mock_create_version.return_value = 20

        config_id, version_id = instantiate_template(1, "Static Config", {})

        assert config_id == 10
        # Check no substitution happened
        call_args = mock_save_cat.call_args_list
        model_call = [c for c in call_args if "model_loading" in str(c)]
        saved_data = model_call[0][0][2]
        assert saved_data["model_path"] == "/models/fixed.gguf"


class TestSuggestedVariables:
    def test_suggests_model_path(self):
        from routes.configs import _get_suggested_variables

        data = {
            "model_loading": {"model_path": "/models/test-7b.gguf"},
            "context_batching": {},
            "gpu_device": {},
        }
        result = _get_suggested_variables(data)

        assert any(v["variable_name"] == "model_path" for v in result)
        model_var = next(v for v in result if v["variable_name"] == "model_path")
        assert model_var["default_value"] == "/models/test-7b.gguf"

    def test_suggests_ctx_size(self):
        from routes.configs import _get_suggested_variables

        data = {
            "model_loading": {},
            "context_batching": {"ctx_size": 8192},
            "gpu_device": {},
        }
        result = _get_suggested_variables(data)

        assert any(v["variable_name"] == "ctx_size" for v in result)

    def test_suggests_gpu_layers(self):
        from routes.configs import _get_suggested_variables

        data = {
            "model_loading": {},
            "context_batching": {},
            "gpu_device": {"gpu_layers": "-1"},
        }
        result = _get_suggested_variables(data)

        assert any(v["variable_name"] == "gpu_layers" for v in result)

    def test_no_suggestions_empty_data(self):
        from routes.configs import _get_suggested_variables

        data = {"model_loading": {}, "context_batching": {}, "gpu_device": {}}
        result = _get_suggested_variables(data)
        assert len(result) == 0


class TestVariableSubstitutionComplexTables:
    @patch("models.templates.save_complex_table")
    @patch("models.templates.save_category")
    @patch("models.templates.create_version")
    @patch("models.templates.create_config")
    @patch("models.templates.get_all_version_data")
    @patch("models.templates.get_template")
    def test_substitutes_in_lora_paths(
        self, mock_get_template, mock_get_data, mock_create_config,
        mock_create_version, mock_save_cat, mock_save_complex
    ):
        """Variable substitution works in complex table rows."""
        from models.templates import instantiate_template

        mock_get_template.return_value = MockDictRow({
            "id": 1,
            "source_version_id": 42,
        })
        mock_get_data.return_value = {
            "model_loading": {"version_id": 42, "model_path": "{{model_path}}"},
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
            "lora_adapters": [
                {"id": 1, "version_id": 42, "path": "{{model_path}}/adapter", "scale": 0.8},
            ],
        }
        mock_create_config.return_value = 10
        mock_create_version.return_value = 20

        instantiate_template(1, "Test", {"model_path": "/models/new"})

        # Check lora_adapters was saved with substitution
        mock_save_complex.assert_called_once()
        _, tbl_name, rows = mock_save_complex.call_args[0]
        assert tbl_name == "lora_adapters"
        assert rows[0]["path"] == "/models/new/adapter"
