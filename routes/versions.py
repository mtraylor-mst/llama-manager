from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, session

bp = Blueprint('versions', __name__)


def get_common_option_set():
    """Return a set of (category, column_name) tuples for all common options."""
    try:
        from models.configs import get_common_options
        options = get_common_options()
        return {(opt['category'], opt['column_name']) for opt in options}
    except Exception:
        return set()


def get_common_options_list():
    """Return list of common option dicts with resolved labels."""
    try:
        from models.configs import get_common_options
        from template_utils import CATEGORY_FIELDS
        options = get_common_options()
        result = []
        for opt in options:
            fields = CATEGORY_FIELDS.get(opt['category'], [])
            field_def = next((f for f in fields if f[0] == opt['column_name']), None)
            label = opt['custom_label'] or (field_def[1] if field_def else opt['column_name'])
            result.append({
                'id': opt['id'],
                'category': opt['category'],
                'column_name': opt['column_name'],
                'label': label,
            })
        return result
    except Exception:
        return []


def get_common_options_grouped():
    """Return common options grouped by category label."""
    try:
        from models.configs import get_common_options
        from template_utils import CATEGORY_FIELDS
        options = get_common_options()
        groups = {}
        for opt in options:
            cat_label = CATEGORY_LABELS.get(opt['category'], opt['category'])
            if cat_label not in groups:
                groups[cat_label] = {'label': cat_label, 'fields': []}
            fields = CATEGORY_FIELDS.get(opt['category'], [])
            field_def = next((f for f in fields if f[0] == opt['column_name']), None)
            label = opt['custom_label'] or (field_def[1] if field_def else opt['column_name'])
            groups[cat_label]['fields'].append({
                'id': opt['id'],
                'category': opt['category'],
                'column_name': opt['column_name'],
                'label': label,
            })
        return list(groups.values())
    except Exception:
        return []


@bp.route('/config/<int:config_id>/versions')
def history(config_id):
    from models.configs import get_config, get_all_versions, get_latest_version
    from services.screen_manager import get_running_version_id
    config = get_config(config_id)
    if not config:
        flash('Config not found', 'error')
        return redirect(url_for('index'))
    versions = get_all_versions(config_id)
    latest = get_latest_version(config_id)
    running_vid = get_running_version_id()
    running_is_this_config = any(v['id'] == running_vid for v in versions) if running_vid else False
    return render_template(
        'versions/history.html',
        config=config,
        versions=versions,
        latest_version_id=latest['id'] if latest else None,
        running_version_id=running_vid if running_is_this_config else None,
    )


@bp.route('/config/<int:config_id>/version/latest/edit', methods=['GET', 'POST'])
def edit_latest(config_id):
    from models.configs import get_config, get_latest_version
    config = get_config(config_id)
    if not config:
        flash('Config not found', 'error')
        return redirect(url_for('index'))
    version = get_latest_version(config_id)
    if not version:
        flash('No versions found', 'error')
        return redirect(url_for('configs.view', config_id=config_id))
    return _edit_form(version, config)


@bp.route('/version/<int:version_id>/edit', methods=['GET', 'POST'])
def edit(version_id):
    from models.configs import get_version, get_all_version_data
    version = get_version(version_id)
    if not version:
        flash('Version not found', 'error')
        return redirect(url_for('index'))
    data = get_all_version_data(version_id)
    return _edit_form(version, None, data=data)


@bp.route('/version/<int:version_id>/fork-edit', methods=['GET', 'POST'])
def fork_edit(version_id):
    from models.configs import get_version, get_all_version_data
    version = get_version(version_id)
    if not version:
        flash('Version not found', 'error')
        return redirect(url_for('index'))

    source_data = get_all_version_data(version_id)
    session['fork_source_version_id'] = version_id
    session['fork_config_id'] = version['config_id']
    session.pop('fork_version_id', None)

    fake_version = {
        'id': None,
        'config_id': version['config_id'],
        'config_name': version['config_name'],
        'version_number': '(New)',
        'comments': '',
        'status': None,
    }
    return _edit_form(fake_version, None, data=source_data, is_fork=True)


@bp.route('/version/<int:version_id>/delete', methods=['POST'])
def delete(version_id):
    from models.configs import get_version, delete_version
    from services.screen_manager import get_running_version_id

    version = get_version(version_id)
    if not version:
        flash('Version not found', 'error')
        return redirect(url_for('index'))

    running_vid = get_running_version_id()
    if running_vid == version_id:
        flash('Cannot delete the currently running version. Stop it first.', 'error')
        return redirect(url_for('configs.view', config_id=version['config_id']))

    if not delete_version(version_id):
        flash('Failed to delete version', 'error')
        return redirect(url_for('configs.view', config_id=version['config_id']))

    flash(f'Version {version["version_number"]} deleted', 'success')
    return redirect(url_for('configs.view', config_id=version['config_id']))


def _save_version_data(version_id, config_id):
    from models.configs import CATEGORIES, COMPLEX_TABLES, save_category, save_complex_table

    # Save comments and status
    from models.base import get_conn
    with get_conn() as conn:
        with conn.cursor() as cur:
            status_val = request.form.get('status') or None
            cur.execute(
                'UPDATE config_versions SET comments = %s, status = %s WHERE id = %s',
                (request.form.get('comments', ''), status_val, version_id),
            )
            conn.commit()

    # Save each category
    for cat in CATEGORIES:
        prefix = f'{cat}_'
        data = {}
        for key, val in request.form.items():
            if key.startswith(prefix):
                col = key[len(prefix):]
                if val == '' or val == 'None':
                    data[col] = None
                elif key.endswith('_bool') or col in _BOOL_COLS.get(cat, set()):
                    data[col] = 1 if val == '1' or val == 'on' else 0
                else:
                    data[col] = val
        if data:
            save_category(version_id, cat, data)

    # Save complex tables
    for tbl in COMPLEX_TABLES:
        rows = []
        ids_key = request.form.get(f'{tbl}_ids')
        if ids_key:
            row_ids = ids_key.split(',')
            for rid in row_ids:
                rid = rid.strip()
                if not rid:
                    continue
                row = {}
                for key, val in request.form.items():
                    if key.startswith(f'{tbl}_{rid}_'):
                        col = key[len(f'{tbl}_{rid}_'):]
                        row[col] = val if val else None
                if row:
                    rows.append(row)
        save_complex_table(version_id, tbl, rows)


