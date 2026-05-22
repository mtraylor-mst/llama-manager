"""Jinja2 template utility functions for rendering form fields."""

from html import escape as hescape

# Field definitions: category -> list of (column, label, field_type, options/hint)
CATEGORY_FIELDS = {
    "model_loading": [
        ("model_path", "Model Path", "text", "Path to .gguf file"),
        ("model_url", "Model URL", "text", None),
        ("hf_repo", "HF Repo", "text", "user/model:quant"),
        ("hf_file", "HF File", "text", None),
        ("hf_token", "HF Token", "password", None),
        ("aliases", "Aliases", "text", "comma-separated"),
        ("tags", "Tags", "text", "comma-separated"),
        ("mmproj_path", "MMProj Path", "text", None),
        ("mmproj_auto", "Auto MMProj", "tristate", None),
        ("mmproj_offload", "Offload MMProj", "tristate", None),
    ],
    "context_batching": [
        ("ctx_size", "Context Size", "int", "0 = from model"),
        ("n_predict", "Max Predictions", "int", "-1 = infinite"),
        ("batch_size", "Batch Size", "int", "default: 2048"),
        ("ubatch_size", "U-Batch Size", "int", "default: 512"),
        ("keep_tokens", "Keep Tokens", "int", "0 or -1 = all"),
        ("n_parallel", "Parallel Slots", "int", "-1 = auto"),
        ("cont_batching", "Continuous Batching", "tristate", None),
        ("cache_prompt", "Cache Prompts", "tristate", None),
        ("cache_reuse", "Cache Reuse Min", "int", "0 = disabled"),
        ("slot_prompt_similarity", "Slot Prompt Similarity", "float", "0.0 = disabled"),
    ],
    "cpu_threading": [
        ("threads", "Threads (Gen)", "int", "-1 = default"),
        ("threads_batch", "Threads (Batch)", "int", "same as --threads"),
        (
            "prio",
            "Priority",
            "select",
            [
                ("0", "normal"),
                ("-1", "low"),
                ("1", "medium"),
                ("2", "high"),
                ("3", "realtime"),
            ],
        ),
        ("poll", "Poll Level", "int", "0-100, default: 50"),
        (
            "numa",
            "NUMA Mode",
            "select",
            [
                ("none", "none"),
                ("distribute", "distribute"),
                ("isolate", "isolate"),
                ("numactl", "numactl"),
            ],
        ),
        ("cpu_strict", "Strict CPU Placement", "bool", None),
        ("threads_draft", "Threads (Draft)", "int", None),
        ("threads_batch_draft", "Threads Batch (Draft)", "int", None),
    ],
    "gpu_device": [
        ("gpu_layers", "GPU Layers", "text", "N, auto, or all"),
        ("devices", "Devices", "text", "dev1,dev2,..."),
        (
            "split_mode",
            "Split Mode",
            "select",
            [
                ("none", "none"),
                ("layer", "layer"),
                ("row", "row"),
                ("tensor", "tensor"),
            ],
        ),
        ("tensor_split", "Tensor Split", "text", "e.g. 3,1"),
        ("main_gpu", "Main GPU", "int", "default: 0"),
        (
            "flash_attn",
            "Flash Attention",
            "select",
            [("auto", "auto"), ("on", "on"), ("off", "off")],
        ),
        ("kv_offload", "KV Offload", "tristate", None),
        ("repack", "Weight Repack", "tristate", None),
        ("fit", "Auto Fit", "select", [("on", "on"), ("off", "off")]),
        ("fit_target", "Fit Target (MiB)", "text", "per-device margin"),
        ("fit_ctx", "Fit Min Context", "int", "default: 4096"),
        ("op_offload", "Op Offload", "tristate", None),
        ("cpu_moe", "CPU MoE", "bool", None),
    ],
    "memory": [
        (
            "cache_type_k",
            "KV Cache Type K",
            "select",
            [
                ("f32", "f32"),
                ("f16", "f16"),
                ("bf16", "bf16"),
                ("q8_0", "q8_0"),
                ("q4_0", "q4_0"),
            ],
        ),
        (
            "cache_type_v",
            "KV Cache Type V",
            "select",
            [
                ("f32", "f32"),
                ("f16", "f16"),
                ("bf16", "bf16"),
                ("q8_0", "q8_0"),
                ("q4_0", "q4_0"),
            ],
        ),
        ("mmap", "Memory Map", "tristate", None),
        ("mlock", "Lock Memory", "bool", None),
        ("direct_io", "Direct I/O", "tristate", None),
    ],
    "sampling": [
        ("seed", "Seed", "int", "-1 = random"),
        ("temperature", "Temperature", "float", "default: 0.80"),
        ("top_k", "Top-K", "int", "0 = disabled"),
        ("top_p", "Top-P", "float", "1.0 = disabled"),
        ("min_p", "Min-P", "float", "0.0 = disabled"),
        ("typical_p", "Typical P", "float", "1.0 = disabled"),
        ("repeat_last_n", "Repeat Last N", "int", "-1 = ctx_size"),
        ("repeat_penalty", "Repeat Penalty", "float", "1.0 = disabled"),
        ("presence_penalty", "Presence Penalty", "float", "0.0 = disabled"),
        ("frequency_penalty", "Frequency Penalty", "float", "0.0 = disabled"),
        (
            "mirostat",
            "Mirostat",
            "select",
            [("0", "disabled"), ("1", "Mirostat"), ("2", "Mirostat 2.0")],
        ),
        ("mirostat_lr", "Mirostat LR", "float", "default: 0.10"),
        ("mirostat_ent", "Mirostat Entropy", "float", "default: 5.00"),
        ("dynatemp_range", "Dynamic Temp Range", "float", "0.0 = disabled"),
        ("xtc_probability", "XTC Probability", "float", "0.0 = disabled"),
        ("xtc_threshold", "XTC Threshold", "float", "1.0 = disabled"),
        ("ignore_eos", "Ignore EOS", "bool", None),
    ],
    "server": [
        ("host", "Host", "text", "default: 127.0.0.1"),
        ("port", "Port", "int", "default: 8080"),
        ("timeout", "Timeout (sec)", "int", "default: 600"),
        ("threads_http", "HTTP Threads", "int", "-1 = default"),
        ("webui", "Web UI", "tristate", None),
        ("metrics", "Prometheus Metrics", "bool", None),
        ("slots", "Slots Endpoint", "tristate", None),
        ("embedding", "Embeddings Only", "bool", None),
        ("reranking", "Reranking", "bool", None),
        ("api_key", "API Key", "password", None),
        ("sleep_idle_seconds", "Sleep Idle (sec)", "int", "-1 = disabled"),
    ],
    "speculative": [
        ("draft_max", "Draft Max Tokens", "int", "default: 16"),
        ("draft_min", "Draft Min Tokens", "int", "default: 0"),
        ("draft_p_min", "Draft P Min", "float", "default: 0.75"),
        ("ctx_size_draft", "Draft Context Size", "int", None),
        (
            "spec_type",
            "Spec Type",
            "select",
            [
                ("none", "none"),
                ("ngram-cache", "ngram-cache"),
                ("ngram-simple", "ngram-simple"),
                ("ngram-map-k", "ngram-map-k"),
                ("draft-mtp", "draft-mtp (MTP)"),
            ],
        ),
        ("spec_ngram_size_n", "Ngram Size N", "int", "default: 12"),
        ("spec_ngram_size_m", "Ngram Size M", "int", "default: 48"),
        ("spec_draft_n_max", "Draft N Max", "int", None),
    ],
    "chat_templates": [
        (
            "chat_template",
            "Chat Template",
            "select",
            [
                ("auto", "auto (from model)"),
                ("chatml", "chatml"),
                ("llama3", "llama3"),
                ("mistral-v3", "mistral-v3"),
                ("deepseek", "deepseek"),
                ("gemma", "gemma"),
                ("phi3", "phi3"),
            ],
        ),
        (
            "chat_template_kwargs",
            "Chat Template Kwargs",
            "text",
            'JSON string, e.g. {"preserve_thinking":true}',
        ),
        ("jinja", "Use Jinja", "tristate", None),
        (
            "reasoning",
            "Reasoning",
            "select",
            [("auto", "auto"), ("on", "on"), ("off", "off")],
        ),
        (
            "reasoning_format",
            "Reasoning Format",
            "select",
            [("auto", "auto"), ("none", "none"), ("deepseek", "deepseek")],
        ),
        ("reasoning_budget", "Reasoning Budget", "int", "-1 = unrestricted"),
        ("skip_chat_parsing", "Skip Chat Parsing", "tristate", None),
        ("prefill_assistant", "Prefill Assistant", "tristate", None),
    ],
    "checkpoints": [
        ("ctx_checkpoints", "Context Checkpoints", "int", "default: 32"),
        ("cache_ram", "Cache RAM (MiB)", "int", "-1 = no limit"),
        ("kv_unified", "Unified KV Buffer", "tristate", None),
        ("cache_idle_slots", "Cache Idle Slots", "tristate", None),
    ],
    "logging": [
        (
            "log_verbosity",
            "Verbosity",
            "select",
            [
                ("0", "generic"),
                ("1", "error"),
                ("2", "warning"),
                ("3", "info"),
                ("4", "debug"),
            ],
        ),
        ("log_file", "Log File", "text", None),
        (
            "log_colors",
            "Log Colors",
            "select",
            [("auto", "auto"), ("on", "on"), ("off", "off")],
        ),
        ("log_timestamps", "Timestamps", "bool", None),
        ("verbose", "Verbose (All)", "bool", None),
        ("offline", "Offline Mode", "bool", None),
    ],
    "advanced": [
        (
            "rope_scaling",
            "RoPE Scaling",
            "select",
            [("none", "none"), ("linear", "linear"), ("yarn", "yarn")],
        ),
        ("rope_scale", "RoPE Scale", "float", None),
        ("rope_freq_base", "RoPE Freq Base", "float", None),
        ("rope_freq_scale", "RoPE Freq Scale", "float", None),
        ("yarn_orig_ctx", "YaRN Orig Ctx", "int", None),
        ("yarn_ext_factor", "YaRN Ext Factor", "float", None),
        ("yarn_attn_factor", "YaRN Attn Factor", "float", None),
        ("grammar_file", "Grammar File", "text", None),
        ("json_schema_file", "JSON Schema File", "text", None),
    ],
}

