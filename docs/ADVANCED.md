# Advanced Features & Optimization

This guide covers the technical details for fine-tuning model performance and interacting with the `llama-manager` API.

## Parameter Reference

The following parameters are used to configure `llama-server`. They are organized by functional category. Each parameter lists its CLI flag(s), default value, and a brief description.

**Tristate Parameters**: Some parameters support three states instead of a simple on/off:

| State | Effect |
|---|---|
| **(default)** | Omit the flag entirely — llama.cpp uses its built-in default |
| **Enable** | Explicitly add the flag to enable the feature |
| **Disable** | Add the `--no-` variant to explicitly disable the feature |

Parameters with tristate support are marked with `default: on` or `default: off` in the Default column, indicating what llama.cpp's behavior is when the flag is left unset.

### Model Loading

Configure which model to load and how to load it.

| Parameter | Flag(s) | Default | Description |
|---|---|---|---|
| Model Path | `-m` <br> `--model` | *(required)* | Absolute path to the `.gguf` model file. |
| Model URL | `--model-url` | — | Download and load a model directly from a remote URL. |
| HF Repo | `--hf-repo` <br> `-hfr` | — | HuggingFace repository in `user/model:quant` format for direct Hub loading. |
| HF File | `--hf-file` <br> `-hff` | — | Specific filename within the HuggingFace repo. |
| HF Token | `--hf-token` <br> `-hft` | — | Authentication token for private HuggingFace repos. |
| Draft Model | `--model-draft` <br> `-md` | — | Secondary model used for speculative decoding (drafting tokens). |
| Vocoder Model | `--model-vocoder` | — | Audio vocoder model for speech-enabled models. |
| MMProj Path | `--mmproj` <br> `-mm` | — | Path to multi-modal projection weights for vision models. |
| MMProj URL | `--mmproj-url` <br> `-mmu` | — | Remote URL to download mmproj weights from. |
| Auto MMProj | `--mmproj-auto` <br> `--no-mmproj` | default: off | Automatically search for and load a matching mmproj file. (Tristate) |
| Offload MMProj | `--mmproj-offload` <br> `--no-mmproj-offload` | default: off | Offload the mmproj layer to GPU memory. (Tristate) |
| Aliases | `-a` <br> `--alias` | — | Comma-separated display names for the model in the API. |
| Tags | `--tags` | — | Comma-separated tags for model metadata and filtering. |

### GPU & Device Optimization

Control how computation is distributed across GPUs and CPU.

| Parameter | Flag(s) | Default | Description |
|---|---|---|---|
| GPU Layers | `-ngl` <br> `--gpu-layers` | 0 | Number of layers to offload to GPU. Use `all` or `auto` to maximize offloading. Higher values improve speed until VRAM is exhausted. |
| Devices | `--device` <br> `-dev` | — | Comma-separated list of GPU devices to use (e.g., `0,1`). |
| Split Mode | `-sm` <br> `--split-mode` | none | How work splits across GPUs: `layer` (alternate layers), `row` (split within layers), `tensor` (tensor parallelism). |
| Tensor Split | `-ts` <br> `--tensor-split` | — | Ratio of tensor weights per GPU (e.g., `3,1` for 75%/25% split). |
| Main GPU | `-mg` <br> `--main-gpu` | 0 | Primary GPU index for non-parallel work. |
| Flash Attention | `-fa` <br> `--flash-attn` | auto | Enable flash attention (`on`/`off`/`auto`) for faster processing and lower memory on long contexts. |
| KV Offload | `--kv-offload` <br> `--no-kv-offload` <br> `-kvo` | default: off | Move the Key-Value cache to GPU to reduce system RAM pressure. (Tristate) |
| Weight Repack | `--repack` <br> `--no-repack` <br> `-nr` | default: off | Repack model weights for more efficient GPU memory usage. (Tristate) |
| No Host Memory | `--no-host` | off | Disable host (CPU) memory allocation entirely. Use when VRAM is sufficient. |
| Auto Fit | `--fit` | off | Automatically determine optimal layer offloading based on available VRAM (`on`/`off`). |
| Fit Target | `-fitt` <br> `--fit-target` | — | Per-device VRAM margin in MiB to reserve when auto-fitting. |
| Fit Min Context | `-fitc` <br> `--fit-ctx` | 4096 | Minimum context size to assume when auto-fitting. |
| Op Offload | `--op-offload` <br> `--no-op-offload` | default: off | Offload additional operations (norms, embeddings) to GPU. (Tristate) |
| CPU MoE | `--cpu-moe` <br> `-cmoe` | off | Run Mixture-of-Experts layers on CPU instead of GPU. |
| N CPU MoE | `-ncmoe` <br> `--n-cpu-moe` | — | Number of expert layers to run on CPU. |
| CPU MoE Draft | `--cpu-moe-draft` <br> `-cmoed` | off | Run draft model's MoE layers on CPU. |
| N CPU MoE Draft | `-ncmoed` <br> `--n-cpu-moe-draft` | — | Number of draft expert layers to run on CPU. |

