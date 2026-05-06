"""Import running llama-server config from process cmdline."""
import os
from services.screen_manager import get_status


def get_server_pid():
    """Get PID of llama-server process. Finds it by name via pgrep."""
    # First check if server process is running
    status = get_status()
    if not status['running']:
        return None
    # Find llama-server by process name via pgrep
    try:
        import subprocess
        out = subprocess.check_output(['pgrep', '-x', 'llama-server'], text=True, stderr=subprocess.DEVNULL)
        pids = out.strip().split('\n')
        return int(pids[0]) if pids and pids[0] else None
    except (subprocess.CalledProcessError, ValueError):
        return None


def read_cmdline(pid):
    """Read /proc/<pid>/cmdline and return list of arguments."""
    try:
        with open(f'/proc/{pid}/cmdline', 'rb') as f:
            raw = f.read()
        parts = raw.split(b'\x00')
        return [p.decode('utf-8', errors='replace') for p in parts if p]
    except (FileNotFoundError, PermissionError):
        return None


def _normalize_flag(name):
    """Normalize flag name: strip --, convert underscores to hyphens."""
    return name.lstrip('-').replace('_', '-')


def parse_args(args):
    """Parse command line args into a dict of flag -> value."""
    result = {}

    bool_flags = {
        'mlock', 'mmap', 'kvo', 'kv-offload', 'repack', 'cb', 'cont-batching',
        'warmup', 'special', 'spm-infill', 'offline', 'verbose', 'perf',
        'cache-prompt', 'metrics', 'props', 'slots', 'embedding', 'embeddings',
        'rerank', 'reranking', 'webui', 'jinja', 'kv-unified',
        'cache-idle-slots', 'context-shift', 'log-prefix', 'log-timestamps',
        'log-disable', 'escape', 'ignore-eos', 'backend-sampling',
        'reuse-port', 'lora-init-without-apply', 'skip-chat-parsing',
        'prefill-assistant', 'op-offload', 'cpu-moe', 'cpu-moe-draft',
        'check-tensors', 'no-host', 'flash-attn', 'fa',
    }

    short_to_long = {
        '-m': 'model', '-t': 'threads', '-tb': 'threads-batch',
        '-c': 'ctx-size', '-n': 'n-predict', '-b': 'batch-size',
        '-ub': 'ubatch-size', '-s': 'seed', '-ngl': 'gpu-layers',
        '-fa': 'flash-attn', '-np': 'parallel', '-hfr': 'hf-repo',
        '-hff': 'hf-file', '-hft': 'hf-token', '-a': 'alias',
        '-dev': 'device', '-sm': 'split-mode', '-ts': 'tensor-split',
        '-mg': 'main-gpu', '-ctk': 'cache-type-k', '-ctv': 'cache-type-v',
        '-to': 'timeout', '-mm': 'mmproj', '-mmu': 'mmproj-url',
        '-md': 'model-draft', '-cd': 'ctx-size-draft',
        '-devd': 'device-draft', '-ngld': 'gpu-layers-draft',
        '-lcs': 'lookup-cache-static', '-lcd': 'lookup-cache-dynamic',
        '-ctxcp': 'ctx-checkpoints', '-cpent': 'checkpoint-every-n-tokens',
        '-cram': 'cache-ram', '-j': 'json-schema', '-jf': 'json-schema-file',
        '-rea': 'reasoning', '-sps': 'slot-prompt-similarity',
        '-kvo': 'kv-offload', '-nkvo': 'no-kv-offload',
    }

    if not args:
        return result

    i = 1

    while i < len(args):
        arg = args[i]
        if not arg.startswith('-'):
            i += 1
            continue

        # Long --no-xxx flags (check before other long flags)
        if arg.startswith('--no-'):
            positive = _normalize_flag(arg[5:])  # strip '--no-', keep rest
            result[positive] = False
            i += 1
            continue

        # Short flags (-X, -XX, etc.) — anything with single dash, no double dash
        if arg.startswith('-') and not arg.startswith('--'):
            long_name = short_to_long.get(arg, _normalize_flag(arg))
            if i + 1 < len(args) and not args[i+1].startswith('-'):
                result[long_name] = args[i+1]
                i += 2
            else:
                result[long_name] = True
            continue

        # Long --flag=value format
        if '=' in arg:
            flag, val = arg.split('=', 1)
            result[_normalize_flag(flag)] = val
            i += 1
            continue

        # Long --flag (boolean or with value)
        flag_name = _normalize_flag(arg)
        if flag_name in bool_flags:
            result[flag_name] = True
            i += 1
            continue

        # --flag value format
        if i + 1 < len(args) and not args[i+1].startswith('-'):
            result[flag_name] = args[i+1]
            i += 2
            continue

        result[flag_name] = True
        i += 1

    return result


