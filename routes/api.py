import os
from flask import Blueprint, request, jsonify

bp = Blueprint("api", __name__)


@bp.route("/api/models")
def list_models():
    from config import MODEL_DIR
    from services.command_builder import get_models_in_dir

    requested = request.args.get("dir", "")
    # Constrain to MODEL_DIR: if dir is provided, it must be under MODEL_DIR
    if requested:
        real_base = os.path.realpath(MODEL_DIR)
        real_req = os.path.realpath(os.path.join(real_base, requested))
        if not real_req.startswith(real_base + os.sep) and real_req != real_base:
            return jsonify({"error": "Access denied"}), 403
        models = get_models_in_dir(real_req)
    else:
        models = get_models_in_dir()
    return jsonify(models)


@bp.route("/api/version/<int:version_id>/data")
def version_data(version_id):
    from models.configs import get_all_version_data, CATEGORIES, COMPLEX_TABLES

    data = get_all_version_data(version_id)
    return jsonify(
        {
            "categories": {cat: data.get(cat, {}) for cat in CATEGORIES},
            "complex": {tbl: data.get(tbl, []) for tbl in COMPLEX_TABLES},
        }
    )