### Sampling & Generation Controls

These settings control the creativity, randomness, and coherence of model output.

| Parameter | Flag(s) | Default | Description |
|---|---|---|---|
| Samplers | `--samplers` | — | Custom sampler chain as a comma-separated list (overrides individual sampler settings). |
| Sampler Sequence | `--sampler-seq` <br> `--sampling-seq` | — | Ordered sequence of samplers to apply. |
| Seed | `-s` <br> `--seed` | -1 | Random seed for reproducibility. Use `-1` for random each time. |
| Ignore EOS | `--ignore-eos` | off | Continue generating past the end-of-sequence token. |
| Temperature | `--temp` <br> `--temperature` | 0.80 | Controls randomness. Higher (`1.2+`) = more creative; lower (`0.2`) = more deterministic. |
| Top-K | `--top-k` | 40 | Limit next-token selection to the K most likely tokens. Set to `0` to disable. |
| Top-P | `--top-p` | 0.95 | Nucleus sampling: only consider tokens within the top P probability mass. Set to `1.0` to disable. |
| Min-P | `--min-p` | 0.0 | Minimum probability threshold relative to the best token. Set to `0.0` to disable. |
| Top-N-Sigma | `--top-nsigma` <br> `--top-n-sigma` | — | Limit candidates to tokens within N standard deviations of the mean logit. |
| XTC Probability | `--xtc-probability` | 0.0 | Xtreme Token Cutting: probability of applying the filter. Set to `0.0` to disable. |
| XTC Threshold | `--xtc-threshold` | 1.0 | Minimum probability threshold for XTC filtering. Set to `1.0` to disable. |
| Typical P | `--typical` <br> `--typical-p` | 1.0 | Locally typical sampling threshold. Set to `1.0` to disable. |
| Repeat Last N | `--repeat-last-n` | -1 | Number of recent tokens to check for repetition. `-1` = full context size. |
| Repeat Penalty | `--repeat-penalty` | 1.0 | Penalty multiplier for repeated tokens. `1.0` = disabled, `1.1-1.5` typical range. |
| Presence Penalty | `--presence-penalty` | 0.0 | Flat penalty applied to any token that has appeared before. Encourages topic diversity. |
| Frequency Penalty | `--frequency-penalty` | 0.0 | Scaled penalty based on how often a token has appeared. Discourages repetition. |
| DRY Multiplier | `--dry-multiplier` | — | Disruption Repetition Reduction scaling factor. |
| DRY Base | `--dry-base` | — | DRY base penalty value. |
| DRY Allowed Length | `--dry-allowed-length` | — | Maximum repeated sequence length to ignore in DRY mode. |
| DRY Penalty Last N | `--dry-penalty-last-n` | — | Token window for DRY repetition detection. |
| Adaptive Target | `--adaptive-target` | — | Target value for adaptive repetition reduction. |
| Adaptive Decay | `--adaptive-decay` | — | Decay rate for adaptive repetition adjustment. |
| Dynamic Temp Range | `--dynatemp-range` | 0.0 | Range for dynamic temperature adjustment based on entropy. `0.0` = disabled. |
| Dynamic Temp Exp | `--dynatemp-exp` | — | Exponent controlling the sensitivity of dynamic temperature changes. |
| Mirostat | `--mirostat` | 0 | Advanced perplexity control: `0`=disabled, `1`=Mirostat, `2`=Mirostat 2.0. |
| Mirostat LR | `--mirostat-lr` | 0.10 | Learning rate for the Mirostat algorithm. |
| Mirostat Entropy | `--mirostat-ent` | 5.00 | Target entropy (information density) for Mirostat. |
| Backend Sampling | `--backend-sampling` <br> `-bs` | off | Offload sampling computation to the GPU backend. |

