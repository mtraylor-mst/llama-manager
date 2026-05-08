from template_utils import (
    category_fields,
    render_field,
    complex_label,
    render_complex,
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
