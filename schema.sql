-- llama.cpp Config Manager Schema
-- Database: llama_configs

CREATE TABLE IF NOT EXISTS configs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    model_dir VARCHAR(1024),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS config_versions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    config_id INT NOT NULL,
    version_number INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    comments TEXT,
    status VARCHAR(20) DEFAULT NULL,
    FOREIGN KEY (config_id) REFERENCES configs(id) ON DELETE CASCADE,
    UNIQUE KEY uniq_config_version (config_id, version_number)
);

-- Migration: Add status column if it doesn't exist yet
ALTER TABLE config_versions ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT NULL;

CREATE TABLE IF NOT EXISTS performance_metrics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    version_id INT NOT NULL,
    load_time_sec DECIMAL(10,2),
    tps DECIMAL(10,2),
    vram_used_mb INT,
    peak_cpu_pct DECIMAL(5,2),
    notes TEXT,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (version_id) REFERENCES config_versions(id) ON DELETE CASCADE
);

-- Model Loading
CREATE TABLE IF NOT EXISTS v_model_loading (
    version_id INT PRIMARY KEY,
    model_path VARCHAR(2048),
    model_url VARCHAR(2048),
    hf_repo VARCHAR(512),
    hf_file VARCHAR(512),
    hf_token VARCHAR(512),
    lora_paths TEXT,
    control_vector_paths TEXT,
    model_draft VARCHAR(2048),
    model_vocoder VARCHAR(2048),
    mmproj_path VARCHAR(2048),
    mmproj_url VARCHAR(2048),
    mmproj_auto TINYINT(1),
    mmproj_offload TINYINT(1),
    aliases TEXT,
    tags TEXT,
    FOREIGN KEY (version_id) REFERENCES config_versions(id) ON DELETE CASCADE
);

-- Context & Batching
CREATE TABLE IF NOT EXISTS v_context_batching (
    version_id INT PRIMARY KEY,
    ctx_size INT,
    n_predict INT,
    batch_size INT,
    ubatch_size INT,
    keep_tokens INT,
    n_parallel INT,
    cont_batching TINYINT(1),
    context_shift TINYINT(1),
    reverse_prompt TEXT,
    special_tokens TINYINT(1),
    warmup TINYINT(1),
    spm_infill TINYINT(1),
    pooling VARCHAR(50),
    cache_prompt TINYINT(1),
    cache_reuse INT,
    slot_prompt_similarity DECIMAL(3,2),
    FOREIGN KEY (version_id) REFERENCES config_versions(id) ON DELETE CASCADE
);

-- CPU / Threading
CREATE TABLE IF NOT EXISTS v_cpu_threading (
    version_id INT PRIMARY KEY,
    threads INT,
    threads_batch INT,
    cpu_mask VARCHAR(255),
    cpu_range VARCHAR(64),
    cpu_strict TINYINT(1),
    prio INT,
    poll INT,
    cpu_mask_batch VARCHAR(255),
    cpu_range_batch VARCHAR(64),
    cpu_strict_batch TINYINT(1),
    prio_batch INT,
    poll_batch TINYINT(1),
    numa VARCHAR(50),
    threads_draft INT,
    threads_batch_draft INT,
    FOREIGN KEY (version_id) REFERENCES config_versions(id) ON DELETE CASCADE
);

-- GPU / Device
CREATE TABLE IF NOT EXISTS v_gpu_device (
    version_id INT PRIMARY KEY,
    gpu_layers VARCHAR(50),
    devices VARCHAR(512),
    split_mode VARCHAR(50),
    tensor_split VARCHAR(255),
    main_gpu INT,
    flash_attn VARCHAR(10),
    kv_offload TINYINT(1),
    repack TINYINT(1),
    no_host TINYINT(1),
    fit VARCHAR(10),
    fit_target VARCHAR(255),
    fit_ctx INT,
    op_offload TINYINT(1),
    cpu_moe TINYINT(1),
    n_cpu_moe INT,
    cpu_moe_draft TINYINT(1),
    n_cpu_moe_draft INT,
    FOREIGN KEY (version_id) REFERENCES config_versions(id) ON DELETE CASCADE
);