# Maps parsed flag name → (category, column)
FLAG_TO_COLUMN = {
    'model': ('model_loading', 'model_path'),
    'model-url': ('model_loading', 'model_url'),
    'hf-repo': ('model_loading', 'hf_repo'),
    'hf': ('model_loading', 'hf_repo'),
    'hf-file': ('model_loading', 'hf_file'),
    'hf-token': ('model_loading', 'hf_token'),
    'alias': ('model_loading', 'aliases'),
    'tags': ('model_loading', 'tags'),
    'mmproj': ('model_loading', 'mmproj_path'),
    'mmproj-url': ('model_loading', 'mmproj_url'),
    'ctx-size': ('context_batching', 'ctx_size'),
    'n-predict': ('context_batching', 'n_predict'),
    'batch-size': ('context_batching', 'batch_size'),
    'ubatch-size': ('context_batching', 'ubatch_size'),
    'keep': ('context_batching', 'keep_tokens'),
    'parallel': ('context_batching', 'n_parallel'),
    'cont-batching': ('context_batching', 'cont_batching'),
    'context-shift': ('context_batching', 'context_shift'),
    'reverse-prompt': ('context_batching', 'reverse_prompt'),
    'special': ('context_batching', 'special_tokens'),
    'warmup': ('context_batching', 'warmup'),
    'spm-infill': ('context_batching', 'spm_infill'),
    'pooling': ('context_batching', 'pooling'),
    'cache-prompt': ('context_batching', 'cache_prompt'),
    'cache-reuse': ('context_batching', 'cache_reuse'),
    'slot-prompt-similarity': ('context_batching', 'slot_prompt_similarity'),
    'threads': ('cpu_threading', 'threads'),
    'threads-batch': ('cpu_threading', 'threads_batch'),
    'cpu-mask': ('cpu_threading', 'cpu_mask'),
    'cpu-range': ('cpu_threading', 'cpu_range'),
    'cpu-strict': ('cpu_threading', 'cpu_strict'),
    'prio': ('cpu_threading', 'prio'),
    'poll': ('cpu_threading', 'poll'),
    'cpu-mask-batch': ('cpu_threading', 'cpu_mask_batch'),
    'cpu-range-batch': ('cpu_threading', 'cpu_range_batch'),
    'cpu-strict-batch': ('cpu_threading', 'cpu_strict_batch'),
    'prio-batch': ('cpu_threading', 'prio_batch'),
    'poll-batch': ('cpu_threading', 'poll_batch'),
    'numa': ('cpu_threading', 'numa'),
    'threads-draft': ('cpu_threading', 'threads_draft'),
    'threads-batch-draft': ('cpu_threading', 'threads_batch_draft'),
    'gpu-layers': ('gpu_device', 'gpu_layers'),
    'n-gpu-layers': ('gpu_device', 'gpu_layers'),
    'device': ('gpu_device', 'devices'),
    'split-mode': ('gpu_device', 'split_mode'),
    'tensor-split': ('gpu_device', 'tensor_split'),
    'main-gpu': ('gpu_device', 'main_gpu'),
    'flash-attn': ('gpu_device', 'flash_attn'),
    'fa': ('gpu_device', 'flash_attn'),
    'ngl': ('gpu_device', 'gpu_layers'),
    'kv-offload': ('gpu_device', 'kv_offload'),
    'repack': ('gpu_device', 'repack'),
    'no-host': ('gpu_device', 'no_host'),
    'fit': ('gpu_device', 'fit'),
    'fit-target': ('gpu_device', 'fit_target'),
    'fit-ctx': ('gpu_device', 'fit_ctx'),
    'op-offload': ('gpu_device', 'op_offload'),
    'cpu-moe': ('gpu_device', 'cpu_moe'),
    'n-cpu-moe': ('gpu_device', 'n_cpu_moe'),
    'cpu-moe-draft': ('gpu_device', 'cpu_moe_draft'),
    'n-cpu-moe-draft': ('gpu_device', 'n_cpu_moe_draft'),
    'cache-type-k': ('memory', 'cache_type_k'),
    'cache-type-v': ('memory', 'cache_type_v'),
    'cache-type-k-draft': ('memory', 'cache_type_k_draft'),
    'cache-type-v-draft': ('memory', 'cache_type_v_draft'),
    'mmap': ('memory', 'mmap'),
    'mlock': ('memory', 'mlock'),
    'direct-io': ('memory', 'direct_io'),
    'defrag-thold': ('memory', 'defrag_thold'),
    'swa-full': ('memory', 'swa_full'),
    'samplers': ('sampling', 'samplers'),
    'sampler-seq': ('sampling', 'sampler_seq'),
    'sampling-seq': ('sampling', 'sampler_seq'),
    'seed': ('sampling', 'seed'),
    'ignore-eos': ('sampling', 'ignore_eos'),
    'temp': ('sampling', 'temperature'),
    'temperature': ('sampling', 'temperature'),
    'top-k': ('sampling', 'top_k'),
    'top-p': ('sampling', 'top_p'),
    'min-p': ('sampling', 'min_p'),
    'top-nsigma': ('sampling', 'top_n_sigma'),
    'top-n-sigma': ('sampling', 'top_n_sigma'),
    'xtc-probability': ('sampling', 'xtc_probability'),
    'xtc-threshold': ('sampling', 'xtc_threshold'),
    'typical': ('sampling', 'typical_p'),
    'typical-p': ('sampling', 'typical_p'),
    'repeat-last-n': ('sampling', 'repeat_last_n'),
    'repeat-penalty': ('sampling', 'repeat_penalty'),
    'presence-penalty': ('sampling', 'presence_penalty'),
    'frequency-penalty': ('sampling', 'frequency_penalty'),
    'dry-multiplier': ('sampling', 'dry_multiplier'),
    'dry-base': ('sampling', 'dry_base'),
    'dry-allowed-length': ('sampling', 'dry_allowed_length'),
    'dry-penalty-last-n': ('sampling', 'dry_penalty_last_n'),
    'adaptive-target': ('sampling', 'adaptive_target'),
    'adaptive-decay': ('sampling', 'adaptive_decay'),
    'dynatemp-range': ('sampling', 'dynatemp_range'),
    'dynatemp-exp': ('sampling', 'dynatemp_exp'),
    'mirostat': ('sampling', 'mirostat'),
    'mirostat-lr': ('sampling', 'mirostat_lr'),
    'mirostat-ent': ('sampling', 'mirostat_ent'),
    'backend-sampling': ('sampling', 'backend_sampling'),
    'host': ('server', 'host'),
    'port': ('server', 'port'),
    'reuse-port': ('server', 'reuse_port'),
    'path': ('server', 'static_path'),
    'api-prefix': ('server', 'api_prefix'),
    'timeout': ('server', 'timeout'),
    'threads-http': ('server', 'threads_http'),
    'api-key': ('server', 'api_key'),
    'ssl-key-file': ('server', 'ssl_key_file'),
    'ssl-cert-file': ('server', 'ssl_cert_file'),
    'webui': ('server', 'webui'),
    'embedding': ('server', 'embedding'),
    'embeddings': ('server', 'embedding'),
    'rerank': ('server', 'reranking'),
    'reranking': ('server', 'reranking'),
    'metrics': ('server', 'metrics'),
    'props': ('server', 'props'),
    'slots': ('server', 'slots'),
    'slot-save-path': ('server', 'slot_save_path'),
    'media-path': ('server', 'media_path'),
    'lora-init-without-apply': ('server', 'lora_init_without_apply'),
    'sleep-idle-seconds': ('server', 'sleep_idle_seconds'),
    'draft': ('speculative', 'draft_max'),
    'draft-max': ('speculative', 'draft_max'),
    'draft-min': ('speculative', 'draft_min'),
    'draft-n-min': ('speculative', 'draft_min'),
    'draft-p-min': ('speculative', 'draft_p_min'),
    'ctx-size-draft': ('speculative', 'ctx_size_draft'),
    'device-draft': ('speculative', 'devices_draft'),
    'gpu-layers-draft': ('speculative', 'gpu_layers_draft'),
    'n-gpu-layers-draft': ('speculative', 'gpu_layers_draft'),
    'spec-type': ('speculative', 'spec_type'),
    'spec-ngram-size-n': ('speculative', 'spec_ngram_size_n'),
    'spec-ngram-size-m': ('speculative', 'spec_ngram_size_m'),
    'spec-ngram-min-hits': ('speculative', 'spec_ngram_min_hits'),
    'chat-template': ('chat_templates', 'chat_template'),
    'chat-template-file': ('chat_templates', 'chat_template_file'),
    'chat-template-kwargs': ('chat_templates', 'chat_template_kwargs'),
    'jinja': ('chat_templates', 'jinja'),
    'reasoning-format': ('chat_templates', 'reasoning_format'),
    'reasoning': ('chat_templates', 'reasoning'),
    'reasoning-budget': ('chat_templates', 'reasoning_budget'),
    'reasoning-budget-message': ('chat_templates', 'reasoning_budget_message'),
    'skip-chat-parsing': ('chat_templates', 'skip_chat_parsing'),
    'prefill-assistant': ('chat_templates', 'prefill_assistant'),
    'ctx-checkpoints': ('checkpoints', 'ctx_checkpoints'),
    'swa-checkpoints': ('checkpoints', 'ctx_checkpoints'),
    'checkpoint-every-n-tokens': ('checkpoints', 'checkpoint_every_nt'),
    'cache-ram': ('checkpoints', 'cache_ram'),
    'kv-unified': ('checkpoints', 'kv_unified'),
    'cache-idle-slots': ('checkpoints', 'cache_idle_slots'),
    'lookup-cache-static': ('checkpoints', 'lookup_cache_static'),
    'lookup-cache-dynamic': ('checkpoints', 'lookup_cache_dynamic'),
    'log-verbosity': ('logging', 'log_verbosity'),
    'log-file': ('logging', 'log_file'),
    'log-colors': ('logging', 'log_colors'),
    'log-prefix': ('logging', 'log_prefix'),
    'log-timestamps': ('logging', 'log_timestamps'),
    'verbose': ('logging', 'verbose'),
    'log-verbose': ('logging', 'verbose'),
    'log-disable': ('logging', 'log_disable'),
    'offline': ('logging', 'offline'),
    'perf': ('logging', 'perf'),
    'escape': ('logging', 'escape'),
    'rope-scaling': ('advanced', 'rope_scaling'),
    'rope-scale': ('advanced', 'rope_scale'),
    'rope-freq-base': ('advanced', 'rope_freq_base'),
    'rope-freq-scale': ('advanced', 'rope_freq_scale'),
    'yarn-orig-ctx': ('advanced', 'yarn_orig_ctx'),
    'yarn-ext-factor': ('advanced', 'yarn_ext_factor'),
    'yarn-attn-factor': ('advanced', 'yarn_attn_factor'),
    'yarn-beta-slow': ('advanced', 'yarn_beta_slow'),
    'yarn-beta-fast': ('advanced', 'yarn_beta_fast'),
    'grammar': ('advanced', 'grammar'),
    'grammar-file': ('advanced', 'grammar_file'),
    'json-schema': ('advanced', 'json_schema'),
    'json-schema-file': ('advanced', 'json_schema_file'),
    'check-tensors': ('advanced', 'check_tensors'),
    'image-min-tokens': ('advanced', 'image_min_tokens'),
    'image-max-tokens': ('advanced', 'image_max_tokens'),
}