def _edit_form(version, config, data=None, is_fork=False):
    from models.configs import CATEGORIES, COMPLEX_TABLES, get_all_version_data, create_version

    if request.method == 'POST':
        if is_fork:
            # This is a fork -- create the version now on save
            source_vid = session.pop('fork_source_version_id', None)
            config_id = session.pop('fork_config_id', None)
            new_vid = create_version(config_id, request.form.get('comments', ''))
            session['fork_version_id'] = new_vid

            # Copy data from source version to the new version
            from models.base import get_conn
            source_data = get_all_version_data(source_vid)
            with get_conn() as conn:
                with conn.cursor() as cur:
                    for cat in CATEGORIES:
                        table = f'v_{cat}'
                        row = source_data.get(cat, {})
                        if row:
                            row.pop('version_id', None)
                            cols = ', '.join(row.keys())
                            placeholders = ', '.join(['%s'] * len(row))
                            cur.execute(
                                f'INSERT INTO {table} (version_id, {cols}) VALUES (%s, {placeholders})',
                                (new_vid,) + tuple(row.values()),
                            )
                    for tbl in COMPLEX_TABLES:
                        table = f'v_{tbl}'
                        rows = source_data.get(tbl, [])
                        for row in rows:
                            row.pop('id', None)
                            row.pop('version_id', None)
                            cols = ', '.join(row.keys())
                            placeholders = ', '.join(['%s'] * len(row))
                            cur.execute(
                                f'INSERT INTO {table} (version_id, {cols}) VALUES (%s, {placeholders})',
                                (new_vid,) + tuple(row.values()),
                            )
                conn.commit()

            _save_version_data(new_vid, config_id)
            flash('Version saved', 'success')
            return redirect(url_for('configs.view', config_id=config_id))
        else:
            # Existing version edit
            _save_version_data(version['id'], version['config_id'])
            flash('Version saved', 'success')
            return redirect(url_for('configs.view', config_id=version['config_id']))

    if data is None:
        data = get_all_version_data(version['id'])

    categories = CATEGORIES
    complex_tables = COMPLEX_TABLES

    # Determine which version of this config is currently running
    from services.screen_manager import get_running_version_id
    from models.configs import get_all_versions
    running_vid = get_running_version_id()
    all_versions = get_all_versions(version['config_id'])
    running_version = None
    if running_vid:
        for v in all_versions:
            if v['id'] == running_vid:
                running_version = v
                break

    return render_template(
        'versions/form.html',
        version=version,
        config=config,
        data=data,
        categories=categories,
        complex_tables=complex_tables,
        category_labels=CATEGORY_LABELS,
        running_version_id=running_vid,
        running_version=running_version,
        is_fork=is_fork,
        common_option_ids=get_common_option_set(),
        common_options_list=get_common_options_list(),
        common_options_grouped=get_common_options_grouped(),
    )


@bp.route('/version/<int:version_id>/duplicate', methods=['POST'])
def duplicate(version_id):
    from models.configs import get_version, duplicate_version
    version = get_version(version_id)
    if not version:
        flash('Version not found', 'error')
        return redirect(url_for('index'))

    new_vid = duplicate_version(version_id, version['config_id'], 'Duplicated')
    flash('Version duplicated', 'success')
    return redirect(url_for('versions.edit', version_id=new_vid))


@bp.route('/version/<int:version_id>/command')
def command(version_id):
    from services.command_builder import build_command
    cmd = build_command(version_id)
    return jsonify({'command': cmd})


# Boolean columns per category
_BOOL_COLS = {
    'context_batching': {'cont_batching', 'context_shift', 'special_tokens', 'warmup',
                         'spm_infill', 'cache_prompt'},
    'cpu_threading': {'cpu_strict', 'cpu_strict_batch', 'poll_batch'},
    'gpu_device': {'kv_offload', 'repack', 'no_host', 'op_offload', 'cpu_moe',
                   'cpu_moe_draft'},
    'memory': {'mmap', 'mlock', 'direct_io'},
    'sampling': {'ignore_eos', 'backend_sampling'},
    'server': {'reuse_port', 'webui', 'embedding', 'reranking', 'metrics',
               'props', 'slots', 'lora_init_without_apply'},
    'chat_templates': {'jinja', 'skip_chat_parsing', 'prefill_assistant'},
    'checkpoints': {'kv_unified', 'cache_idle_slots'},
    'logging': {'log_prefix', 'log_timestamps', 'verbose', 'log_disable',
                'offline', 'perf', 'escape'},
}

CATEGORY_LABELS = {
    'model_loading': 'Model Loading',
    'context_batching': 'Context & Batching',
    'cpu_threading': 'CPU / Threading',
    'gpu_device': 'GPU / Device',
    'memory': 'Memory',
    'sampling': 'Sampling',
    'server': 'Server',
    'speculative': 'Speculative Decoding',
    'chat_templates': 'Chat & Templates',
    'checkpoints': 'Checkpoints & Cache',
    'logging': 'Logging',
    'advanced': 'Advanced / Override',
}
