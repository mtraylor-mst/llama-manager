from config import SERVER_BINARY


def int_bool(v):
    return int(bool(v)) if v is not None else None


def neg_bool(v):
    return 1 if v else (0 if v is not None else None)


def float_fmt(v):
    if v is None:
        return None
    s = f"{v:f}".rstrip("0").rstrip(".")
    return s if "." in s or v == int(v) else f"{v:.4f}"


# Maps category -> flag definitions: (short_flag, long_flag, is_bool, format_func)
FLAG_DEFINITIONS = {
    "model_loading": [
        ("-m", "--model", False, None),
        ("--model-url", None, False, None),
        ("--hf-repo", "-hfr", False, None),
        ("--hf-file", "-hff", False, None),
        ("--hf-token", "-hft", False, None),
        ("--lora", None, False, None),
        ("--control-vector", None, False, None),
        ("--mmproj", "-mm", False, None),
        ("--mmproj-url", "-mmu", False, None),
        ("--mmproj-auto/--no-mmproj", None, True, None),
        ("--mmproj-offload/--no-mmproj-offload", None, True, None),
        ("-a", "--alias", False, None),
        ("--tags", None, False, None),
    ],
    "context_batching": [
        ("-c", "--ctx-size", False, None),
        ("-n", "--n-predict", False, None),
        ("-b", "--batch-size", False, None),
        ("-ub", "--ubatch-size", False, None),
        ("--keep", None, False, None),
        ("-np", "--parallel", False, None),
        ("--cont-batching/--no-cont-batching", "-cb/-nocb", True, None),
        ("--context-shift/--no-context-shift", None, True, None),
        ("-r", "--reverse-prompt", False, None),
        ("--special", None, True, None),
        ("--warmup/--no-warmup", None, True, None),
        ("--spm-infill", None, True, None),
        ("--pooling", None, False, None),
        ("--cache-prompt/--no-cache-prompt", None, True, None),
        ("--cache-reuse", None, False, None),
        ("-sps", "--slot-prompt-similarity", False, None),
    ],
    "cpu_threading": [
        ("-t", "--threads", False, None),
        ("-tb", "--threads-batch", False, None),
        ("-C", "--cpu-mask", False, None),
        ("-Cr", "--cpu-range", False, None),
        ("--cpu-strict", None, True, None),
        ("--prio", None, False, None),
        ("--poll", None, False, None),
        ("-Cb", "--cpu-mask-batch", False, None),
        ("-Crb", "--cpu-range-batch", False, None),
        ("--cpu-strict-batch", None, True, None),
        ("--prio-batch", None, False, None),
        ("--poll-batch", None, True, None),
        ("--numa", None, False, None),
        ("-td", "--threads-draft", False, None),
        ("-tbd", "--threads-batch-draft", False, None),
    ],
    "gpu_device": [
        ("-ngl", "--gpu-layers", False, None),
        ("--device", "-dev", False, None),
        ("-sm", "--split-mode", False, None),
        ("-ts", "--tensor-split", False, None),
        ("-mg", "--main-gpu", False, None),
        ("-fa", "--flash-attn", False, None),
        ("--kv-offload/--no-kv-offload", "-kvo/-nkvo", True, None),
        ("--repack/--no-repack", "-nr", True, None),
        ("--no-host", None, True, neg_bool),
        ("--fit", None, False, None),
        ("-fitt", "--fit-target", False, None),
        ("-fitc", "--fit-ctx", False, None),
        ("--op-offload/--no-op-offload", None, True, None),
        ("--cpu-moe", "-cmoe", True, None),
        ("-ncmoe", "--n-cpu-moe", False, None),
        ("--cpu-moe-draft", "-cmoed", True, None),
        ("-ncmoed", "--n-cpu-moe-draft", False, None),
    ],
    "memory": [
        ("-ctk", "--cache-type-k", False, None),
        ("-ctv", "--cache-type-v", False, None),
        ("-ctkd", "--cache-type-k-draft", False, None),
        ("-ctvd", "--cache-type-v-draft", False, None),
        ("--mmap/--no-mmap", None, True, None),
        ("--mlock", None, True, None),
        ("--direct-io/--no-direct-io", "-dio/-ndio", True, None),
        ("-dt", "--defrag-thold", False, None),
        ("--swa-full", None, True, None),
    ],
    "sampling": [
        ("--samplers", None, False, None),
        ("--sampler-seq", "--sampling-seq", False, None),
        ("-s", "--seed", False, None),
        ("--ignore-eos", None, True, None),
        ("--temp", "--temperature", False, float_fmt),
        ("--top-k", None, False, None),
        ("--top-p", None, False, float_fmt),
        ("--min-p", None, False, float_fmt),
        ("--top-nsigma", "--top-n-sigma", False, float_fmt),
        ("--xtc-probability", None, False, float_fmt),
        ("--xtc-threshold", None, False, float_fmt),
        ("--typical", "--typical-p", False, float_fmt),
        ("--repeat-last-n", None, False, None),
        ("--repeat-penalty", None, False, float_fmt),
        ("--presence-penalty", None, False, float_fmt),
        ("--frequency-penalty", None, False, float_fmt),
        ("--dry-multiplier", None, False, float_fmt),
        ("--dry-base", None, False, float_fmt),
        ("--dry-allowed-length", None, False, None),
        ("--dry-penalty-last-n", None, False, None),
        ("--adaptive-target", None, False, float_fmt),
        ("--adaptive-decay", None, False, float_fmt),
        ("--dynatemp-range", None, False, float_fmt),
        ("--dynatemp-exp", None, False, float_fmt),
        ("--mirostat", None, False, None),
        ("--mirostat-lr", None, False, float_fmt),
        ("--mirostat-ent", None, False, float_fmt),
        ("--backend-sampling", "-bs", True, None),
    ],
    "server": [
        ("--host", None, False, None),
        ("--port", None, False, None),
        ("--reuse-port", None, True, None),
        ("--path", None, False, None),
        ("--api-prefix", None, False, None),
        ("-to", "--timeout", False, None),
        ("--threads-http", None, False, None),
        ("--api-key", None, False, None),
        ("--ssl-key-file", None, False, None),
        ("--ssl-cert-file", None, False, None),
        ("--webui/--no-webui", None, True, None),
        ("--embedding", "--embeddings", True, None),
        ("--rerank", "--reranking", True, None),
        ("--metrics", None, True, None),
        ("--props", None, True, None),
        ("--slots/--no-slots", None, True, None),
        ("--slot-save-path", None, False, None),
        ("--media-path", None, False, None),
        ("--lora-init-without-apply", None, True, None),
        ("--sleep-idle-seconds", None, False, None),
    ],
    "speculative": [
        ("-md", "--model-draft", False, None),
        ("--draft", "--draft-max", False, None),
        ("--draft-min", "--draft-n-min", False, None),
        ("--draft-p-min", None, False, float_fmt),
        ("-cd", "--ctx-size-draft", False, None),
        ("-devd", "--device-draft", False, None),
        ("-ngld", "--gpu-layers-draft", False, None),
        ("--spec-type", None, False, None),
        ("--spec-ngram-size-n", None, False, None),
        ("--spec-ngram-size-m", None, False, None),
        ("--spec-ngram-min-hits", None, False, None),
        ("--spec-draft-n-max", None, False, None),
        ("--spec-replace", None, False, None),
        ("-otd", "--override-tensor-draft", False, None),
    ],
    "chat_templates": [
        ("--chat-template", None, False, None),
        ("--chat-template-file", None, False, None),
        ("--chat-template-kwargs", None, False, None),
        ("--jinja/--no-jinja", None, True, None),
        ("--reasoning-format", None, False, None),
        ("-rea", "--reasoning", False, None),
        ("--reasoning-budget", None, False, None),
        ("--reasoning-budget-message", None, False, None),
        ("--skip-chat-parsing/--no-skip-chat-parsing", None, True, None),
        ("--prefill-assistant/--no-prefill-assistant", None, True, None),
    ],
    "checkpoints": [
        ("-ctxcp", "--ctx-checkpoints", False, None),
        ("-cpent", "--checkpoint-every-n-tokens", False, None),
        ("-cram", "--cache-ram", False, None),
        ("--kv-unified/--no-kv-unified", "-kvu/-no-kvu", True, None),
        ("--cache-idle-slots/--no-cache-idle-slots", None, True, None),
        ("-lcs", "--lookup-cache-static", False, None),
        ("-lcd", "--lookup-cache-dynamic", False, None),
    ],
    "logging": [
        ("-lv", "--log-verbosity", False, None),
        ("--log-file", None, False, None),
        ("--log-colors", None, False, None),
        ("--log-prefix", None, True, None),
        ("--log-timestamps", None, True, None),
        ("-v", "--verbose/--log-verbose", True, None),
        ("--log-disable", None, True, None),
        ("--offline", None, True, None),
        ("--perf/--no-perf", None, True, None),
        ("-e", "--escape/--no-escape", True, None),
    ],
    "advanced": [
        ("--rope-scaling", None, False, None),
        ("--rope-scale", None, False, float_fmt),
        ("--rope-freq-base", None, False, float_fmt),
        ("--rope-freq-scale", None, False, float_fmt),
        ("--yarn-orig-ctx", None, False, None),
        ("--yarn-ext-factor", None, False, float_fmt),
        ("--yarn-attn-factor", None, False, float_fmt),
        ("--yarn-beta-slow", None, False, float_fmt),
        ("--yarn-beta-fast", None, False, float_fmt),
        ("--grammar", None, False, None),
        ("--grammar-file", None, False, None),
        ("-j", "--json-schema", False, None),
        ("-jf", "--json-schema-file", False, None),
        ("--check-tensors", None, True, None),
        ("--image-min-tokens", None, False, None),
        ("--image-max-tokens", None, False, None),
    ],
}

