from template_utils import (
    category_fields,
    render_field,
    complex_label,
    render_complex,
    register_template_helpers,
)


class TestCategoryFields:
    def test_known_category(self):
        fields = category_fields("model_loading")
        assert len(fields) > 0
        assert ("model_path", "Model Path") in fields

    def test_unknown_category(self):
        fields = category_fields("nonexistent")
        assert fields == []


class TestRenderField:
    def test_text_field(self):
        html = render_field("model_loading", "model_path", "/path/to/model.gguf")
        assert 'type="text"' in html
        assert "/path/to/model.gguf" in html

    def test_bool_checked(self):
        html = render_field("memory", "mlock", 1)
        assert "checked" in html
        assert 'type="checkbox"' in html

    def test_bool_unchecked(self):
        html = render_field("memory", "mlock", 0)
        assert "checked" not in html
        assert 'type="checkbox"' in html

    def test_tristate_enabled(self):
        html = render_field("memory", "mmap", 1)
        assert "<select" in html
        assert 'value="enable" selected' in html

    def test_tristate_disabled(self):
        html = render_field("memory", "mmap", 0)
        assert "<select" in html
        assert 'value="disable" selected' in html

    def test_tristate_default(self):
        html = render_field("memory", "mmap", None)
        assert "<select" in html
        assert 'value="" selected' in html

    def test_select_field(self):
        html = render_field("cpu_threading", "prio", "2")
        assert "<select" in html
        assert 'value="2" selected' in html

    def test_int_field(self):
        html = render_field("context_batching", "ctx_size", "4096")
        assert 'type="int"' in html
        assert 'value="4096"' in html

    def test_unknown_field_fallback(self):
        html = render_field("model_loading", "unknown_col", "testval")
        assert 'type="text"' in html
        assert 'value="testval"' in html

    def test_html_escaping(self):
        html = render_field("model_loading", "model_path", "<script>alert(1)</script>")
        assert "<script>" not in html
        assert "&lt;script&gt;" in html


class TestComplexLabel:
    def test_known_table(self):
        assert complex_label("logit_biases") == "Logit Biases"

    def test_unknown_table_passthrough(self):
        assert complex_label("unknown_table") == "unknown_table"


class TestRenderComplex:
    def test_empty_rows(self):
        html = render_complex("lora_adapters", [])
        assert "None configured" in html

    def test_with_rows(self):
        rows = [{"path": "/path/to/lora.gguf", "scale": 0.5}]
        html = render_complex("lora_adapters", rows)
        assert "<table" in html
        assert 'value="/path/to/lora.gguf"' in html

    def test_multiple_rows(self):
        rows = [
            {"path": "/lora1.gguf", "scale": 0.5},
            {"path": "/lora2.gguf", "scale": 0.8},
            {"path": "/lora3.gguf", "scale": 1.0},
        ]
        html = render_complex("lora_adapters", rows)
        assert html.count('<tr data-row="0">') == 1
        assert html.count('<tr data-row="1">') == 1
        assert html.count('<tr data-row="2">') == 1
        assert html.count("</tr>") == 4  # 3 data rows + 1 header row

    def test_unknown_table_type(self):
        rows = [{"col1": "val1"}]
        html = render_complex("unknown_table", rows)
        assert "<table" in html
        assert html.count("<th>") == 0  # No field definitions for unknown table


class TestPasswordField:
    def test_password_field_with_value(self):
        html = render_field("server", "api_key", "mysecret123")
        assert 'type="password"' in html
        assert 'type="hidden"' in html
        # Secret is only in hidden field, not visible password input
        assert 'name="server_api_key" value="mysecret123">' in html
        assert 'name="__server_api_key" value=""' in html
        assert 'placeholder="••••••"' in html

    def test_password_field_empty(self):
        html = render_field("server", "api_key", "")
        assert 'type="password"' in html
        assert 'type="hidden"' in html
        assert "placeholder=" not in html

    def test_password_field_none(self):
        html = render_field("server", "api_key", None)
        assert 'type="password"' in html
        assert 'type="hidden"' in html


class TestBoolWithPythonTrue:
    def test_bool_python_true(self):
        html = render_field("memory", "mlock", True)
        assert "checked" in html
        assert 'type="checkbox"' in html


class TestSelectDefault:
    def test_select_no_matching_value(self):
        html = render_field("cpu_threading", "prio", "99")
        assert "<select" in html
        assert 'value="" selected' not in html
        assert '<option value="">(default)</option>' in html


class TestRegisterTemplateHelpers:
    def test_registers_all_functions(self):
        from app import create_app

        app = create_app()
        app.config["TESTING"] = True
        register_template_helpers(app)

        assert app.jinja_env.globals["category_fields"] == category_fields
        assert app.jinja_env.globals["render_field"] == render_field
        assert app.jinja_env.globals["complex_label"] == complex_label
        assert app.jinja_env.globals["render_complex"] == render_complex