### Context & Batching

Control context window size, token processing, and request handling.

| Parameter | Flag(s) | Default | Description |
|---|---|---|---|
| Context Size | `-c` <br> `--ctx-size` | 0 | Maximum token context window. `0` = use model default. Larger values require more VRAM. |
| Max Predictions | `-n` <br> `--n-predict` | -1 | Maximum tokens to generate per request. `-1` = unlimited. |
| Batch Size | `-b` <br> `--batch-size` | 2048 | Tokens processed in parallel during prompt ingestion. Larger = faster prompt processing. |
| U-Batch Size | `-ub` <br> `--ubatch-size` | 512 | Internal micro-batch size for computation. Affects memory vs speed tradeoff. |
| Keep Tokens | `--keep` | 0 | Number of initial tokens to preserve during context shifting. `-1` = keep all. |
| Parallel Slots | `-np` <br> `--parallel` | 1 | Number of concurrent request slots. `-1` = auto-detect. |
| Continuous Batching | `--cont-batching` <br> `--no-cont-batching` <br> `-cb` | default: off | Enable continuous (iterative) batching for better throughput under load. (Tristate) |
| Context Shift | `--context-shift` <br> `--no-context-shift` | default: off | Allow context shifting when the window is full (drops oldest tokens). (Tristate) |
| Reverse Prompt | `-r` <br> `--reverse-prompt` | — | Stop generation when this prompt pattern appears in output. |
| Special Tokens | `--special` | off | Process special/control tokens during generation instead of treating them as text. |
| Warmup | `--warmup` <br> `--no-warmup` | default: off | Run a warmup pass on model loading to pre-compile compute graphs. (Tristate) |
| SPM Infill | `--spm-infill` | off | Enable SentencePiece infill mode for edit/completion tasks. |
| Pooling | `--pooling` | — | Pooling strategy for embedding models (e.g., `none`, `mean`, `cls`). |
| Cache Prompts | `--cache-prompt` <br> `--no-cache-prompt` | default: on | Cache processed prompts in the KV cache for reuse across requests. (Tristate) |
| Cache Reuse Min | `--cache-reuse` | 0 | Minimum prefix match length to reuse cached context. `0` = disabled. |
| Slot Prompt Similarity | `-sps` <br> `--slot-prompt-similarity` | 0.0 | Prefix similarity threshold for slot cache matching. `0.0` = disabled. |

### CPU / Threading

Fine-tune CPU utilization, thread affinity, and process priority.

| Parameter | Flag(s) | Default | Description |
|---|---|---|---|
| Threads (Gen) | `-t` <br> `--threads` | -1 | CPU threads for token generation. `-1` = use default (all available). |
| Threads (Batch) | `-tb` <br> `--threads-batch` | — | CPU threads for batch/prompt processing. Defaults to value of `--threads`. |
| CPU Mask | `-C` <br> `--cpu-mask` | — | Hex bitmask for CPU affinity during generation (e.g., `0xF`). |
| CPU Range | `-Cr` <br> `--cpu-range` | — | Comma-separated CPU core range for generation (e.g., `0-3,8-11`). |
| Strict CPU Placement | `--cpu-strict` | off | Enforce strict CPU affinity placement. |
| Priority | `--prio` | 0 | Process priority: `0`=normal, `-1`=low, `1`=medium, `2`=high, `3`=realtime. |
| Poll Level | `--poll` | 50 | Thread polling aggressiveness (0-100). Higher = more responsive but more CPU usage. |
| CPU Mask (Batch) | `-Cb` <br> `--cpu-mask-batch` | — | Hex bitmask for batch processing CPU affinity. |
| CPU Range (Batch) | `-Crb` <br> `--cpu-range-batch` | — | Core range for batch processing affinity. |
| Strict CPU (Batch) | `--cpu-strict-batch` | off | Enforce strict CPU affinity for batch threads. |
| Priority (Batch) | `--prio-batch` | — | Separate priority level for batch processing threads. |
| Poll Batch | `--poll-batch` | off | Enable polling mode for batch processing threads. |
| NUMA Mode | `--numa` | none | Non-Uniform Memory Access mode: `none`, `distribute`, `isolate`, `numactl`. |
| Threads (Draft) | `-td` <br> `--threads-draft` | — | CPU threads for draft model generation. |
| Threads Batch (Draft) | `-tbd` <br> `--threads-batch-draft` | — | CPU threads for draft model batch processing. |

