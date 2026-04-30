from flask import Blueprint, request, jsonify

bp = Blueprint('api', __name__)


@bp.route('/api/models')
def list_models():
    from services.command_builder import get_models_in_dir
    model_dir = request.args.get('dir')
    models = get_models_in_dir(model_dir)
    return jsonify(models)


@bp.route('/api/version/<int:version_id>/data')
def version_data(version_id):
    from models.configs import get_all_version_data, CATEGORIES, COMPLEX_TABLES
    data = get_all_version_data(version_id)
    return jsonify({
        'categories': {cat: data.get(cat, {}) for cat in CATEGORIES},
        'complex': {tbl: data.get(tbl, []) for tbl in COMPLEX_TABLES},
    })
