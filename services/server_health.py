"""Server health check — pings llama-server HTTP API /health endpoint."""

import json
import logging
import time
import urllib.request
import urllib.error

from config import DEFAULT_API_HOST, DEFAULT_API_PORT

logger = logging.getLogger(__name__)

# Timeout for health check in seconds — keep short so nav bar doesn't hang
HEALTH_TIMEOUT = 1


def get_server_url(version_id=None, version_data=None):
    """Get the llama-server URL from version data or defaults."""
    if version_data:
        server = version_data.get("server", {})
        host = server.get("host") or DEFAULT_API_HOST
        port = server.get("port") or DEFAULT_API_PORT
    elif version_id:
        from models.configs import get_all_version_data

        data = get_all_version_data(version_id)
        server = data.get("server", {})
        host = server.get("host") or DEFAULT_API_HOST
        port = server.get("port") or DEFAULT_API_PORT
    else:
        host = DEFAULT_API_HOST
        port = DEFAULT_API_PORT
    return f"http://{host}:{port}"


def check_health(version_id=None, version_data=None):
    """Ping llama-server /health endpoint.

    Returns dict with:
      - healthy: bool
      - response_time_ms: float (rounded)
      - status: str from API or None
      - error: str or None
    """
    url = get_server_url(version_id, version_data) + "/health"
    start = time.monotonic()
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=HEALTH_TIMEOUT) as resp:
            elapsed_ms = round((time.monotonic() - start) * 1000)
            data = json.loads(resp.read().decode())
            return {
                "healthy": True,
                "response_time_ms": elapsed_ms,
                "status": data.get("status"),
                "error": None,
            }
    except urllib.error.URLError as e:
        elapsed_ms = round((time.monotonic() - start) * 1000)
        reason = str(e.reason) if hasattr(e, "reason") else str(e)
        return {
            "healthy": False,
            "response_time_ms": elapsed_ms,
            "status": None,
            "error": f"Connection failed: {reason}",
        }
    except (OSError, json.JSONDecodeError, Exception) as e:
        elapsed_ms = round((time.monotonic() - start) * 1000)
        return {
            "healthy": False,
            "response_time_ms": elapsed_ms,
            "status": None,
            "error": str(e),
        }