-- Memory
CREATE TABLE IF NOT EXISTS v_memory (
    version_id INT PRIMARY KEY,
    cache_type_k VARCHAR(20),
    cache_type_v VARCHAR(20),
    cache_type_k_draft VARCHAR(20),
    cache_type_v_draft VARCHAR(20),
    mmap TINYINT(1),
    mlock TINYINT(1),
    direct_io TINYINT(1),
    defrag_thold INT,
    swa_full TINYINT(1),
    FOREIGN KEY (version_id) REFERENCES config_versions(id) ON DELETE CASCADE
);

-- Sampling
CREATE TABLE IF NOT EXISTS v_sampling (
    version_id INT PRIMARY KEY,
    samplers TEXT,
    sampler_seq VARCHAR(50),
    seed BIGINT,
    ignore_eos TINYINT(1),
    temperature DECIMAL(5,4),
    top_k INT,
    top_p DECIMAL(4,3),
    min_p DECIMAL(4,3),
    top_n_sigma DECIMAL(5,2),
    xtc_probability DECIMAL(4,3),
    xtc_threshold DECIMAL(4,3),
    typical_p DECIMAL(4,3),
    repeat_last_n INT,
    repeat_penalty DECIMAL(5,4),
    presence_penalty DECIMAL(5,4),
    frequency_penalty DECIMAL(5,4),
    dry_multiplier DECIMAL(5,2),
    dry_base DECIMAL(5,2),
    dry_allowed_length INT,
    dry_penalty_last_n INT,
    adaptive_target DECIMAL(5,2),
    adaptive_decay DECIMAL(4,2),
    dynatemp_range DECIMAL(5,2),
    dynatemp_exp DECIMAL(5,2),
    mirostat INT,
    mirostat_lr DECIMAL(4,3),
    mirostat_ent DECIMAL(5,2),
    backend_sampling TINYINT(1),
    FOREIGN KEY (version_id) REFERENCES config_versions(id) ON DELETE CASCADE
);

-- Server
CREATE TABLE IF NOT EXISTS v_server (
    version_id INT PRIMARY KEY,
    host VARCHAR(255),
    port INT,
    reuse_port TINYINT(1),
    static_path VARCHAR(512),
    api_prefix VARCHAR(255),
    timeout INT,
    threads_http INT,
    api_key TEXT,
    ssl_key_file VARCHAR(512),
    ssl_cert_file VARCHAR(512),
    webui TINYINT(1),
    webui_config TEXT,
    webui_config_file VARCHAR(512),
    webui_mcp_proxy TINYINT(1),
    tools TEXT,
    embedding TINYINT(1),
    reranking TINYINT(1),
    metrics TINYINT(1),
    props TINYINT(1),
    slots TINYINT(1),
    slot_save_path VARCHAR(512),
    media_path VARCHAR(512),
    cache_prompt TINYINT(1),
    lora_init_without_apply TINYINT(1),
    sleep_idle_seconds INT,
    FOREIGN KEY (version_id) REFERENCES config_versions(id) ON DELETE CASCADE
);

-- Speculative Decoding
CREATE TABLE IF NOT EXISTS v_speculative (
    version_id INT PRIMARY KEY,
    draft_max INT,
    draft_min INT,
    draft_p_min DECIMAL(4,3),
    ctx_size_draft INT,
    devices_draft VARCHAR(512),
    gpu_layers_draft VARCHAR(50),
    spec_type VARCHAR(50),
    spec_ngram_size_n INT,
    spec_ngram_size_m INT,
    spec_ngram_min_hits INT,
    spec_draft_n_max INT,
    spec_replace_target VARCHAR(255),
    spec_replace_draft VARCHAR(255),
    override_tensor_draft TEXT,
    FOREIGN KEY (version_id) REFERENCES config_versions(id) ON DELETE CASCADE
);

