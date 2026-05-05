import os

# Application
DEBUG = os.getenv('DEBUG', 'false').lower() in ('true', '1', 'yes')

# Database
DB_HOST = os.getenv('LLAMA_DB_HOST', '127.0.0.1')
DB_USER = os.getenv('LLAMA_DB_USER', 'username')
DB_PASS = os.getenv('LLAMA_DB_PASS', 'password')
DB_NAME = os.getenv('LLAMA_DB_NAME', 'llama_configs')

# Models
MODEL_DIR = os.getenv('LLAMA_MODEL_DIR', '/home/mtraylor/.cache/huggingface/hub/')

# llama.cpp binary
SERVER_BINARY = os.getenv('LLAMA_SERVER_BINARY', '/usr/local/bin/llama-server')

# Authentication (HTTP Basic Auth, disabled by default)
AUTH_ENABLED = os.getenv('AUTH_ENABLED', 'false').lower() in ('true', '1', 'yes')
AUTH_USER = os.getenv('AUTH_USER', '')
AUTH_PASSWORD = os.getenv('AUTH_PASSWORD', '')

def _generate_secret_key():
    """Generate a random secret key if none is configured."""
    import secrets
    return secrets.token_hex(32)


# Flask
SECRET_KEY = os.getenv('LLAMA_SECRET_KEY') or _generate_secret_key()

# Server API (for auto-benchmarking)
DEFAULT_API_HOST = '127.0.0.1'
DEFAULT_API_PORT = 8080
