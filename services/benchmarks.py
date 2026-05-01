"""Benchmark service — sends test prompt to running llama-server, captures metrics."""
import subprocess
import time
import urllib.request
import urllib.error
import json
from config import DEFAULT_API_HOST, DEFAULT_API_PORT


# Default test prompt — ~30 tokens, generic enough for any model
TEST_PROMPT = "Write a short paragraph about the importance of version control in software development."
TEST_N_TOKENS = 128  # how many tokens to request


def get_server_host_port(version_data=None):
    """Get the actual host:port from version server settings, or defaults."""
    if version_data:
        server = version_data.get('server', {})
        host = server.get('host') or DEFAULT_API_HOST
        port = server.get('port') or DEFAULT_API_PORT
    else:
        host = DEFAULT_API_HOST
        port = DEFAULT_API_PORT
    return host, port


def wait_for_server(host, port, timeout=60):
    """Wait for llama-server to be ready. Returns (ready: bool, elapsed_sec: float)."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            url = f'http://{host}:{port}/health'
            req = urllib.request.Request(url, method='GET')
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                if data.get('status') == 'ok':
                    return True, time.time() - start
        except (urllib.error.URLError, OSError, json.JSONDecodeError):
            pass
        time.sleep(1)
    return False, timeout


def run_benchmark(host, port, prompt=TEST_PROMPT, n_tokens=TEST_N_TOKENS):
    """Send a test completion request and measure TPS.

    Returns dict with: tps, tokens_generated, duration_sec, error (if any)
    """
    payload = json.dumps({
        'prompt': prompt,
        'n_predict': n_tokens,
        'temperature': 0.8,
        'top_k': 40,
        'top_p': 0.95,
    }).encode()

    start = time.time()
    try:
        url = f'http://{host}:{port}/completion'
        req = urllib.request.Request(url, data=payload, method='POST')
        req.add_header('Content-Type', 'application/json')

        with urllib.request.urlopen(req, timeout=120) as resp:
            body = resp.read().decode()
            duration = time.time() - start

            # Try to count tokens from response
            data = json.loads(body)
            # llama-server returns timing info in the response
            tokens_generated = 0
            if 'timing' in data:
                timing = data['timing']
                tokens_generated = timing.get('predicted_n', n_tokens)
                # If server reports generation tps directly, use it
                gen_tps = timing.get('generation_ms', 0)
                if gen_tps and tokens_generated:
                    # generation_ms is ms per token
                    server_tps = 1000.0 / gen_tps
                    return {
                        'tps': round(server_tps, 2),
                        'tokens_generated': tokens_generated,
                        'duration_sec': round(duration, 3),
                        'error': None,
                    }

            # Fallback: estimate from duration
            if duration > 0:
                estimated_tps = tokens_generated / duration if tokens_generated else n_tokens / duration
                return {
                    'tps': round(estimated_tps, 2),
                    'tokens_generated': tokens_generated or n_tokens,
                    'duration_sec': round(duration, 3),
                    'error': None,
                }

            return {'tps': 0, 'tokens_generated': 0, 'duration_sec': duration, 'error': 'Unexpected response format'}

    except urllib.error.URLError as e:
        return {'tps': 0, 'tokens_generated': 0, 'duration_sec': 0, 'error': f'Connection failed: {e.reason}'}
    except Exception as e:
        return {'tps': 0, 'tokens_generated': 0, 'duration_sec': 0, 'error': str(e)}


def get_vram():
    """Get VRAM usage via nvidia-smi. Returns MB or None."""
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=memory.used', '--format=csv,noheader'],
            capture_output=True, text=True, timeout=5
        )
        values = [v.strip().replace(' MiB', '') for v in result.stdout.strip().split('\n') if v.strip()]
        return sum(int(v) for v in values if v.isdigit())
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        return None


def get_cpu_usage():
    """Get current CPU usage percentage. Returns float or None."""
    try:
        import psutil
        return psutil.cpu_percent(interval=1)
    except ImportError:
        return None


def benchmark_version(version_id):
    """Run full benchmark for a version. Returns result dict."""
    from models.configs import get_all_version_data, save_performance_metric

    data = get_all_version_data(version_id)
    host, port = get_server_host_port(data)

    # Snapshot VRAM before
    get_vram()

    # Run completion benchmark
    result = run_benchmark(host, port)

    # Snapshot VRAM after
    vram_after = get_vram()
    vram_used = vram_after  # total used (includes model + KV cache)

    # CPU snapshot
    cpu = get_cpu_usage()

    # Save to DB
    save_performance_metric(
        version_id=version_id,
        tps=result.get('tps'),
        vram_used=vram_used,
        peak_cpu=cpu,
        notes=f"Benchmark: {result.get('tokens_generated', 0)} tokens in {result.get('duration_sec', 0)}s",
    )

    return {
        'success': result.get('error') is None,
        'tps': result.get('tps'),
        'tokens_generated': result.get('tokens_generated'),
        'duration_sec': result.get('duration_sec'),
        'vram_used_mb': vram_used,
        'peak_cpu_pct': cpu,
        'error': result.get('error'),
    }