def coerce_value(col, val):
    """Coerce a string value to the right DB type."""
    if val is None:
        return None
    if isinstance(val, bool):
        return 1 if val else 0

    val_str = str(val)

    # Boolean columns
    bool_cols = {
        'cont_batching', 'context_shift', 'special_tokens', 'warmup',
        'spm_infill', 'cache_prompt', 'cpu_strict', 'cpu_strict_batch',
        'poll_batch', 'kv_offload', 'repack', 'no_host', 'op_offload',
        'cpu_moe', 'cpu_moe_draft', 'mmap', 'mlock', 'direct_io',
        'ignore_eos', 'backend_sampling', 'reuse_port', 'webui',
        'embedding', 'reranking', 'metrics', 'props', 'slots',
        'lora_init_without_apply', 'jinja', 'skip_chat_parsing',
        'prefill_assistant', 'kv_unified', 'cache_idle_slots',
        'log_prefix', 'log_timestamps', 'verbose', 'log_disable',
        'offline', 'perf', 'escape', 'check_tensors', 'mmproj_auto',
        'mmproj_offload',
    }
    if col in bool_cols:
        return 1 if val_str.lower() in ('true', '1', 'on') else 0

    # Integer columns
    int_cols = {
        'ctx_size', 'n_predict', 'batch_size', 'ubatch_size', 'keep_tokens',
        'n_parallel', 'cache_reuse', 'threads', 'threads_batch', 'prio',
        'poll', 'prio_batch', 'main_gpu', 'fit_ctx', 'n_cpu_moe',
        'n_cpu_moe_draft', 'seed', 'top_k', 'repeat_last_n', 'dry_allowed_length',
        'dry_penalty_last_n', 'mirostat', 'port', 'timeout', 'threads_http',
        'sleep_idle_seconds', 'draft_max', 'draft_min', 'ctx_size_draft',
        'spec_ngram_size_n', 'spec_ngram_size_m', 'spec_ngram_min_hits',
        'reasoning_budget', 'ctx_checkpoints', 'checkpoint_every_nt',
        'cache_ram', 'log_verbosity', 'yarn_orig_ctx', 'image_min_tokens',
        'image_max_tokens', 'threads_draft', 'threads_batch_draft',
    }
    if col in int_cols:
        try:
            return int(val_str)
        except ValueError:
            return val_str

    # Float columns
    float_cols = {
        'slot_prompt_similarity', 'temperature', 'top_p', 'min_p',
        'top_n_sigma', 'xtc_probability', 'xtc_threshold', 'typical_p',
        'repeat_penalty', 'presence_penalty', 'frequency_penalty',
        'dry_multiplier', 'dry_base', 'adaptive_target', 'adaptive_decay',
        'dynatemp_range', 'dynatemp_exp', 'mirostat_lr', 'mirostat_ent',
        'draft_p_min', 'rope_scale', 'rope_freq_base', 'rope_freq_scale',
        'yarn_ext_factor', 'yarn_attn_factor', 'yarn_beta_slow',
        'yarn_beta_fast',
    }
    if col in float_cols:
        try:
            return float(val_str)
        except ValueError:
            return val_str

    return val_str


