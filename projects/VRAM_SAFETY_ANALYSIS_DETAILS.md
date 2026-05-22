# VRAM Safety & OOM Prediction — Implementation Plan

## Objective

Build a stress-test runner that empirically measures compaction behavior, stores model
metadata for predictive calculations, and displays color-coded safety indicators on the
config view page. Supports single GPU (RTX 3090, 24GB VRAM). Models tested: Qwen3.6-27B,
Devstral, Gemma.

## Files to Create/Modify

### New files
- `services/model_parser.py` — Parse architecture metadata from llama-server logs
- `services/vram_monitor.py` — Background VRAM polling thread (100ms interval)
- `services/vram_stress_test.py` — Stress test orchestrator with background thread + progress tracking
- `services/vram_safety.py` — Theoretical estimate + empirical safety calculator
- `templates/configs/_vram_safety.html` — Partial template for safety card
- `templates/configs/_stress_test_status.html` — Partial template for test progress/results
- `data/wikitext.txt` — Downloaded wikitext-v2 (gitignored)

### Modified files
- `schema.sql` — Add 3 new tables
- `models/configs.py` — Add CRUD for new tables
- `routes/server.py` — Add stress test + safety API endpoints
- `templates/configs/view.html` — Include safety card partial
- `.gitignore` — Add `data/wikitext.txt`

---

## Phase 1: Database Schema (`schema.sql`)

```sql
CREATE TABLE model_metadata (
    model_path VARCHAR(2048) PRIMARY KEY,
    architecture VARCHAR(50),
    n_layers INT,
    n_embd INT,
    n_head INT,
    n_head_kv INT,
    n_ctx_train INT,
    key_length INT,
    value_length INT,
    file_size_bytes BIGINT,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE vram_stress_tests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    version_id INT NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    status VARCHAR(20) DEFAULT 'running',  -- running/completed/failed/cancelled
    total_vram_mb INT,
    compaction_coefficient DECIMAL(6,4),
    failure_ctx_tokens INT NULL,
    model_weight_size_mb INT,
    kv_per_token_bytes DECIMAL(8,4),  -- empirically derived
    FOREIGN KEY (version_id) REFERENCES config_versions(id) ON DELETE CASCADE
);

CREATE TABLE vram_stress_data_points (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stress_test_id INT NOT NULL,
    ctx_tokens INT NOT NULL,
    vram_used_mb INT,
    peak_vram_mb INT,
    tps DECIMAL(8,2),
    FOREIGN KEY (stress_test_id) REFERENCES vram_stress_tests(id) ON DELETE CASCADE
);
```

## Phase 2: Model Parser (`services/model_parser.py`)

Parse architecture metadata from llama-server log files. Extracts from both `print_info:`
lines and GGUF KV metadata.

### Key functions
- **`parse_log(log_path)`** — Parses a log file, returns dict of architecture info
- **`parse_memory_breakdown(log_path)`** — Extracts the `common_memory_breakdown_print` line
  to estimate context VRAM per token and free headroom
- **`get_or_parse_metadata(model_path, log_path)`** — Checks DB first, parses if missing, stores result

### Regex patterns (from observed log format)

```
print_info: n_layer               = 64
print_info: n_embd                = 5120
print_info: n_head_kv             = 4
file size   = 15.65 GiB (5.00 BPW)
common_memory_breakdown_print: | ... | 24124 = 23259 + (20791 = 15345 +    4950 +     495) + ...
```

The memory breakdown line format:
`total = free + (self = model + context + compute) + unaccounted`

From this we derive estimated max context: `free_vram_mb / (context_mb / default_ctx_tokens) * n_ctx_train`

## Phase 3: VRAM Monitor (`services/vram_monitor.py`)

Background thread that polls `nvidia-smi` at 100ms intervals.

### Class interface

```python
class VramMonitor:
    def start(self):
        """Start background thread polling nvidia-smi at 100ms."""

    def stop(self):
        """Stop thread, return collected data points as list of (timestamp, used_mb)."""

    def get_peak(self):
        """Return max VRAM observed so far (thread-safe). Returns MB or None."""

    @staticmethod
    def get_total_vram():
        """One-shot: query memory.total from nvidia-smi. Returns MB."""
```

Thread-safe list of `(timestamp, used_mb)` tuples. Peak is computed on-demand via `max()`.

## Phase 4: Stress Test Runner (`services/vram_stress_test.py`)

### Workflow

1. **Parse model metadata** from existing log file (or quick startup probe if no log exists)
2. **Estimate failure zone** from memory breakdown:
   - Parse context VRAM allocation per token from `common_memory_breakdown_print`
   - Calculate estimated max context: `free_vram_mb / context_per_token_mb`
3. **Phase A — Aggressive steps**: Test at 1k, 2k, 4k, 8k, 16k, 32k, ... up to 80% of estimated failure
   - At each step: send completion request with prompt of that token count, measure VRAM
4. **Phase B — Fine granularity**: From last successful Phase A step toward estimated failure,
   test at 512-token increments (configurable)