### Memory

Manage memory allocation, caching strategy, and disk I/O behavior.

| Parameter | Flag(s) | Default | Description |
|---|---|---|---|
| KV Cache Type K | `-ctk` <br> `--cache-type-k` | f16 | Data type for Key cache: `f16`, `f32`, `bf16`, `q8_0`, `q4_0`, `q5_0`. Lower precision saves VRAM. |
| KV Cache Type V | `-ctv` <br> `--cache-type-v` | f16 | Data type for Value cache: same options as Key cache. |
| KV Cache K (Draft) | `-ctkd` <br> `--cache-type-k-draft` | — | Key cache type for draft model in speculative decoding. |
| KV Cache V (Draft) | `-ctvd` <br> `--cache-type-v-draft` | — | Value cache type for draft model. |
| Memory Map | `--mmap` <br> `--no-mmap` | default: on | Use memory-mapped I/O for loading model weights. Faster startup, lower RAM overhead. (Tristate) |
| Lock Memory | `--mlock` | off | Lock model in RAM to prevent swapping. Ensures consistent performance. |
| Direct I/O | `--direct-io` <br> `--no-direct-io` <br> `-dio` | default: off | Bypass OS page cache for model loading. Useful with large models on high-RAM systems. (Tristate) |
| Defrag Threshold | `-dt` <br> `--defrag-thold` | — | KV cache defragmentation threshold. Reclaims fragmented memory slots. |
| SWA Full | `--swa-full` | off | Enable full Sliding Window Attention mode for models that support it. |

### Server

HTTP server configuration, security, and API behavior.

| Parameter | Flag(s) | Default | Description |
|---|---|---|---|
| Host | `--host` | 127.0.0.1 | Bind address for the HTTP server. Use `0.0.0.0` for network access. |
| Port | `--port` | 8080 | TCP port to listen on. |
| Reuse Port | `--reuse-port` | off | Enable SO_REUSEPORT for running multiple server instances. |
| Static Path | `--path` | — | Directory to serve static files from. |
| API Prefix | `--api-prefix` | — | URL path prefix for all API endpoints. |
| Timeout | `-to` <br> `--timeout` | 600 | Request timeout in seconds. |
| HTTP Threads | `--threads-http` | -1 | Number of threads for handling HTTP requests. `-1` = auto. |
| API Key | `--api-key` | — | Bearer token required for all API requests. |
| SSL Key File | `--ssl-key-file` | — | Path to private key file for HTTPS. |
| SSL Cert File | `--ssl-cert-file` | — | Path to certificate file for HTTPS. |
| Web UI | `--webui` <br> `--no-webui` | default: on | Enable the built-in web interface. (Tristate) |
| Embeddings | `--embedding` <br> `--embeddings` | off | Run in embeddings-only mode (disables chat/completion endpoints). |
| Reranking | `--rerank` <br> `--reranking` | off | Enable reranking endpoint for search/retrieval use cases. |
| Metrics | `--metrics` | off | Expose Prometheus-compatible metrics at `/metrics`. |
| Props | `--props` | off | Enable model properties endpoint. |
| Slots Endpoint | `--slots` <br> `--no-slots` | default: on | Enable the `/slots` API endpoint for slot management. (Tristate) |
| Slot Save Path | `--slot-save-path` | — | Directory to persist slot state between restarts. |
| Media Path | `--media-path` | — | Directory for serving media files in multimodal requests. |
| LoRA Init Only | `--lora-init-without-apply` | off | Load LoRA adapters without applying them (apply later via API). |
| Sleep Idle Sec | `--sleep-idle-seconds` | -1 | Seconds of idle time before the server enters sleep mode. `-1` = never sleep. |