-- Migration: Add spec_draft_n_max column if it doesn't exist yet
ALTER TABLE v_speculative ADD COLUMN IF NOT EXISTS spec_draft_n_max INT;

-- Chat & Templates
CREATE TABLE IF NOT EXISTS v_chat_templates (
    version_id INT PRIMARY KEY,
    chat_template VARCHAR(50),
    chat_template_file VARCHAR(512),
    chat_template_kwargs TEXT,
    jinja TINYINT(1),
    reasoning_format VARCHAR(50),
    reasoning VARCHAR(10),
    reasoning_budget INT,
    reasoning_budget_message TEXT,
    skip_chat_parsing TINYINT(1),
    prefill_assistant TINYINT(1),
    backend_sampling TINYINT(1),
    FOREIGN KEY (version_id) REFERENCES config_versions(id) ON DELETE CASCADE
);

-- Context Checkpoints & Cache
CREATE TABLE IF NOT EXISTS v_checkpoints (
    version_id INT PRIMARY KEY,
    ctx_checkpoints INT,
    checkpoint_every_nt INT,
    cache_ram INT,
    kv_unified TINYINT(1),
    cache_idle_slots TINYINT(1),
    lookup_cache_static VARCHAR(512),
    lookup_cache_dynamic VARCHAR(512),
    FOREIGN KEY (version_id) REFERENCES config_versions(id) ON DELETE CASCADE
);

-- Logging
CREATE TABLE IF NOT EXISTS v_logging (
    version_id INT PRIMARY KEY,
    log_verbosity INT,
    log_file VARCHAR(512),
    log_colors VARCHAR(10),
    log_prefix TINYINT(1),
    log_timestamps TINYINT(1),
    verbose TINYINT(1),
    log_disable TINYINT(1),
    offline TINYINT(1),
    perf TINYINT(1),
    escape TINYINT(1),
    FOREIGN KEY (version_id) REFERENCES config_versions(id) ON DELETE CASCADE
);

-- Advanced / Override
CREATE TABLE IF NOT EXISTS v_advanced (
    version_id INT PRIMARY KEY,
    rope_scaling VARCHAR(20),
    rope_scale DECIMAL(10,4),
    rope_freq_base DECIMAL(10,4),
    rope_freq_scale DECIMAL(10,4),
    yarn_orig_ctx INT,
    yarn_ext_factor DECIMAL(10,4),
    yarn_attn_factor DECIMAL(10,4),
    yarn_beta_slow DECIMAL(10,4),
    yarn_beta_fast DECIMAL(10,4),
    grammar TEXT,
    grammar_file VARCHAR(512),
    json_schema TEXT,
    json_schema_file VARCHAR(512),
    check_tensors TINYINT(1),
    image_min_tokens INT,
    image_max_tokens INT,
    pooling_override VARCHAR(50),
    FOREIGN KEY (version_id) REFERENCES config_versions(id) ON DELETE CASCADE
);

-- Common Options (user-curated list of frequently used fields)
CREATE TABLE IF NOT EXISTS common_options (
    id INT AUTO_INCREMENT PRIMARY KEY,
    category VARCHAR(50) NOT NULL,
    column_name VARCHAR(100) NOT NULL,
    display_order INT NOT NULL DEFAULT 0,
    custom_label VARCHAR(255),
    UNIQUE KEY uniq_common_field (category, column_name)
);

-- Complex value: Logit Biases
CREATE TABLE IF NOT EXISTS v_logit_biases (
    id INT AUTO_INCREMENT PRIMARY KEY,
    version_id INT NOT NULL,
    token_id INT NOT NULL,
    bias_value DECIMAL(8,4) NOT NULL,
    FOREIGN KEY (version_id) REFERENCES config_versions(id) ON DELETE CASCADE
);

-- Complex value: LoRA Adapters (structured)
CREATE TABLE IF NOT EXISTS v_lora_adapters (
    id INT AUTO_INCREMENT PRIMARY KEY,
    version_id INT NOT NULL,
    path VARCHAR(2048) NOT NULL,
    scale DECIMAL(5,4),
    FOREIGN KEY (version_id) REFERENCES config_versions(id) ON DELETE CASCADE
);