COMPLEX_LABELS = {
    "logit_biases": "Logit Biases",
    "lora_adapters": "LoRA Adapters",
    "control_vectors": "Control Vectors",
    "override_kv": "Override KV",
    "override_tensors": "Override Tensors",
    "dry_sequence_breakers": "DRY Sequence Breakers",
}

COMPLEX_FIELDS = {
    "logit_biases": [("token_id", "Token ID", "int"), ("bias_value", "Bias", "float")],
    "lora_adapters": [("path", "Path", "text"), ("scale", "Scale", "float")],
    "control_vectors": [
        ("path", "Path", "text"),
        ("scale", "Scale", "float"),
        ("layer_range_start", "Layer Start", "int"),
        ("layer_range_end", "Layer End", "int"),
    ],
    "override_kv": [
        ("key_name", "Key", "text"),
        (
            "key_type",
            "Type",
            "select",
            [("int", "int"), ("float", "float"), ("bool", "bool"), ("str", "str")],
        ),
        ("key_value", "Value", "text"),
    ],
    "override_tensors": [
        ("tensor_pattern", "Pattern", "text"),
        ("buffer_type", "Buffer Type", "text"),
    ],
    "dry_sequence_breakers": [("breaker_char", "Char", "text")],
}


def category_fields(category):
    """Return list of (col, label) for a category."""
    fields = CATEGORY_FIELDS.get(category, [])
    return [(f[0], f[1]) for f in fields]