# Column name -> flag field mapping per category
COLUMN_MAP = {
    "model_loading": {
        "model_path": "--model",
        "model_url": "--model-url",
        "hf_repo": "--hf-repo",
        "hf_file": "--hf-file",
        "hf_token": "--hf-token",
        "mmproj_path": "--mmproj",
        "mmproj_url": "--mmproj-url",
        "mmproj_auto": "--mmproj-auto/--no-mmproj",
        "mmproj_offload": "--mmproj-offload/--no-mmproj-offload",
        "aliases": "--alias",
        "tags": "--tags",
    },
    "context_batching": {
        "ctx_size": "--ctx-size",
        "n_predict": "--n-predict",
        "batch_size": "--batch-size",
        "ubatch_size": "--ubatch-size",
        "keep_tokens": "--keep",
        "n_parallel": "--parallel",
        "cont_batching": "--cont-batching/--no-cont-batching",
        "context_shift": "--context-shift",
        "reverse_prompt": "--reverse-prompt",
        "special_tokens": "--special",
        "warmup": "--warmup",
        "spm_infill": "--spm-infill",
        "pooling": "--pooling",
        "cache_prompt": "--cache-prompt/--no-cache-prompt",
        "cache_reuse": "--cache-reuse",
        "slot_prompt_similarity": "--slot-prompt-similarity",
    },
    "cpu_threading": {
        "threads": "--threads",
        "threads_batch": "--threads-batch",
        "cpu_mask": "--cpu-mask",
        "cpu_range": "--cpu-range",
        "cpu_strict": "--cpu-strict",
        "prio": "--prio",
        "poll": "--poll",
        "cpu_mask_batch": "--cpu-mask-batch",
        "cpu_range_batch": "--cpu-range-batch",
        "cpu_strict_batch": "--cpu-strict-batch",
        "prio_batch": "--prio-batch",
        "poll_batch": "--poll-batch",
        "numa": "--numa",
        "threads_draft": "--threads-draft",
        "threads_batch_draft": "--threads-batch-draft",
    },
    "gpu_device": {
        "gpu_layers": "--gpu-layers",
        "devices": "--device",
        "split_mode": "--split-mode",
        "tensor_split": "--tensor-split",
        "main_gpu": "--main-gpu",
        "flash_attn": "--flash-attn",
        "kv_offload": "--kv-offload/--no-kv-offload",
        "repack": "--repack/--no-repack",
        "no_host": "--no-host",
        "fit": "--fit",
        "fit_target": "--fit-target",
        "fit_ctx": "--fit-ctx",
        "op_offload": "--op-offload/--no-op-offload",
        "cpu_moe": "--cpu-moe",
        "n_cpu_moe": "--n-cpu-moe",
        "cpu_moe_draft": "--cpu-moe-draft",
        "n_cpu_moe_draft": "--n-cpu-moe-draft",
    },
    "memory": {
        "cache_type_k": "--cache-type-k",
        "cache_type_v": "--cache-type-v",
        "cache_type_k_draft": "--cache-type-k-draft",
        "cache_type_v_draft": "--cache-type-v-draft",
        "mmap": "--mmap/--no-mmap",
        "mlock": "--mlock",
        "direct_io": "--direct-io/--no-direct-io",
        "defrag_thold": "--defrag-thold",
        "swa_full": "--swa-full",
    },
    "sampling": {
        "samplers": "--samplers",
        "sampler_seq": "--sampler-seq",
        "seed": "--seed",
        "ignore_eos": "--ignore-eos",
        "temperature": "--temperature",
        "top_k": "--top-k",
        "top_p": "--top-p",
        "min_p": "--min-p",
        "top_n_sigma": "--top-n-sigma",
        "xtc_probability": "--xtc-probability",
        "xtc_threshold": "--xtc-threshold",
        "typical_p": "--typical-p",
        "repeat_last_n": "--repeat-last-n",
        "repeat_penalty": "--repeat-penalty",
        "presence_penalty": "--presence-penalty",
        "frequency_penalty": "--frequency-penalty",
        "dry_multiplier": "--dry-multiplier",
        "dry_base": "--dry-base",
        "dry_allowed_length": "--dry-allowed-length",
        "dry_penalty_last_n": "--dry-penalty-last-n",
        "adaptive_target": "--adaptive-target",
        "adaptive_decay": "--adaptive-decay",
        "dynatemp_range": "--dynatemp-range",
        "dynatemp_exp": "--dynatemp-exp",
        "mirostat": "--mirostat",
        "mirostat_lr": "--mirostat-lr",
        "mirostat_ent": "--mirostat-ent",
        "backend_sampling": "--backend-sampling",
    },
    "server": {
        "host": "--host",
        "port": "--port",
        "reuse_port": "--reuse-port",
        "static_path": "--path",
        "api_prefix": "--api-prefix",
        "timeout": "--timeout",
        "threads_http": "--threads-http",
        "ssl_key_file": "--ssl-key-file",
        "ssl_cert_file": "--ssl-cert-file",
        "webui": "--webui/--no-webui",
        "embedding": "--embedding",
        "reranking": "--reranking",
        "metrics": "--metrics",
        "props": "--props",
        "slots": "--slots/--no-slots",
        "slot_save_path": "--slot-save-path",
        "media_path": "--media-path",
        "lora_init_without_apply": "--lora-init-without-apply",
        "sleep_idle_seconds": "--sleep-idle-seconds",
    },
    "speculative": {
        "draft_max": "--draft-max",
        "draft_min": "--draft-min",
        "draft_p_min": "--draft-p-min",
        "ctx_size_draft": "--ctx-size-draft",
        "devices_draft": "--device-draft",
        "gpu_layers_draft": "--gpu-layers-draft",
        "spec_type": "--spec-type",
        "spec_ngram_size_n": "--spec-ngram-size-n",
        "spec_ngram_size_m": "--spec-ngram-size-m",
        "spec_ngram_min_hits": "--spec-ngram-min-hits",
        "spec_draft_n_max": "--spec-draft-n-max",
    },
    "chat_templates": {
        "chat_template": "--chat-template",
        "chat_template_file": "--chat-template-file",
        "jinja": "--jinja/--no-jinja",
        "reasoning_format": "--reasoning-format",
        "reasoning": "--reasoning",
        "reasoning_budget": "--reasoning-budget",
        "reasoning_budget_message": "--reasoning-budget-message",
        "skip_chat_parsing": "--skip-chat-parsing/--no-skip-chat-parsing",
        "prefill_assistant": "--prefill-assistant/--no-prefill-assistant",
    },
    "checkpoints": {
        "ctx_checkpoints": "--ctx-checkpoints",
        "checkpoint_every_nt": "--checkpoint-every-n-tokens",
        "cache_ram": "--cache-ram",
        "kv_unified": "--kv-unified/--no-kv-unified",
        "cache_idle_slots": "--cache-idle-slots/--no-cache-idle-slots",
        "lookup_cache_static": "--lookup-cache-static",
        "lookup_cache_dynamic": "--lookup-cache-dynamic",
    },
    "logging": {
        "log_verbosity": "--log-verbosity",
        "log_file": "--log-file",
        "log_colors": "--log-colors",
        "log_prefix": "--log-prefix",
        "log_timestamps": "--log-timestamps",
        "verbose": "--verbose",
        "log_disable": "--log-disable",
        "offline": "--offline",
        "perf": "--perf",
        "escape": "--escape",
    },
    "advanced": {
        "rope_scaling": "--rope-scaling",
        "rope_scale": "--rope-scale",
        "rope_freq_base": "--rope-freq-base",
        "rope_freq_scale": "--rope-freq-scale",
        "yarn_orig_ctx": "--yarn-orig-ctx",
        "yarn_ext_factor": "--yarn-ext-factor",
        "yarn_attn_factor": "--yarn-attn-factor",
        "yarn_beta_slow": "--yarn-beta-slow",
        "yarn_beta_fast": "--yarn-beta-fast",
        "grammar": "--grammar",
        "grammar_file": "--grammar-file",
        "json_schema": "--json-schema",
        "json_schema_file": "--json-schema-file",
        "check_tensors": "--check-tensors",
        "image_min_tokens": "--image-min-tokens",
        "image_max_tokens": "--image-max-tokens",
    },
}