### Speculative Decoding

Accelerate generation using a draft model or ngram-based speculation.

| Parameter | Flag(s) | Default | Description |
|---|---|---|---|
| Draft Max Tokens | `--draft` <br> `--draft-max` | 16 | Maximum number of tokens the draft model proposes per step. |
| Draft Min Tokens | `--draft-min` <br> `--draft-n-min` | 0 | Minimum draft tokens required before verification. |
| Draft P Min | `--draft-p-min` | 0.75 | Minimum acceptance probability threshold for draft tokens. |
| Draft Context Size | `-cd` <br> `--ctx-size-draft` | — | Context size for the draft model (defaults to main context). |
| Devices (Draft) | `-devd` <br> `--device-draft` | — | GPU devices assigned to the draft model. |
| GPU Layers (Draft) | `-ngld` <br> `--gpu-layers-draft` | — | Number of draft model layers to offload to GPU. |
| Spec Type | `--spec-type` | none | Speculation method: `none`, `ngram-cache`, `ngram-simple`, `ngram-map-k`, `draft-mtp`. |
| Ngram Size N | `--spec-ngram-size-n` | 12 | Minimum n-gram size for ngram-based speculation. |
| Ngram Size M | `--spec-ngram-size-m` | 48 | Maximum n-gram size for ngram-based speculation. |
| Ngram Min Hits | `--spec-ngram-min-hits` | — | Minimum historical hits required before an n-gram is used for speculation. |
| Draft N Max | `--spec-draft-n-max` | — | Maximum number of draft tokens for MTP speculative decoding. |
| Override Tensor Draft | `-otd` <br> `--override-tensor-draft` | — | Tensor override pattern for the draft model. |

### Chat & Templates

Control chat formatting, reasoning behavior, and template handling.

| Parameter | Flag(s) | Default | Description |
|---|---|---|---|
| Chat Template | `--chat-template` | auto | Built-in template: `auto`, `chatml`, `llama3`, `mistral-v3`, `deepseek`, `gemma`, `phi3`. |
| Chat Template File | `--chat-template-file` | — | Path to a custom Jinja2 chat template file. |
| Chat Template Kwargs | `--chat-template-kwargs` | — | JSON string of extra variables for the template (e.g., `{"preserve_thinking":true}`). |
| Use Jinja | `--jinja` <br> `--no-jinja` | default: off | Force use of Jinja2 templating instead of built-in templates. (Tristate) |
| Reasoning Format | `--reasoning-format` | auto | Output format for reasoning models: `auto`, `none`, `deepseek`. |
| Reasoning | `-rea` <br> `--reasoning` | auto | Enable/disable reasoning output: `auto`, `on`, `off`. |
| Reasoning Budget | `--reasoning-budget` | -1 | Maximum tokens allocated for reasoning. `-1` = unrestricted. |
| Reasoning Budget Msg | `--reasoning-budget-message` | — | Custom message appended when the reasoning budget is exceeded. |
| Skip Chat Parsing | `--skip-chat-parsing` <br> `--no-skip-chat-parsing` | default: off | Bypass chat template parsing and send raw content to the model. (Tristate) |
| Prefill Assistant | `--prefill-assistant` <br> `--no-prefill-assistant` | default: off | Prefill the assistant role token to steer generation start. (Tristate) |

### Checkpoints & Cache

Manage context checkpointing, RAM caching, and lookup strategies.

