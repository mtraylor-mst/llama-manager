# Advanced Features & Optimization

This guide covers the technical details for fine-tuning model performance and interacting with the `llama-manager` API.

## Parameter Reference

The following parameters are used to configure the `llama-server`. They are organized by functional category to help you optimize your setup.

### Model Loading
*   **Model Path**: The absolute path to the `.gguf` file.
*   **Model URL**: Load a model directly from a URL.
*   **HuggingFace Integration**: Specify `hf-repo`, `hf-file`, or `hf-token` to load models directly from the HuggingFace Hub.
*   **LoRA Adapters**: Attach multiple LoRA adapters with specific scaling factors.
*   **Multimedia**: Configure Multi-modal projection (`mmproj`) for vision-enabled models.

### GPU & Device Optimization
*   **GPU Layers (`-ngl`)**: Determines how many layers are offloaded to the GPU. Increasing this improves speed until VRAM is exhausted.
*   **Flash Attention**: Enable `--fa` to speed up processing and reduce memory usage for long contexts.
*   **Split Mode & Tensor Split**: For multi-GPU setups, define how work is distributed across devices.
*   **KV Offload**: Move the Key-Value cache to the GPU to save system RAM.

### Sampling & Generation Controls
These settings control the "creativity" and randomness of the model output.
*   **Temperature**: Higher values (e.g., `1.2`) increase randomness; lower values (e.g., `0.2`) make the model more deterministic.
*   **Top-K / Top-P**: Limits the pool of potential next tokens to improve coherence.
*   **Repeat Penalty**: Reduces the likelihood of the model repeating the same phrases.
*   **Mirostat**: An advanced algorithm for controlling perplexity and maintaining consistent output quality.

### Context & Batching
*   **Context Size (`-c`)**: The maximum number of tokens the model can consider. Larger contexts require significantly more VRAM.
*   **Batch Size (`-b`)**: Controls how many tokens are processed in parallel during the prompt ingestion phase.
*   **Parallelism (`-np`)**: Allows the server to handle multiple requests simultaneously.

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

Returns the list of pinned common option presets for quick configuration.

**Response Example:**
```json
[
  {
    "id": 1,
    "label": "Fast Chat",
    "order": 0,
    "config": { "temperature": 0.7, "top_p": 0.9, ... }
  }
]
```

`POST /common-options/toggle` — Enable/disable a common option preset.
`POST /common-options/reorder` — Reorder the pinned options list.
`POST /common-options/remove/<int:option_id>` — Remove a common option preset.
`POST /common-options/update-label/<int:option_id>` — Rename a common option preset.

---

### Authentication
If `AUTH_ENABLED=true`, all endpoints require HTTP Basic Auth with the configured username and password. CSRF tokens are required for state-changing POST requests when accessed via browser sessions.
