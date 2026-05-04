from flask import Flask, render_template
from config import MODEL_DIR, SECRET_KEY


def create_app():
    app = Flask(__name__)
    app.secret_key = SECRET_KEY

    # Register template helpers
    from template_utils import register_template_helpers
    register_template_helpers(app)

    @app.context_processor
    def inject_context():
        from services.screen_manager import get_status, get_running_version_id
        st = get_status()
        running_vid = get_running_version_id() if st['running'] else None
        running_ver_info = None
        if running_vid:
            from models.configs import get_version
            running_ver_info = get_version(running_vid)
        return {
            'server_status': st,
            'running_version_id': running_vid,
            'running_version_info': running_ver_info,
            'model_dir': MODEL_DIR,
        }

    # Register blueprints
    from routes.configs import bp as configs_bp
    app.register_blueprint(configs_bp)

    from routes.versions import bp as versions_bp
    app.register_blueprint(versions_bp)

    from routes.server import bp as server_bp
    app.register_blueprint(server_bp)

    from routes.api import bp as api_bp
    app.register_blueprint(api_bp)

    from routes.common import bp as common_bp
    app.register_blueprint(common_bp)

    @app.route('/')
    def index():
        from models.configs import get_all_configs
        return render_template('configs/index.html', configs=get_all_configs())

    return app
