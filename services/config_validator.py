"""Pre-launch validation for config versions."""

import os
import logging

from models.configs import get_all_version_data
from services.vram_safety import theoretical_estimate
from services.model_parser import get_or_parse_metadata

logger = logging.getLogger(__name__)


# Fields that must be positive integers (> 0)
POSITIVE_INT_FIELDS = {
    "context_batching": {"ctx_size", "batch_size", "ubatch_size"},
    "cpu_threading": {"threads", "threads_batch"},
    "gpu_device": {"gpu_layers", "main_gpu"},
}

# Fields that must be non-negative (>= 0)
NON_NEGATIVE_FIELDS = {
    "context_batching": {"n_predict", "n_parallel"},
    "server": {"port", "timeout"},
}


def validate(version_id):
    """Validate a version's config for launch-readiness.

    Returns (errors, warnings) — both lists of dicts with 'field' and 'message'.
    Errors block launch; warnings are advisory only.
    """
    errors = []
    warnings = []

    try:
        data = get_all_version_data(version_id)
    except Exception as e:
        return [{"field": "general", "message": f"Could not load version data: {e}"}], []

    # --- Hard errors ---

    ml = data.get("model_loading", {})
    model_path = ml.get("model_path")
    hf_repo = ml.get("hf_repo")
    model_url = ml.get("model_url")

    # Model source required — either local path, HF repo, or URL
    if not model_path and not hf_repo and not model_url:
        errors.append(
            {"field": "model_source", "message": "Model source is required (model_path, hf_repo, or model_url)"}
        )

    # Model file must exist (only for local path)
    if model_path and not os.path.exists(model_path):
        errors.append(
            {"field": "model_path", "message": f"Model file not found: {model_path}"}
        )

    # Draft model file must exist if specified
    draft_path = ml.get("model_draft")
    if draft_path and not os.path.exists(draft_path):
        errors.append(
            {"field": "model_draft", "message": f"Draft model not found: {draft_path}"}
        )

    # mmproj file must exist if specified
    mmproj_path = ml.get("mmproj_path")
    if mmproj_path and not os.path.exists(mmproj_path):
        errors.append(
            {"field": "mmproj_path", "message": f"mmproj file not found: {mmproj_path}"}
        )

    # --- Value sanity warnings ---

    _check_positive_ints(data, warnings)
    _check_non_negative(data, warnings)

    # --- VRAM estimate warning ---

    vram = theoretical_estimate(version_id)
    if vram:
        margin_pct = vram.get("margin_pct", 100)
        status = vram.get("status", "green")
        predicted = vram.get("predicted_peak_mb", 0)
        total = vram.get("total_vram_mb", 0)

        if status == "red":
            warnings.append(
                {
                    "field": "vram",
                    "message": (
                        f"VRAM likely insufficient: estimated {predicted} MB of "
                        f"{total} MB ({margin_pct}% margin)"
                    ),
                }
            )
        elif status == "yellow":
            warnings.append(
                {
                    "field": "vram",
                    "message": (
                        f"Low VRAM margin: estimated {predicted} MB of "
                        f"{total} MB ({margin_pct}% margin)"
                    ),
                }
            )
    else:
        # Could not estimate — only warn if local model path is set and exists
        if model_path and os.path.exists(model_path):
            meta = get_or_parse_metadata(model_path)
            if not meta:
                warnings.append(
                    {
                        "field": "vram",
                        "message": (
                            "Cannot estimate VRAM usage — no cached metadata for this model. "
                            "Launch once to populate metadata, then re-check."
                        ),
                    }
                )

    return errors, warnings


def _check_positive_ints(data, warnings):
    """Check that required positive integer fields have valid values."""
    for category, fields in POSITIVE_INT_FIELDS.items():
        row = data.get(category, {})
        for field in fields:
            val = row.get(field)
            if val is not None and int(val) <= 0:
                warnings.append(
                    {
                        "field": f"{category}.{field}",
                        "message": f"{field} should be > 0 (got {val})",
                    }
                )


def _check_non_negative(data, warnings):
    """Check that non-negative fields have valid values."""
    for category, fields in NON_NEGATIVE_FIELDS.items():
        row = data.get(category, {})
        for field in fields:
            val = row.get(field)
            if val is not None and int(val) < 0:
                warnings.append(
                    {
                        "field": f"{category}.{field}",
                        "message": f"{field} should be >= 0 (got {val})",
                    }
                )