-- Complex value: Control Vectors
CREATE TABLE IF NOT EXISTS v_control_vectors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    version_id INT NOT NULL,
    path VARCHAR(2048) NOT NULL,
    scale DECIMAL(5,4),
    layer_range_start INT,
    layer_range_end INT,
    FOREIGN KEY (version_id) REFERENCES config_versions(id) ON DELETE CASCADE
);

-- Complex value: Override KV
CREATE TABLE IF NOT EXISTS v_override_kv (
    id INT AUTO_INCREMENT PRIMARY KEY,
    version_id INT NOT NULL,
    key_name VARCHAR(255) NOT NULL,
    key_type VARCHAR(10) NOT NULL,
    key_value TEXT NOT NULL,
    FOREIGN KEY (version_id) REFERENCES config_versions(id) ON DELETE CASCADE
);

-- Complex value: Override Tensors
CREATE TABLE IF NOT EXISTS v_override_tensors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    version_id INT NOT NULL,
    tensor_pattern VARCHAR(255) NOT NULL,
    buffer_type VARCHAR(50) NOT NULL,
    FOREIGN KEY (version_id) REFERENCES config_versions(id) ON DELETE CASCADE
);

-- Complex value: DRY Sequence Breakers
CREATE TABLE IF NOT EXISTS v_dry_sequence_breakers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    version_id INT NOT NULL,
    breaker_char VARCHAR(10) NOT NULL,
    FOREIGN KEY (version_id) REFERENCES config_versions(id) ON DELETE CASCADE
);

-- VRAM Safety & OOM Prediction
CREATE TABLE IF NOT EXISTS model_metadata (
    id INT AUTO_INCREMENT PRIMARY KEY,
    model_path VARCHAR(2048) NOT NULL,
    architecture VARCHAR(50),
    n_layers INT,
    n_embd INT,
    n_head INT,
    n_head_kv INT,
    n_ctx_train INT,
    key_length INT,
    value_length INT,
    file_size_bytes BIGINT,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uniq_model_path (model_path(767))
);

CREATE TABLE IF NOT EXISTS vram_stress_tests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    version_id INT NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    status VARCHAR(20) DEFAULT 'running',
    total_vram_mb INT,
    compaction_coefficient DECIMAL(6,4),
    failure_ctx_tokens INT NULL,
    model_weight_size_mb INT,
    kv_per_token_bytes DECIMAL(8,4),
    FOREIGN KEY (version_id) REFERENCES config_versions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS vram_stress_data_points (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stress_test_id INT NOT NULL,
    ctx_tokens INT NOT NULL,
    vram_used_mb INT,
    peak_vram_mb INT,
    tps DECIMAL(8,2),
    FOREIGN KEY (stress_test_id) REFERENCES vram_stress_tests(id) ON DELETE CASCADE
);

-- Config Templates
CREATE TABLE IF NOT EXISTS config_templates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    source_version_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_version_id) REFERENCES config_versions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS template_variables (
    id INT AUTO_INCREMENT PRIMARY KEY,
    template_id INT NOT NULL,
    variable_name VARCHAR(100) NOT NULL,
    display_label VARCHAR(255),
    default_value TEXT,
    hint TEXT,
    display_order INT NOT NULL DEFAULT 0,
    FOREIGN KEY (template_id) REFERENCES config_templates(id) ON DELETE CASCADE,
    UNIQUE KEY uniq_template_var (template_id, variable_name)
);

-- Config Usage Analytics
CREATE TABLE IF NOT EXISTS config_usage (
    id INT AUTO_INCREMENT PRIMARY KEY,
    version_id INT NOT NULL,
    launched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    stopped_at TIMESTAMP NULL DEFAULT NULL,
    exit_reason VARCHAR(50) DEFAULT NULL,
    FOREIGN KEY (version_id) REFERENCES config_versions(id) ON DELETE CASCADE
);