def render_field(category, col, value):
    """Render an HTML input for a field."""
    fields = CATEGORY_FIELDS.get(category, [])
    field_def = next((f for f in fields if f[0] == col), None)
    if not field_def:
        return f'<input type="text" name="{category}_{col}" value="{hescape(str(value) if value else "", quote=True)}">'

    _, _, ftype, hint = field_def
    name = f"{category}_{col}"

    if ftype == "bool":
        if value == 1 or value is True:
            return f'<input type="checkbox" name="{name}" value="1" checked>'
        return f'<input type="checkbox" name="{name}" value="1">'

    elif ftype == "tristate":
        v = str(value) if value is not None else ""
        opts = [
            ("", "(default)"),
            ("enable", "Enable"),
            ("disable", "Disable"),
        ]
        html = f'<select name="{name}">\n'
        for opt_val, opt_label in opts:
            sel = (
                "selected"
                if v == opt_val
                or (opt_val == "enable" and value in (1, True))
                or (opt_val == "disable" and value in (0, False))
                else ""
            )
            html += f'<option value="{opt_val}" {sel}>{opt_label}</option>\n'
        html += "</select>"
        return html

    elif ftype == "select":
        options = field_def[3]
        html = f'<select name="{name}">\n<option value="">(default)</option>\n'
        for opt_val, opt_label in options:
            sel = "selected" if str(value) == str(opt_val) else ""
            html += f'<option value="{hescape(str(opt_val), quote=True)}" {sel}>{opt_label}</option>\n'
        html += "</select>"
        return html

    elif ftype == "password":
        escaped_value = hescape(str(value) if value else "", quote=True)
        placeholder = 'placeholder="••••••"' if value else ""
        return (
            f'<input type="hidden" name="{name}" value="{escaped_value}">'
            f'<input type="password" name="__{name}" value="" {placeholder}>'
        )

    else:
        val = hescape(str(value) if value is not None else "", quote=True)
        ftype_html = "text" if ftype in ("text",) else ftype
        return f'<input type="{ftype_html}" name="{name}" value="{val}">'


def complex_label(tbl):
    return COMPLEX_LABELS.get(tbl, tbl)


def render_complex(tbl, rows):
    """Render complex value rows (logit_biases, etc.)."""
    fields = COMPLEX_FIELDS.get(tbl, [])
    if not rows:
        return '<p class="empty">None configured</p>'

    html = '<table class="complex-table">\n<thead><tr>'
    for _, label, _ in fields:
        html += f"<th>{label}</th>"
    html += "</tr></thead>\n<tbody>\n"

    for i, row in enumerate(rows):
        html += f'<tr data-row="{i}">'
        for col, _, ftype in fields:
            val = hescape(str(row.get(col, "") or ""), quote=True)
            html += f'<td><input type="text" name="{tbl}_{i}_{col}" value="{val}"></td>'
        html += "</tr>\n"

    html += "</tbody></table>"
    return html


def register_template_helpers(app):
    """Register Jinja2 globals for template helpers."""
    app.jinja_env.globals["category_fields"] = category_fields
    app.jinja_env.globals["render_field"] = render_field
    app.jinja_env.globals["complex_label"] = complex_label
    app.jinja_env.globals["render_complex"] = render_complex