def _extract_model_name(parsed):
    """Extract a human-readable model name from parsed args.

    Priority: model_path basename > hf_repo/hf_file combo > fallback.
    """
    # Try model_path first (basename)
    model_path = parsed.get('model')
    if model_path:
        return os.path.basename(model_path)

    # Try hf_repo + hf_file
    hf_repo = parsed.get('hf-repo') or parsed.get('hf')
    hf_file = parsed.get('hf-file')
    if hf_repo and hf_file:
        return f'{hf_repo}/{hf_file}'
    if hf_repo:
        return hf_repo

    return None


def _compare_signatures(signature, version_id):
    """Compare a signature dict against an existing version.

    Returns True if all set values in the signature match the version's stored values.
    """
    from models.configs import get_category, CATEGORIES

    def _compare_val(a, b):
        try:
            return float(a) == float(b)
        except (ValueError, TypeError):
            return str(a) == str(b)

    for col, val in signature.items():
        if val is None or val == 0 or val == '':
            continue
        cat = next((c for c in CATEGORIES if (c, col) in FLAG_TO_COLUMN.values()), None)
        if not cat:
            continue
        row = get_category(version_id, cat)
        existing = row.get(col) if row else None
        if existing is not None:
            if not _compare_val(existing, val):
                return False
    return True