5. **Derive metrics**:
   - `kv_per_token_bytes` = linear regression slope of (vram_used_mb * 1024*1024) vs ctx_tokens
   - `compaction_coefficient` = max(peak_vram / steady_vram - 1) across all steps
   - `failure_ctx_tokens` = last step before OOM or crash

### Token-accurate prompts

Use llama-server `/tokenize` endpoint to verify prompt length. Use wikitext-v2 as source text,
sliced and padded to exact token counts. If wikitext not available yet, download on first run:
- Download from `https://s3.amazonaws.com/research.metamind.io/wikitext/wikitext-2-raw-v1.zip`
- Extract `wiki.test.raw`, store as `data/wikitext.txt`

### Background execution

- `run_stress_test(version_id)` — spawns daemon thread, stores test record with `status=running`
- Thread updates status/data points in DB as it progresses
- `get_stress_test_status(test_id)` — returns current progress for polling
- Only one stress test runs at a time (reject concurrent requests)

### Thread safety

Use a global dict of active test threads keyed by test_id, with locks for shared state.
Thread is daemon=True so it won't block app shutdown.

## Phase 5: Safety Calculator (`services/vram_safety.py`)

### Theoretical estimate (available immediately, no test needed)

```python
def theoretical_estimate(version_id):
    meta = get_model_metadata(model_path)
    config = get_version_config(version_id)

    # Weight size from file
    weight_size_mb = meta.file_size_bytes / (1024*1024)

    # KV cache per token (attention-based, approximate for hybrids)
    head_dim = meta.n_embd / meta.n_head
    kv_per_token = 2 * meta.n_layers * meta.n_head_kv * head_dim * kv_quant_bytes(config.cache_type_k)

    # Predicted peak with conservative compaction buffer (10% default)
    predicted_peak = weight_size_mb + (config.ctx_size * kv_per_token / 1024/1024) * 1.10

    return {
        "weight_size_mb": ...,
        "kv_cache_mb": ...,
        "predicted_peak_mb": ...,
        "total_vram_mb": ...,
        "margin_pct": ...,
        "status": "green" | "yellow" | "red",
        "source": "theoretical",
    }
```

### Empirical calculation (uses stress test data, overrides theoretical)

Same formula but with real `compaction_coefficient` and `kv_per_token_bytes` from stress test.
Source label changes to `"empirical"` for high-confidence display.

### Combined entry point

`get_safety(version_id)` returns empirical if available, falls back to theoretical.

### Color thresholds (configurable, defaults)

- **Green**: margin >= 20%
- **Yellow**: margin 5% to 20%
- **Red**: margin < 5%

## Phase 6: Routes (`routes/server.py` additions)

```python
@bp.route("/version/<int:version_id>/vram-safety")
def vram_safety(version_id):
    """GET — Return safety calculation (JSON)."""

@bp.route("/version/<int:version_id>/vram-stress-test", methods=["POST"])
@rate_limit(max_calls=1, period=3600)  # One test per hour
def start_stress_test(version_id):
    """POST — Start a stress test in background thread."""

@bp.route("/version/<int:version_id>/vram-stress-test/latest")
def latest_stress_test(version_id):
    """GET — Get most recent stress test status/results (JSON)."""

@bp.route("/vram-stress-test/<int:test_id>")
def stress_test_status(test_id):
    """GET — Poll for stress test progress (JSON, used by HTMX polling)."""
```

## Phase 7: UI Templates

### `_vram_safety.html` partial (shown on config view page)

- Color-coded badge (green/yellow/red) with margin percentage
- Breakdown: weight size, KV cache estimate, predicted peak vs total VRAM
- Source label: "Theoretical Estimate" or "Based on Stress Test"
- "Run Stress Test" button if no empirical data exists
- If stress test data exists: show compaction coefficient and failure threshold

### `_stress_test_status.html` partial (shown when test is running or completed)

- Running: progress bar, current step, elapsed time, live VRAM readout
- Completed: table of data points (ctx_tokens, vram_used_mb, peak_vram_mb, tps),
  derived coefficients, link to rerun

Both use HTMX polling (`hx-get` with `hx-trigger="every 5s"`) for live updates.

## Phase 8: Tests

- `tests/test_model_parser.py` — Parse known log content, verify extracted values
- `tests/test_vram_monitor.py` — Mock nvidia-smi, verify peak tracking
- `tests/test_vram_safety.py` — Theoretical + empirical calculations with known inputs
- `tests/test_vram_stress_test.py` — Orchestration with mocked server/API calls

## Additional Notes

### Single-GPU assumption

All nvidia-smi queries target device 0. Total VRAM is queried once at test start and stored
in the stress test record.

### Theoretical vs empirical comparison

The safety card shows both when available, with a confidence indicator:
- Theoretical = "Low confidence" (uses 10% default compaction buffer)
- Empirical = "High confidence" (measured from actual GPU behavior)

This enables comparing and refining the theoretical formula over time.

### KV cache quantization bytes reference

| Quantization | Bytes per element |
|-------------|-------------------|
| f16         | 2                 |
| q8_0        | 1                 |
| q4_0        | 0.5               |
| q5_0        | 0.625             |

### Wikitext download

On first stress test run, check if `data/wikitext.txt` exists. If not, download and extract.
Add `data/wikitext.txt` to `.gitignore`.