# Fields that are boolean flags (1 = enable flag, 0 = disable/negate flag)
BOOL_FIELDS = {
    "context_batching": {
        "cont_batching",
        "context_shift",
        "special_tokens",
        "warmup",
        "spm_infill",
        "cache_prompt",
    },
    "cpu_threading": {"cpu_strict", "cpu_strict_batch", "poll_batch"},
    "gpu_device": {
        "kv_offload",
        "repack",
        "no_host",
        "op_offload",
        "cpu_moe",
        "cpu_moe_draft",
    },
    "memory": {"mmap", "mlock", "direct_io"},
    "sampling": {"ignore_eos", "backend_sampling"},
    "server": {
        "reuse_port",
        "webui",
        "embedding",
        "reranking",
        "metrics",
        "props",
        "slots",
        "lora_init_without_apply",
    },
    "chat_templates": {"jinja", "skip_chat_parsing", "prefill_assistant"},
    "checkpoints": {"kv_unified", "cache_idle_slots"},
    "logging": {
        "log_prefix",
        "log_timestamps",
        "verbose",
        "log_disable",
        "offline",
        "perf",
        "escape",
    },
}

# Fields that use negation flags (0 means emit --no-xxx)
NEGATIVE_BOOL_FIELDS = {
    "gpu_device": {"no_host"},  # stored as 1=--no-host, so it's already positive
}


