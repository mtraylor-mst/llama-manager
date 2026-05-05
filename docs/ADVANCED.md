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

For developers looking to integrate with `llama-manager`, the following REST endpoints are available.

### Base URL
The API is served on the same port as the web interface (default: `http://127.0.0.1:5000`).

### Endpoints

#### List Models
`GET /api/models`

Retrieves a list of available `.gguf` models in a specified directory.

**Query Parameters:**
| Parameter | Type | Description |
|---|---|---|
| `dir` | `string` | (Optional) The directory to scan for models. |

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
