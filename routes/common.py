import logging
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for

bp = Blueprint('common', __name__)
logger = logging.getLogger(__name__)


@bp.route('/common-options')
def index():
    try:
        from models.configs import get_common_options
        from template_utils import CATEGORY_FIELDS
        options = get_common_options()
    except Exception as e:
        logger.error('Error loading common options', exc_info=True)
        flash('Error loading common options. Have you run the schema migration?', 'error')
        options = []

    # Resolve labels for each option
    resolved = []
    for opt in options:
        fields = CATEGORY_FIELDS.get(opt['category'], [])
        field_def = next((f for f in fields if f[0] == opt['column_name']), None)
        label = opt['custom_label'] or (field_def[1] if field_def else opt['column_name'])
        resolved.append({
            'id': opt['id'],
            'category': opt['category'],
            'column_name': opt['column_name'],
            'label': label,
            'display_order': opt['display_order'],
        })
    from routes.versions import CATEGORY_LABELS
    return render_template(
        'common_options/index.html',
        options=resolved,
        category_labels=CATEGORY_LABELS,
    )


@bp.route('/common-options/toggle', methods=['POST'])
def toggle():
    """Toggle a field in/out of common options. Used from version edit form."""
    data = request.get_json() or {}
    category = data.get('category')
    column_name = data.get('column_name')
    add = data.get('add', True)

    if not category or not column_name:
        return jsonify({'error': 'Missing category or column_name'}), 400

    try:
        from models.configs import is_common_option, add_common_option, remove_common_option, get_common_options

        currently_common = is_common_option(category, column_name)

        if add and not currently_common:
            success = add_common_option(category, column_name)
            return jsonify({'added': success, 'common': True})
        elif not add and currently_common:
            options = get_common_options()
            opt = next((o for o in options if o['category'] == category and o['column_name'] == column_name), None)
            if opt:
                success = remove_common_option(opt['id'])
                return jsonify({'removed': success, 'common': False})
            return jsonify({'error': 'Option not found'}), 404

        return jsonify({'common': currently_common})
    except Exception as e:
        logger.error('Error toggling common option', exc_info=True)
        return jsonify({'error': 'Failed to toggle option'}), 500


@bp.route('/common-options/reorder', methods=['POST'])
def reorder():
    """Reorder common options via drag-and-drop."""
    data = request.get_json() or {}
    order_list = data.get('order', [])

    if not order_list:
        return jsonify({'error': 'No order provided'}), 400

    from models.configs import reorder_common_options
    reorder_common_options(order_list)
    return jsonify({'ok': True})


@bp.route('/common-options/remove/<int:option_id>', methods=['POST'])
def remove(option_id):
    """Remove a common option from the common options page."""
    from models.configs import remove_common_option
    if remove_common_option(option_id):
        flash('Option removed', 'success')
    else:
        flash('Failed to remove option', 'error')
    return redirect(url_for('common.index'))


@bp.route('/common-options/update-label/<int:option_id>', methods=['POST'])
def update_label(option_id):
    """Update the custom label for a common option."""
    custom_label = request.form.get('custom_label', '').strip() or None
    from models.base import get_conn
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'UPDATE common_options SET custom_label = %s WHERE id = %s',
                (custom_label, option_id),
            )
            conn.commit()
    flash('Label updated', 'success')
    return redirect(url_for('common.index'))