| Parameter | Flag(s) | Default | Description |
|---|---|---|---|
| Context Checkpoints | `-ctxcp` <br> `--ctx-checkpoints` | 32 | Number of context checkpoints to maintain for fast recovery. |
| Checkpoint Every N | `-cpent` <br> `--checkpoint-every-n-tokens` | — | Create a checkpoint every N generated tokens. |
| Cache RAM | `-cram` <br> `--cache-ram` | -1 | Maximum RAM (MiB) allocated for the KV cache. `-1` = no limit. |
| Unified KV Buffer | `--kv-unified` <br> `--no-kv-unified` <br> `-kvu` | default: off | Use a single unified buffer for all KV caches instead of per-slot allocation. (Tristate) |
| Cache Idle Slots | `--cache-idle-slots` <br> `--no-cache-idle-slots` | default: off | Preserve cached context in idle (inactive) slots. (Tristate) |
| Lookup Cache Static | `-lcs` <br> `--lookup-cache-static` | — | Static lookup cache size for prefix matching. |
| Lookup Cache Dynamic | `-lcd` <br> `--lookup-cache-dynamic` | — | Dynamic lookup cache size that scales with usage. |

### Logging

Control log output, formatting, and diagnostic information.

| Parameter | Flag(s) | Default | Description |
|---|---|---|---|
| Verbosity | `-lv` <br> `--log-verbosity` | 0 | Log level: `0`=generic, `1`=error, `2`=warning, `3`=info, `4`=debug. |
| Log File | `--log-file` | — | Path to write log output to a file. |
| Log Colors | `--log-colors` | auto | Terminal color support: `auto`, `on`, `off`. |
| Log Prefix | `--log-prefix` | off | Prepend timestamp and level to each log line. |
| Timestamps | `--log-timestamps` | off | Include detailed timestamps in log output. |
| Verbose (All) | `-v` <br> `--verbose` | off | Enable maximum verbosity for all subsystems. |
| Log Disable | `--log-disable` | off | Suppress all log output. |
| Offline Mode | `--offline` | off | Disable network access (HuggingFace downloads, updates). |
| Performance Stats | `--perf` <br> `--no-perf` | default: on | Print timing and performance statistics after generation. (Tristate) |
| Escape Output | `-e` <br> `--escape` <br> `--no-escape` | default: off | Escape special characters in output for safe programmatic consumption. (Tristate) |

### Advanced / Override

Low-level model overrides, grammar constraints, and RoPE configuration.

| Parameter | Flag(s) | Default | Description |
|---|---|---|---|
| RoPE Scaling | `--rope-scaling` | none | Positional encoding scaling method: `none`, `linear`, `yarn`. |
| RoPE Scale | `--rope-scale` | — | Manual scaling factor for RoPE embeddings. |
| RoPE Freq Base | `--rope-freq-base` | — | Override the base frequency of RoPE positional encodings. |
| RoPE Freq Scale | `--rope-freq-scale` | — | Scale factor applied to RoPE frequencies for context extension. |
| YaRN Orig Ctx | `--yarn-orig-ctx` | — | Original context size the model was trained on (for YaRN scaling). |
| YaRN Ext Factor | `--yarn-ext-factor` | — | YaRN extrapolation multiplier for extending context beyond training length. |
| YaRN Attn Factor | `--yarn-attn-factor` | — | YaRN attention scaling factor. |
| YaRN Beta Slow | `--yarn-beta-slow` | — | YaRN interpolation beta for slow frequency components. |
| YaRN Beta Fast | `--yarn-beta-fast` | — | YaRN interpolation beta for fast frequency components. |
| Grammar (inline) | `--grammar` | — | Inline BNF grammar string to constrain output format. |
| Grammar File | `--grammar-file` | — | Path to a `.gbnf` grammar file for structured output. |
| JSON Schema (inline) | `-j` <br> `--json-schema` | — | Inline JSON schema to validate and constrain generated JSON. |
| JSON Schema File | `-jf` <br> `--json-schema-file` | — | Path to a JSON schema file. |
| Check Tensors | `--check-tensors` | off | Validate tensor shapes and types on model load (debugging). |
| Image Min Tokens | `--image-min-tokens` | — | Minimum token allocation for image features in multimodal models. |
| Image Max Tokens | `--image-max-tokens` | — | Maximum token allocation for image features. |

### Complex Tables

Some parameters support multiple entries and are stored as tables rather than single values.

#### LoRA Adapters (`--lora`)
Attach fine-tuned adapter weights with individual scaling factors. Each entry has a `path` to the `.bin` or `.safetensors` file and a `scale` multiplier (e.g., `1.0`).