def build_command(version_id):
    """Build the full llama-server command line from a version's data."""
    from models.configs import get_all_version_data

    parts = [SERVER_BINARY]
    data = get_all_version_data(version_id)

    for category in [
        "model_loading",
        "context_batching",
        "cpu_threading",
        "gpu_device",
        "memory",
        "sampling",
        "server",
        "speculative",
        "chat_templates",
        "checkpoints",
        "logging",
        "advanced",
    ]:
        row = data.get(category, {})
        col_map = COLUMN_MAP.get(category, {})
        bools = BOOL_FIELDS.get(category, set())

        for col, flag in col_map.items():
            val = row.get(col)
            if val is None:
                continue

            if col in bools:
                if val == 1 or val is True:
                    positive = flag.split("/")[0] if "/" in flag else flag
                    parts.append(positive)
                elif val == 0 or val is False:
                    neg = flag.replace("--no-", "--").replace("/--no-", "/--no-")
                    # For flags like --webui/--no-webui, extract the negative form
                    if "/--no-" in flag:
                        neg = flag.split("/--no-")[1]
                        parts.append(f"--no-{neg}")
                    elif flag.startswith("--no-"):
                        parts.append(flag)
                    else:
                        parts.append(f"--no-{flag.lstrip('-')}")
            else:
                val_str = str(val)
                if val_str:
                    parts.extend([flag, val_str])

    # Model path is special - it comes first after binary
    model = data.get("model_loading", {}).get("model_path")
    if model:
        # Remove any --model already added and put it first
        new_parts = [SERVER_BINARY, "-m", model]
        i = 1
        while i < len(parts):
            p = parts[i]
            if p in ("-m", "--model"):
                i += 2  # skip flag and its value
                continue
            new_parts.append(p)
            i += 1
        parts = new_parts

    # LoRA adapters from structured table
    loras = data.get("lora_adapters", [])
    if loras:
        lora_args = []
        for la in loras:
            if la.get("scale"):
                lora_args.append(f"{la['path']}:{la['scale']}")
            else:
                lora_args.append(la["path"])
        if lora_args:
            parts.extend(["--lora", ",".join(lora_args)])

    # Control vectors from structured table
    cvs = data.get("control_vectors", [])
    for cv in cvs:
        if cv.get("scale"):
            parts.extend(["--control-vector-scaled", f"{cv['path']}:{cv['scale']}"])
        else:
            parts.extend(["--control-vector", cv["path"]])
        if (
            cv.get("layer_range_start") is not None
            and cv.get("layer_range_end") is not None
        ):
            parts.extend(
                [
                    "--control-vector-layer-range",
                    str(cv["layer_range_start"]),
                    str(cv["layer_range_end"]),
                ]
            )

    # Logit biases
    lbs = data.get("logit_biases", [])
    for lb in lbs:
        sign = "+" if lb["bias_value"] >= 0 else "-"
        parts.extend(
            [
                "--logit-bias",
                f"{lb['token_id']}{sign}{abs(lb['bias_value'])}",
            ]
        )

    # Override KV
    oks = data.get("override_kv", [])
    if oks:
        kv_parts = []
        for ok in oks:
            kv_parts.append(f"{ok['key_name']}={ok['key_type']}:{ok['key_value']}")
        if kv_parts:
            parts.extend(["--override-kv", ",".join(kv_parts)])

    # Override tensors (main)
    ots = data.get("override_tensors", [])
    if ots:
        ot_parts = []
        for ot in ots:
            ot_parts.append(f"{ot['tensor_pattern']}={ot['buffer_type']}")
        if ot_parts:
            parts.extend(["--override-tensor", ",".join(ot_parts)])

    # DRY sequence breakers
    dsbs = data.get("dry_sequence_breakers", [])
    for dsb in dsbs:
        parts.extend(["--dry-sequence-breaker", dsb["breaker_char"]])

    # Grammar file vs inline grammar handled by advanced row
    grammar_file = data.get("advanced", {}).get("grammar_file")
    if grammar_file:
        # Remove --grammar if both are set (file takes precedence)
        parts = [p for p in parts if p != "--grammar"]

    # JSON schema file vs inline
    jsf = data.get("advanced", {}).get("json_schema_file")
    if jsf:
        parts.extend(["--json-schema-file", jsf])

    # Draft model
    md = data.get("model_loading", {}).get("model_draft")
    if md:
        parts.extend(["--model-draft", md])

    # Vocoder model
    mv = data.get("model_loading", {}).get("model_vocoder")
    if mv:
        parts.extend(["--model-vocoder", mv])

    # LoRA scaled (from model_loading lora_paths as fallback)
    lora_paths = data.get("model_loading", {}).get("lora_paths")
    if lora_paths and not loras:
        parts.extend(["--lora", lora_paths])

    # API key from server
    api_key = data.get("server", {}).get("api_key")
    if api_key:
        parts.extend(["--api-key", api_key])

    # Chat template kwargs (JSON value — no quoting needed, passed directly to Popen)
    ct_kwargs = data.get("chat_templates", {}).get("chat_template_kwargs")
    if ct_kwargs:
        parts.extend(["--chat-template-kwargs", ct_kwargs])

    # Spec replace
    sr_target = data.get("speculative", {}).get("spec_replace_target")
    sr_draft = data.get("speculative", {}).get("spec_replace_draft")
    if sr_target and sr_draft:
        parts.extend(["--spec-replace", sr_target, sr_draft])

    # Override tensor draft
    otd = data.get("speculative", {}).get("override_tensor_draft")
    if otd:
        parts.extend(["--override-tensor-draft", otd])

    return parts


def build_command_string(version_id, redact_secrets=False):
    """Build a properly quoted command string for display/copy-paste."""
    import shlex

    args = build_command(version_id)
    if redact_secrets:
        secret_flags = {"--hf-token", "--api-key"}
        masked = []
        skip_next = False
        for i, arg in enumerate(args):
            if skip_next:
                skip_next = False
                masked.append("***")
                continue
            if arg in secret_flags and i + 1 < len(args):
                masked.append(arg)
                skip_next = True
                continue
            masked.append(arg)
        args = masked
    return " ".join(shlex.quote(a) for a in args)


def get_models_in_dir(model_dir=None):
    """Scan a directory for .gguf files."""
    import os
    from config import MODEL_DIR

    d = model_dir or MODEL_DIR
    if not os.path.isdir(d):
        return []

    models = []
    for root, dirs, files in os.walk(d):
        for f in sorted(files):
            if f.lower().endswith(".gguf"):
                full = os.path.join(root, f)
                rel = os.path.relpath(full, d)
                models.append({"path": full, "name": f, "rel": rel})
    return models