def import_running_config(config_name=None):
    """Import the running llama-server config into a new config + version.

    Groups imports by model filename. If a config for the same model already exists,
    adds a new version only if the settings differ from the latest version.

    Returns (config_id, version_id, parsed_args_dict, created_new).
    - created_new is True when a new version was created, False when existing version matched.
    """
    pid = get_server_pid()
    if not pid:
        raise RuntimeError('No running llama-server process found')

    args = read_cmdline(pid)
    if not args:
        raise RuntimeError(f'Could not read cmdline for PID {pid}')

    parsed = parse_args(args)

    # Derive config name from model, or fall back to provided/custom name
    model_name = _extract_model_name(parsed)
    # Use custom name if explicitly provided and not the default placeholder
    cfg_name = model_name or (config_name if config_name and config_name != 'Imported Config' else None) or 'Imported Config'

    # Build signature: flat dict of col -> coerced_value for all mapped flags
    signature = {}
    for flag, val in parsed.items():
        mapping = FLAG_TO_COLUMN.get(flag)
        if not mapping:
            continue
        cat, col = mapping
        signature[col] = coerce_value(col, val)

    # Look for existing config matching this model name
    from models.configs import get_all_configs, get_latest_version, \
        create_config, create_version, save_category

    existing_config = None
    if model_name:
        all_configs = get_all_configs()
        for cfg in all_configs:
            if cfg['name'] == cfg_name:
                existing_config = cfg
                break

    # If we found a matching config, check if latest version already has these settings
    if existing_config:
        latest = get_latest_version(existing_config['id'])
        if latest:
            latest_vid = latest['id'] if isinstance(latest, dict) else latest[0]
            if _compare_signatures(signature, latest_vid):
                # Settings match — no new version needed
                return existing_config['id'], latest_vid, parsed, False

    cfg_id = None
    if existing_config:
        cfg_id = existing_config['id']
    else:
        cfg_id = create_config(
            name=cfg_name,
            description=f'Imported from running process (PID {pid})',
        )

    version_id = create_version(cfg_id, comments='Auto-imported from running server')

    # Map parsed args to category tables
    categories = {}
    for flag, val in parsed.items():
        mapping = FLAG_TO_COLUMN.get(flag)
        if not mapping:
            continue
        cat, col = mapping
        coerced = coerce_value(col, val)
        if cat not in categories:
            categories[cat] = {}
        categories[cat][col] = coerced

    # Save each category
    for cat, data in categories.items():
        if data:
            save_category(version_id, cat, data)

    return cfg_id, version_id, parsed, True