# llama-manager

Track, compare, and launch [llama.cpp](https://github.com/ggerganov/llama.cpp) server configurations from a web interface.

## Features

- **Import running configs** — captures the full command line from a live `llama-server` process and stores it as a versioned config
- **Grouped by model** — imports are automatically grouped under the model filename, with new versions added when settings change
- **Version history** — each config tracks multiple versions so you can iterate on settings without losing what worked
- **Launch & restart** — starts `llama-server` in a labelled `screen` session (`llama-manager-{version_id}`) for easy management
- **Live logs** — streams server output in real-time on the config view page
- **Command preview** — generates and displays the full command line with a one-click copy button
- **Benchmarking** — run TPS benchmarks and track performance metrics per version

## Setup

```bash
pip install -r requirements.txt
# Initialize the database (run schema.sql against your MySQL/MariaDB server)
mysql -h $HOST -u $USER -p llama_configs < schema.sql
```

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `LLAMA_DB_HOST` | `10.10.3.15` | Database host |
| `LLAMA_DB_USER` | `llama_mgr` | Database user |
| `LLAMA_DB_PASS` | `llama_mgr` | Database password |
| `LLAMA_DB_NAME` | `llama_configs` | Database name |
| `LLAMA_MODEL_DIR` | `~/.cache/huggingface/hub/` | Default model directory |
| `LLAMA_SCREEN_PREFIX` | `llama-manager` | Screen session name prefix |
| `LLAMA_SERVER_BINARY` | `/usr/local/bin/llama-server` | Path to llama.cpp server binary |

## Usage

1. **Start a server** from the terminal with your desired flags
2. Click **Import Config** in the nav bar to capture its settings
3. The config is stored under the model name (e.g., `Qwen3.6-27B.Q4_K_M.gguf`)
4. Edit any version's parameters through the web form, or launch it directly
5. Subsequent imports of the same model add new versions only when settings differ

## Tech Stack

Flask, MySQL/MariaDB, HTMX, `screen` for process management
