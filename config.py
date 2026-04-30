import os

# Database
DB_HOST = os.getenv('LLAMA_DB_HOST', '10.10.3.15')
DB_USER = os.getenv('LLAMA_DB_USER', 'llama_mgr')
DB_PASS = os.getenv('LLAMA_DB_PASS', 'llama_mgr')
DB_NAME = os.getenv('LLAMA_DB_NAME', 'llama_configs')

# Models
MODEL_DIR = os.getenv('LLAMA_MODEL_DIR', '/home/mtraylor/.cache/huggingface/hub/')

# Screen session prefix (sessions named {prefix}-v{version_number})
SCREEN_PREFIX = os.getenv('LLAMA_SCREEN_PREFIX', 'llama-manager')

# llama.cpp binary
SERVER_BINARY = os.getenv('LLAMA_SERVER_BINARY', '/usr/local/bin/llama-server')

# Flask
SECRET_KEY = os.getenv('LLAMA_SECRET_KEY', 'change-me-in-production')

# Server API (for auto-benchmarking)
DEFAULT_API_HOST = '127.0.0.1'
DEFAULT_API_PORT = 8080
