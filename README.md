# llama-manager

Track, compare, and launch [llama.cpp](https://github.com/ggerganov/llama.cpp) server configurations from a web interface.

## Features

- **Import running configs** — captures the full command line from a live `llama-server` process and stores it as a versioned config
- **Grouped by model** — imports are automatically grouped under the model filename, with new versions added when settings change
- **Version history** — each config tracks multiple versions so you can iterate on settings without losing what worked
- **Fork & duplicate** — create new versions from any existing version, or duplicate a version as-is
- **Launch & stop** — starts `llama-server` directly via subprocess with PID tracking for reliable process management
- **Pre-launch validation** — checks model file existence, VRAM fit estimates, and value sanity before starting a server
- **Live logs** — SSE-streamed server output in real-time on the config view page
- **Command preview** — generates and displays the full command line with secret redaction
- **Benchmarking** — run TPS benchmarks, track VRAM/CPU usage, and compare performance per version
- **Server health monitoring** — pings the llama-server HTTP API to confirm responsiveness, displayed in the nav bar
- **VRAM safety analysis** — theoretical VRAM usage estimates with color-coded safety indicators
- **VRAM stress testing** — binary search to find the maximum context size before OOM
- **Config templates** — save parameterized presets from existing versions for rapid deployment
- **Usage analytics** — track launch frequency, runtime, and failure modes across configs
- **Common options** — pin frequently-used fields to a compact quick-edit panel
- **Command diff** — compare two versions and see exactly which flags were added, removed, or changed
- **Benchmark comparison** — view benchmarks across all versions of a config, or compare multiple configs side-by-side
- **Version management** — fork, duplicate, and delete versions to iterate safely
- **HTTP Basic Auth** — optional authentication layer for protected deployments
- **CSRF protection** — Flask-WTF CSRF tokens on all state-changing requests

## Setup

```bash
# Create and activate a virtual environment
uv venv --python 3.10 --seed
source .venv/bin/activate

pip install -r requirements.txt
# Initialize the database (run schema.sql against your MySQL/MariaDB server)
mysql -h $HOST -u $USER -p llama_configs < schema.sql
# Configure via .env file or environment variables
python run.py
```

For detailed prerequisites, virtual environment setup, and database initialization, see [Setup & Installation](docs/SETUP.md).

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `LLAMA_DB_HOST` | `127.0.0.1` | Database host |
| `LLAMA_DB_USER` | `username` | Database user |
| `LLAMA_DB_PASS` | `password` | Database password |
| `LLAMA_DB_NAME` | `llama_configs` | Database name |
| `LLAMA_MODEL_DIR` | `~/.cache/huggingface/hub/` | Default model directory |
| `LLAMA_SERVER_BINARY` | `/usr/local/bin/llama-server` | Path to llama.cpp server binary |
| `LLAMA_SECRET_KEY` | *(random)* | Flask secret key for sessions |
| `AUTH_ENABLED` | `false` | Enable HTTP Basic Auth |
| `AUTH_USER` | *(empty)* | Auth username |
| `AUTH_PASSWORD` | *(empty)* | Auth password |
| `DEBUG` | `false` | Flask debug mode |

## Usage

1. **Start a server** from the terminal with your desired flags
2. Click **Import Config** in the nav bar to capture its settings
3. The config is stored under the model name (e.g., `Qwen3.6-27B.Q4_K_M.gguf`)
4. Edit any version's parameters through the web form, or launch it directly
5. Subsequent imports of the same model add new versions only when settings differ

For detailed workflows — importing, forking, benchmarking, server lifecycle, and more — see [Core Workflows](docs/WORKFLOWS.md).

## Advanced Topics

- **Parameter reference & tuning guide** — [Advanced Features & Optimization](docs/ADVANCED.md)
- **API endpoints** — full reference in [Advanced Features & Optimization](docs/ADVANCED.md)
- **Benchmarking deep dive** (how it works, request details, metric interpretation) — [Benchmarking Guide](docs/BENCHMARKING.md)
- **Common issues and maintenance** — [Troubleshooting & Maintenance](docs/TROUBLESHOOTING.md)

## Tech Stack

Flask, Flask-WTF (CSRF protection), PyMySQL, HTMX, python-dotenv — subprocess-based process management with PID tracking
