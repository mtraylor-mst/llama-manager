# Benchmarking Guide

This document explains how `llama-manager` benchmarks work under the hood — what requests are sent, how metrics are captured, and how to interpret the results.

## Overview

The benchmark feature sends a standardized completion request to your running `llama-server`, measures generation speed, and captures system resource usage. Results are stored in the database for historical comparison across versions.

**Endpoint**: `POST /version/<int:version_id>/benchmark`  
**Rate Limit**: 1 call per 120 seconds (to prevent benchmark spam during tuning).

---

## How It Works

### Step-by-Step Flow

When you trigger a benchmark from the UI or API, the following sequence occurs:

1. **Resolve Server Address**
   The benchmark service reads the version's stored `server` settings (`host`, `port`). Falls back to defaults if not set:
   - Default host: `127.0.0.1`
   - Default port: `8080`

2. **VRAM Snapshot (Before)**
   Runs `nvidia-smi --query-gpu=memory.used` to capture baseline GPU memory usage. This value is captured but not used directly in the final report — it establishes a pre-benchmark baseline.

3. **Send Completion Request**
   A POST request is sent to the llama-server's `/completion` endpoint with a fixed test prompt and generation parameters (see "Request Details" below).

4. **Measure Response Time**
   Wall-clock duration is measured from request send to full response receipt. TPS is calculated either from server-reported timing data or estimated from token count / duration.

5. **VRAM Snapshot (After)**
   Runs `nvidia-smi` again to capture total GPU memory consumed by the loaded model and KV cache. This is the value reported as `vram_used_mb`.

6. **CPU Usage Sample**
   Calls `psutil.cpu_percent(interval=1)` for a 1-second blocking sample of overall CPU utilization during benchmark execution.

7. **Persist Results**
   All metrics are saved to the database via `save_performance_metric()` and associated with the version's history.

---

## Request Details

### Test Prompt

The default test prompt is defined in `services/benchmarks.py`:

```python
TEST_PROMPT = "Write a short paragraph about the importance of version control in software development."
```

This prompt is approximately 30 tokens — generic enough to work with any model, and long enough to produce meaningful generation timing.

### Request Payload

The benchmark sends this JSON body to `http://<host>:<port>/completion`:

```json
{
  "prompt": "Write a short paragraph about the importance of version control in software development.",
  "n_predict": 128,
  "temperature": 0.8,
  "top_k": 40,
  "top_p": 0.95
}
```

| Field | Value | Purpose |
|---|---|---|
| `prompt` | Test prompt above | Input text for the model to continue |
| `n_predict` | `128` | Number of tokens to generate (fixed for consistency) |
| `temperature` | `0.8` | Moderate randomness — balanced between creative and deterministic |
| `top_k` | `40` | Token pool size limit |
| `top_p` | `0.95` | Nucleus sampling threshold |

These parameters are intentionally fixed so benchmark results are comparable across runs. The goal is measuring raw generation speed, not evaluating output quality.

### Timeout Behavior

The HTTP request has a **120-second timeout**. If the server does not respond within this window (e.g., very large context, slow CPU-only inference), the benchmark fails with an error.

---

## Metrics Explained

### TPS (Tokens Per Second)

**Primary speed metric.** How many tokens the model generates per second during the completion request.

- **Server-reported**: If llama-server returns timing data in its response (`timing.generation_ms`), TPS is calculated as `1000 / ms_per_token`. This is the most accurate value.
- **Estimated fallback**: If server timing data is unavailable, TPS is estimated as `tokens_generated / duration_sec`.

**Interpretation**: Higher is faster. A typical GPU-offloaded 7B model might achieve 30-80 TPS depending on hardware. CPU-only inference may be 5-20 TPS.

### VRAM Used (MB)

Total GPU memory consumed after the benchmark, measured via `nvidia-smi`. This includes:
- Model weights loaded to GPU
- KV cache for active context windows
- Any other GPU allocations by llama-server

**Interpretation**: Compare this against your GPU's total VRAM to understand headroom. If you're near capacity, reducing `gpu_layers` or `ctx_size` may be necessary.

### Peak CPU %

Overall system CPU utilization sampled over 1 second during benchmark execution via `psutil.cpu_percent(interval=1)`. This is a blocking call that measures average CPU usage across all cores during the interval.

**Interpretation**: High values (80%+) indicate CPU-bound operation — either the model isn't fully GPU-offloaded, or you're running other resource-intensive processes.

### Duration (seconds)

Wall-clock time from sending the HTTP request to receiving the full response. Includes network overhead, prompt processing (prefill), and token generation.

**Interpretation**: For a fixed 128-token request, shorter duration means faster overall throughput. Useful for comparing end-to-end latency between configurations.

### Tokens Generated

Actual number of tokens returned by the server in the completion response. Typically matches `n_predict` (128), but may be lower if the model generates an EOS token early or the request is truncated.

---

## Interpreting Results

### Finding Your GPU Layers Sweet Spot

The most common use case for benchmarking is determining optimal `gpu_layers`:

1. Start with a conservative value (e.g., 20 layers)
2. Run benchmark, note TPS and VRAM used
3. Increase gpu_layers by 10-20
4. Repeat until TPS plateaus or VRAM approaches your GPU's limit
5. The highest gpu_layers value before the plateau is your sweet spot

### Comparing Configurations

Because benchmarks are stored per-version in the database, you can compare:
- Same model with different `gpu_layers` values
- Different context sizes (`ctx_size`) to see memory impact
- Flash attention enabled vs disabled
- Different batch sizes for throughput optimization

### Common Issues

| Symptom | Likely Cause | Fix |
|---|---|---|
| TPS = 0, "Connection failed" error | Server not running or wrong host/port | Verify server is started and `server.host`/`server.port` match |
| Very low TPS (<5) | CPU-only inference or VRAM overflow | Increase `gpu_layers` or reduce model size |
| High VRAM but low TPS | KV cache overhead from large context | Reduce `ctx_size` or enable flash attention (`--fa`) |
| Benchmark times out (>120s) | Extremely slow generation (CPU, small batch) | Check hardware capabilities; consider smaller models for CPU-only use |

---

## Dependencies

Benchmarking requires these system tools:

- **nvidia-smi**: Part of NVIDIA GPU drivers. Used to query VRAM usage. On non-NVIDIA systems, `vram_used_mb` will be `null`.
- **psutil**: Python package (included in `requirements.txt`). Used for CPU usage sampling. Falls back gracefully if unavailable — `peak_cpu_pct` will be `null`.

---

## API Response Example

Successful benchmark:

```json
{
  "success": true,
  "tps": 52.3,
  "tokens_generated": 128,
  "duration_sec": 2.45,
  "vram_used_mb": 4608,
  "peak_cpu_pct": 35.2,
  "error": null
}
```

Failed benchmark (server unreachable):

```json
{
  "success": false,
  "tps": 0,
  "tokens_generated": 0,
  "duration_sec": 0,
  "vram_used_mb": null,
  "peak_cpu_pct": 12.5,
  "error": "Connection failed — is llama-server running?"
}
```