#### Logit Biases (`--logit-bias`)
Bias specific token IDs toward or away from selection. Each entry specifies a `token_id` and a `bias_value` (positive = encourage, negative = discourage).

#### Control Vectors (`--control-vector`)
Apply directional control vectors to steer model behavior. Each entry includes a `path`, `scale`, and optional `layer_range_start` / `layer_range_end`.

#### Override KV (`--override-kv`)
Override internal model key-value parameters. Each entry has a `key_name`, `key_type` (`int`, `float`, `bool`, `str`), and `key_value`. Useful for patching model metadata without modifying the file.

#### Override Tensors (`--override-tensor`)
Replace or zero-out specific tensors by pattern match. Each entry specifies a `tensor_pattern` (regex) and `buffer_type` for the replacement buffer.

#### DRY Sequence Breakers (`--dry-sequence-breaker`)
Characters that reset the DRY repetition counter. Common values include newline (`\n`) and period (`.`).

---

## Benchmarking

`llama-manager` includes a built-in benchmarking tool to help you quantitatively compare different configurations.

### How Benchmarking Works
When you trigger a benchmark, the manager:
1.  Sends a standardized test prompt to the currently running server.
2.  Measures the time taken to generate a response.
3.  Queries system tools (`nvidia-smi`, `psutil`) to capture resource usage.
4.  Saves the results to the version's history.

### Key Metrics Captured
*   **TPS (Tokens Per Second)**: The most critical metric for speed. It represents how fast the model generates text.
*   **VRAM Usage (MB)**: The total amount of GPU memory consumed by the model and the KV cache.
*   **Peak CPU %**: The maximum CPU load detected during the generation process.
*   **Duration**: The total wall-clock time for the benchmark request.

**Pro-Tip**: Use benchmarking to find the "sweet spot" for `gpu_layers` and `context_size` where you maximize TPS without exceeding your available VRAM.

---

## API Reference

For developers looking to integrate with `llama-manager`, the following REST endpoints are available. All responses are JSON unless noted otherwise.

### Base URL
The API is served on the same port as the web interface (default: `http://127.0.0.1:8081`).

### Endpoints

#### List Models
`GET /api/models`

Retrieves a list of available `.gguf` models in a specified directory. Scans are constrained to `LLAMA_MODEL_DIR`.

**Query Parameters:**
| Parameter | Type | Description |
|---|---|---|
| `dir` | `string` | (Optional) Subdirectory under `MODEL_DIR` to scan. Path traversal is blocked. |

**Response Example:**
```json
[
  {
    "path": "/models/llama-3-8b.gguf",
    "name": "llama-3-8b.gguf",
    "rel": "llama-3-8b.gguf"
  }
]
```

#### Get Version Data
`GET /api/version/<int:version_id>/data`

Returns the complete, structured configuration data for a specific version. This includes all category-specific settings and complex tables (LoRAs, Logit Biases, etc.).

**URL Parameters:**
| Parameter | Type | Description |
|---|---|---|
| `version_id` | `integer` | The unique ID of the version. |

**Response Example:**
```json
{
  "categories": {
    "model_loading": { "model_path": "/path/to/model.gguf", ... },
    "sampling": { "temperature": 0.8, ... }
  },
  "complex": {
    "lora_adapters": [{ "path": "/path/to/lora.bin", "scale": 1.0 }],
    "logit_biases": [...]
  }
}
```

#### Server Status
`GET /server/status`

Returns the running/stopped status of the managed llama-server process, including the currently active version ID and details if running. Returns JSON or HTML depending on request headers (HTMX-aware).

**Response Example:**
```json
{
  "running": true,
  "pid": 12345,
  "version_id": 7,
  "config_name": "My Config",
  "version_number": 3
}
```

#### Start Server
`POST /server/start/<int:version_id>`

Starts the llama-server with the specified version's configuration. Rate-limited to 1 call per 30 seconds.

**Response Example:**
```json
{
  "success": true,
  "message": "Server started (v7)"
}
```

#### Stop Server
`POST /server/stop`

Stops the running llama-server process. Rate-limited to 3 calls per 60 seconds.

