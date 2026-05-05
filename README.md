# llama-manager

Track, compare, and launch [llama.cpp](https://github.com/ggerganov/llama.cpp) server configurations from a web interface.

## Features

- **Import running configs** — captures the full command line from a live `llama-server` process and stores it as a versioned config
- **Grouped by model** — imports are automatically grouped under the model filename, with new versions added when settings change
- **Version history** — each config tracks multiple versions so you can iterate on settings without losing what worked
- **Fork & duplicate** — create new versions from any existing version, or duplicate a version as-is
- **Launch & stop** — starts `llama-server` directly via subprocess with PID tracking for reliable process management
- **Live logs** — SSE-streamed server output in real-time on the config view page
- **Command preview** — generates and displays the full command line with secret redaction
- **Benchmarking** — run TPS benchmarks, track VRAM/CPU usage, and compare performance per version
- **Common options** — pin frequently-used fields to a compact quick-edit panel
- **HTTP Basic Auth** — optional authentication layer for protected deployments

## Setup

```bash
pip install -r requirements.txt
# Initialize the database (run schema.sql against your MySQL/MariaDB server)
mysql -h $HOST -u $USER -p llama_configs < schema.sql
# Configure via .env file or environment variables
python run.py
```

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `LLAMA_DB_HOST` | `127.0.0.1` | Database host |
| `LLAMA_DB_USER` | `username` | Database user |
| `LLAMA_DB_PASS` | `password` | Database password |
| `LLAMA_DB_NAME` | `llama_configs` | Database name |
| `LLAMA_MODEL_DIR` | `/home/mtraylor/.cache/huggingface/hub/` | Default model directory |
| `LLAMA_SERVER_BINARY` | `/usr/local/bin/llama-server` | Path to llama.cpp server binary |
| `LLAMA_SECRET_KEY` | *(random)* | Flask secret key for sessions |
| `AUTH_ENABLED` | `false` | Enable HTTP Basic Auth |
| `AUTH_USER` | | Auth username |
| `AUTH_PASSWORD` | | Auth password |
| `DEBUG` | `false` | Flask debug mode |

## Usage

1. **Start a server** from the terminal with your desired flags
2. Click **Import Config** in the nav bar to capture its settings
3. The config is stored under the model name (e.g., `Qwen3.6-27B.Q4_K_M.gguf`)
4. Edit any version's parameters through the web form, or launch it directly
5. Subsequent imports of the same model add new versions only when settings differ

## Tech Stack

Flask, Flask-WTF, PyMySQL, HTMX, python-dotenv — subprocess-based process management with PID tracking
