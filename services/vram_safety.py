"""VRAM safety calculator: theoretical estimates and empirical analysis."""

import logging

from models.configs import get_category, get_all_version_data
from services.model_parser import get_or_parse_metadata
from services.vram_monitor import VramMonitor
from services.vram_stress_test import get_latest_stress_test

logger = logging.getLogger(__name__)

# KV cache quantization: bytes per element per type
KV_QUANT_BYTES = {
    "f16": 2,
    "q8_0": 1,
    "q4_0": 0.5,
    "q5_0": 0.625,
}

# Default quantization if not specified (llama.cpp default is f16)
DEFAULT_KV_QUANT = 2  # f16 = 2 bytes

# Color thresholds (margin percentage of total VRAM)
GREEN_THRESHOLD = 20
YELLOW_THRESHOLD = 5

# Theoretical compaction buffer (conservative estimate)
THEORETICAL_COMPACTION_BUFFER = 1.10


def _kv_quant_bytes(cache_type):
    """Get bytes per element for a KV cache quantization type."""
    if not cache_type:
        return DEFAULT_KV_QUANT
    return KV_QUANT_BYTES.get(cache_type, DEFAULT_KV_QUANT)


def theoretical_estimate(version_id):
    """Calculate theoretical VRAM usage from model metadata and config.

    Returns dict with breakdown and safety status, or None if insufficient data.
    """
    try:
        all_data = get_all_version_data(version_id)
        model_loading = all_data.get("model_loading", {})
        model_path = model_loading.get("model_path", "")

        if not model_path:
            return None

        # Get or parse model metadata
        from services.screen_manager import get_log_file
        log_path = get_log_file(version_id)
        meta = get_or_parse_metadata(model_path, log_path)
        if not meta:
            return None

        # Get config values
        ctx_data = get_category(version_id, "context_batching")
        mem_data = get_category(version_id, "memory")

        ctx_size = ctx_data.get("ctx_size") or 2048
        cache_type_k = mem_data.get("cache_type_k")

        # Weight size from file
        weight_size_mb = meta.get("file_size_bytes", 0) / (1024 * 1024)

        # KV cache per token calculation
        n_layers = meta.get("n_layers", 0)
        n_embd = meta.get("n_embd", 0)
        n_head = meta.get("n_head", 0)
        n_head_kv = meta.get("n_head_kv") or n_head

        head_dim = n_embd / n_head if n_head else 0
        kv_bytes_per_element = _kv_quant_bytes(cache_type_k)

        # KV cache: 2 (key + value) * n_layers * n_head_kv * head_dim * quant_bytes
        kv_per_token_bytes = 2 * n_layers * n_head_kv * head_dim * kv_bytes_per_element
        kv_cache_mb = (ctx_size * kv_per_token_bytes) / (1024 * 1024)

        # Predicted peak with compaction buffer
        predicted_peak_mb = weight_size_mb + kv_cache_mb * THEORETICAL_COMPACTION_BUFFER

        # Total VRAM
        total_vram_mb = VramMonitor.get_total_vram()
        if not total_vram_mb:
            return None

        # Margin calculation
        margin_mb = total_vram_mb - predicted_peak_mb
        margin_pct = round((margin_mb / total_vram_mb) * 100, 1)

        # Status determination
        status = _color_from_margin(margin_pct)

        return {
            "weight_size_mb": round(weight_size_mb),
            "kv_cache_mb": round(kv_cache_mb),
            "predicted_peak_mb": round(predicted_peak_mb),
            "total_vram_mb": total_vram_mb,
            "margin_mb": round(margin_mb),
            "margin_pct": margin_pct,
            "status": status,
            "source": "theoretical",
            "confidence": "low",
            "kv_per_token_bytes": round(kv_per_token_bytes, 2),
            "compaction_buffer": THEORETICAL_COMPACTION_BUFFER - 1,
        }
    except Exception as e:
        logger.error(f"Theoretical estimate failed for version {version_id}: {e}", exc_info=True)
        return None


def empirical_estimate(version_id):
    """Calculate VRAM safety from empirical stress test data.

    Returns dict with breakdown and safety status, or None if no test data.
    """
    test = get_latest_stress_test(version_id)
    if not test or test["status"] != "completed":
        return None

    kv_per_token_bytes = test.get("kv_per_token_bytes")
    compaction_coeff = test.get("compaction_coefficient")
    model_weight_size_mb = test.get("model_weight_size_mb")
    total_vram_mb = test.get("total_vram_mb")

    if not kv_per_token_bytes or not model_weight_size_mb or not total_vram_mb:
        return None

    # Get config for ctx_size
    ctx_data = get_category(version_id, "context_batching")
    ctx_size = ctx_data.get("ctx_size") or 2048

    # Use empirical compaction coefficient, fallback to theoretical buffer
    compaction_multiplier = 1 + (compaction_coeff or 0)
    if compaction_multiplier < 1:
        compaction_multiplier = THEORETICAL_COMPACTION_BUFFER

    kv_cache_mb = (ctx_size * kv_per_token_bytes) / (1024 * 1024)
    predicted_peak_mb = model_weight_size_mb + kv_cache_mb * compaction_multiplier

    margin_mb = total_vram_mb - predicted_peak_mb
    margin_pct = round((margin_mb / total_vram_mb) * 100, 1)

    status = _color_from_margin(margin_pct)

    return {
        "weight_size_mb": model_weight_size_mb,
        "kv_cache_mb": round(kv_cache_mb),
        "predicted_peak_mb": round(predicted_peak_mb),
        "total_vram_mb": total_vram_mb,
        "margin_mb": round(margin_mb),
        "margin_pct": margin_pct,
        "status": status,
        "source": "empirical",
        "confidence": "high",
        "kv_per_token_bytes": kv_per_token_bytes,
        "compaction_coefficient": compaction_coeff,
        "failure_ctx_tokens": test.get("failure_ctx_tokens"),
        "test_id": test["id"],
    }


def get_safety(version_id):
    """Get VRAM safety assessment. Prefers empirical data, falls back to theoretical.

    Returns dict with safety info, or None if insufficient data for either method.
    """
    empirical = empirical_estimate(version_id)
    if empirical:
        return empirical

    theoretical = theoretical_estimate(version_id)
    return theoretical


def _color_from_margin(margin_pct):
    """Determine color status from margin percentage."""
    if margin_pct >= GREEN_THRESHOLD:
        return "green"
    elif margin_pct >= YELLOW_THRESHOLD:
        return "yellow"
    else:
        return "red"
