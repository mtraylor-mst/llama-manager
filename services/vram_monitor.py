"""Background VRAM polling thread using nvidia-smi."""

import subprocess
import threading
import time


class VramMonitor:
    """Polls nvidia-smi at 100ms intervals and collects VRAM usage data."""

    def __init__(self):
        self._thread = None
        self._running = False
        self._lock = threading.Lock()
        self._data_points = []
        self._peak_mb = None

    def start(self):
        """Start background thread polling nvidia-smi at 100ms intervals."""
        if self._running:
            return
        self._running = True
        self._data_points = []
        self._peak_mb = None
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the polling thread. Returns collected data points."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        with self._lock:
            return list(self._data_points)

    def get_peak(self):
        """Return max VRAM observed so far in MB, or None if no data."""
        with self._lock:
            return self._peak_mb

    def get_data_points(self):
        """Return a copy of collected data points as list of (timestamp, used_mb)."""
        with self._lock:
            return list(self._data_points)

    @staticmethod
    def get_total_vram():
        """One-shot query for total VRAM on device 0. Returns MB or None."""
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=memory.total",
                    "--format=csv,noheader,nounits",
                    "-i", "0",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return int(result.stdout.strip())
        except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
            pass
        return None

    def _poll_loop(self):
        """Internal polling loop. Runs at ~100ms intervals while _running is True."""
        while self._running:
            used_mb = self._query_used_vram()
            if used_mb is not None:
                ts = time.time()
                with self._lock:
                    self._data_points.append((ts, used_mb))
                    if self._peak_mb is None or used_mb > self._peak_mb:
                        self._peak_mb = used_mb
            time.sleep(0.1)

    @staticmethod
    def _query_used_vram():
        """Query current VRAM usage on device 0. Returns MB or None."""
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=memory.used",
                    "--format=csv,noheader,nounits",
                    "-i", "0",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return int(result.stdout.strip())
        except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
            pass
        return None
