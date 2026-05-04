from models.base import get_conn


CATEGORIES = [
    'model_loading',
    'context_batching',
    'cpu_threading',
    'gpu_device',
    'memory',
    'sampling',
    'server',
    'speculative',
    'chat_templates',
    'checkpoints',
    'logging',
    'advanced',
]

COMPLEX_TABLES = [
    'logit_biases',
    'lora_adapters',
    'control_vectors',
    'override_kv',
    'override_tensors',
    'dry_sequence_breakers',
]


def get_all_configs():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM configs ORDER BY name')
            return cur.fetchall()


def get_config(cfg_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM configs WHERE id = %s', (cfg_id,))
            return cur.fetchone()


def create_config(name, description='', model_dir=''):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'INSERT INTO configs (name, description, model_dir) VALUES (%s, %s, %s)',
                (name, description, model_dir),
            )
            conn.commit()
            return cur.lastrowid


def update_config(cfg_id, name, description='', model_dir=''):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'UPDATE configs SET name=%s, description=%s, model_dir=%s WHERE id=%s',
                (name, description, model_dir, cfg_id),
            )
            conn.commit()


def delete_config(cfg_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute('DELETE FROM configs WHERE id = %s', (cfg_id,))
            conn.commit()


def get_version(version_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT cv.*, c.name as config_name FROM config_versions cv '
                'JOIN configs c ON c.id = cv.config_id WHERE cv.id = %s',
                (version_id,),
            )
            return cur.fetchone()


def get_latest_version(config_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT * FROM config_versions WHERE config_id = %s '
                'ORDER BY version_number DESC LIMIT 1',
                (config_id,),
            )
            return cur.fetchone()


def delete_version(version_id):
    """Delete a version. CASCADE handles all child tables."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute('DELETE FROM config_versions WHERE id = %s', (version_id,))
            conn.commit()
            return cur.rowcount > 0


def get_all_versions(config_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT * FROM config_versions WHERE config_id = %s '
                'ORDER BY version_number DESC',
                (config_id,),
            )
            return cur.fetchall()


def next_version_number(config_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT COALESCE(MAX(version_number), 0) + 1 FROM config_versions '
                'WHERE config_id = %s',
                (config_id,),
            )
            return cur.fetchone()['COALESCE(MAX(version_number), 0) + 1']


def create_version(config_id, comments=''):
    vn = next_version_number(config_id)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'INSERT INTO config_versions (config_id, version_number, comments) '
                'VALUES (%s, %s, %s)',
                (config_id, vn, comments),
            )
            conn.commit()
            return cur.lastrowid


def duplicate_version(source_version_id, config_id, comments=''):
    """Copy all category data from source version to a new version."""
    next_version_number(config_id)
    version_id = create_version(config_id, comments)

    with get_conn() as conn:
        with conn.cursor() as cur:
            # Copy each category table
            for cat in CATEGORIES:
                table = f'v_{cat}'
                cur.execute(f'SELECT * FROM {table} WHERE version_id = %s', (source_version_id,))
                row = cur.fetchone()
                if row:
                    row.pop('version_id', None)
                    cols = ', '.join(row.keys())
                    placeholders = ', '.join(['%s'] * len(row))
                    cur.execute(
                        f'INSERT INTO {table} (version_id, {cols}) VALUES (%s, {placeholders})',
                        (version_id,) + tuple(row.values()),
                    )

            # Copy complex tables
            for tbl in COMPLEX_TABLES:
                table = f'v_{tbl}'
                cur.execute(f'SELECT * FROM {table} WHERE version_id = %s', (source_version_id,))
                rows = cur.fetchall()
                for row in rows:
                    row.pop('id', None)
                    row.pop('version_id', None)
                    cols = ', '.join(row.keys())
                    placeholders = ', '.join(['%s'] * len(row))
                    cur.execute(
                        f'INSERT INTO {table} (version_id, {cols}) VALUES (%s, {placeholders})',
                        (version_id,) + tuple(row.values()),
                    )

            conn.commit()

    return version_id


def save_category(version_id, category, data):
    """Save a category table row. data is a dict of column->value."""
    table = f'v_{category}'
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Check if row exists
            cur.execute(f'SELECT * FROM {table} WHERE version_id = %s', (version_id,))
            existing = cur.fetchone()

            cols = ', '.join(data.keys())
            placeholders = ', '.join(['%s'] * len(data))
            values = tuple(data.values())

            if existing:
                set_clauses = ', '.join([f'{c} = %s' for c in data.keys()])
                cur.execute(
                    f'UPDATE {table} SET {set_clauses} WHERE version_id = %s',
                    values + (version_id,),
                )
            else:
                cur.execute(
                    f'INSERT INTO {table} (version_id, {cols}) VALUES (%s, {placeholders})',
                    (version_id,) + values,
                )
            conn.commit()


def get_category(version_id, category):
    """Get a category table row for a version."""
    table = f'v_{category}'
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(f'SELECT * FROM {table} WHERE version_id = %s', (version_id,))
            return cur.fetchone() or {}


def save_complex_table(version_id, table_name, rows):
    """Save complex value rows (logit_biases, lora_adapters, etc.)."""
    full_name = f'v_{table_name}'
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(f'DELETE FROM {full_name} WHERE version_id = %s', (version_id,))
            for row in rows:
                cols = ', '.join(row.keys())
                placeholders = ', '.join(['%s'] * len(row))
                values = tuple(row.values())
                cur.execute(
                    f'INSERT INTO {full_name} (version_id, {cols}) VALUES (%s, {placeholders})',
                    (version_id,) + values,
                )
            conn.commit()


def get_complex_table(version_id, table_name):
    """Get complex value rows for a version."""
    full_name = f'v_{table_name}'
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(f'SELECT * FROM {full_name} WHERE version_id = %s ORDER BY id', (version_id,))
            return cur.fetchall()


def get_all_version_data(version_id):
    """Get all category and complex data for a version."""
    result = {}
    for cat in CATEGORIES:
        result[cat] = get_category(version_id, cat)
    for tbl in COMPLEX_TABLES:
        result[tbl] = get_complex_table(version_id, tbl)
    return result


def save_performance_metric(version_id, load_time=None, tps=None, vram_used=None,
                            peak_cpu=None, notes=''):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'INSERT INTO performance_metrics '
                '(version_id, load_time_sec, tps, vram_used_mb, peak_cpu_pct, notes) '
                'VALUES (%s, %s, %s, %s, %s, %s)',
                (version_id, load_time, tps, vram_used, peak_cpu, notes),
            )
            conn.commit()
            return cur.lastrowid


def get_performance_metrics(version_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT * FROM performance_metrics WHERE version_id = %s '
                'ORDER BY recorded_at DESC',
                (version_id,),
            )
            return cur.fetchall()


def get_common_options():
    """Get all common options ordered by display_order."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM common_options ORDER BY display_order')
            return cur.fetchall()


def is_common_option(category, column_name):
    """Check if a field is marked as a common option."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT id FROM common_options WHERE category = %s AND column_name = %s',
                (category, column_name),
            )
            return cur.fetchone() is not None


def add_common_option(category, column_name, custom_label=None):
    """Add a field to common options. Returns True if added, False if already exists."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT MAX(display_order) AS max_order FROM common_options'
            )
            max_order = cur.fetchone()['max_order'] or 0
            try:
                cur.execute(
                    'INSERT INTO common_options (category, column_name, display_order, custom_label) '
                    'VALUES (%s, %s, %s, %s)',
                    (category, column_name, max_order + 1, custom_label),
                )
                conn.commit()
                return True
            except Exception:
                return False


def remove_common_option(option_id):
    """Remove a common option by ID."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute('DELETE FROM common_options WHERE id = %s', (option_id,))
            conn.commit()
            return cur.rowcount > 0


def reorder_common_options(order_list):
    """Bulk update display_order. order_list is a list of IDs in desired order."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            for idx, opt_id in enumerate(order_list):
                cur.execute(
                    'UPDATE common_options SET display_order = %s WHERE id = %s',
                    (idx, opt_id),
                )
            conn.commit()