**Response Example:**
```json
{
  "success": true,
  "message": "Server stopped"
}
```

#### Get Logs
`GET /server/logs?lines=50`

Returns the last N lines from the llama-server log file.

**Query Parameters:**
| Parameter | Type | Description |
|---|---|---|
| `lines` | `integer` | (Optional) Number of recent lines to return. Defaults to 50. |

#### Stream Logs (SSE)
`GET /server/stream-logs`

Server-Sent Events endpoint that streams real-time stdout from the running llama-server process. Returns `text/event-stream`.

**Headers:**
| Header | Value | Description |
|---|---|---|
| `Cache-Control` | `no-cache` | Prevents browser caching |
| `X-Accel-Buffering` | `no` | Disables nginx buffering for SSE |

#### Run Benchmark
`POST /version/<int:version_id>/benchmark`

Triggers a benchmark run against the currently active server. Rate-limited to 1 call per 120 seconds. Sends a test prompt, measures TPS, captures VRAM via `nvidia-smi`, and CPU usage via `psutil`.

**Response Example:**
```json
{
  "success": true,
  "tps": 45.2,
  "tokens_generated": 128,
  "duration_sec": 2.83,
  "vram_used_mb": 4096,
  "peak_cpu_pct": 78.5,
  "error": null
}
```

#### Import Running Config
`POST /server/import-config`

Captures the current running server's command-line flags and imports them as a new version (or updates existing config if settings match). Accepts form data with `config_name`.

**Response Example:**
```json
{
  "success": true,
  "message": "Config imported (24 flags)",
  "config_id": 3,
  "version_id": 12
}
```

#### Common Options
`GET /common-options`

Returns the HTML page for managing common options (pinned fields shown on every version edit form).

`POST /common-options/toggle`

Add or remove a field from common options. Accepts JSON with `category`, `column_name`, and `add` (boolean).

`POST /common-options/reorder`

Reorder common options via drag-and-drop. Accepts JSON with `order` (list of option IDs).

`POST /common-options/remove/<int:option_id>`

Remove a common option preset.

`POST /common-options/update-label/<int:option_id>`

Rename a common option preset. Accepts form data with `custom_label`.

#### Command Diff
`GET /api/benchmarks/diff`

Compares the generated command lines between two versions. Returns flags that were added, removed, or changed.

**Query Parameters:**
| Parameter | Type | Description |
|---|---|---|
| `v1` | `integer` | First version ID to compare |
| `v2` | `integer` | Second version ID to compare |

**Response Example:**
```json
{
  "version_1": { "id": 5, "version_number": 2, "config_name": "My Config" },
  "version_2": { "id": 7, "version_number": 3, "config_name": "My Config" },
  "added": [{ "flag": "--flash-attn", "value": null }],
  "removed": [{ "flag": "--no-mmap", "value": null }],
  "changed": [{ "flag": "-ngl", "old_value": "20", "new_value": "35" }],
  "command_1": "llama-server -m /path/to/model.gguf -ngl 20 --no-mmap",
  "command_2": "llama-server -m /path/to/model.gguf -ngl 35 --flash-attn"
}
```

#### Command Preview
`GET /version/<int:version_id>/command`

Returns the full command line for a version with secrets redacted.

**Response Example:**
```json
{
  "command": "llama-server -m /path/to/model.gguf -ngl 35 --host 0.0.0.0 --port 8080"
}
```

#### Config Benchmarks
`GET /config/<int:config_id>/benchmarks`

Returns the benchmark history page for all versions of a config.

#### Benchmark Comparison
`GET /benchmarks/compare`

Returns the cross-config benchmark comparison page. Optionally filter by one or more `config_id` query parameters.

#### Version Deletion
`POST /version/<int:version_id>/delete`

Deletes a version and all its associated data. Cannot delete the currently running version.

#### Version Duplication
`POST /version/<int:version_id>/duplicate`

Creates an exact copy of a version. Redirects to the edit form for the new version.

---

### Authentication
If `AUTH_ENABLED=true`, all endpoints require HTTP Basic Auth with the configured username and password. CSRF tokens are required for state-changing POST requests when accessed via browser sessions.
