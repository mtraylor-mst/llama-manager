import logging
from flask import Flask, render_template, Response, request
from flask_wtf.csrf import CSRFProtect
from config import MODEL_DIR, SECRET_KEY, AUTH_ENABLED, AUTH_USER, AUTH_PASSWORD

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

csrf = CSRFProtect()


def create_app():
    if AUTH_ENABLED and (not AUTH_USER or not AUTH_PASSWORD):
        raise RuntimeError(
            "AUTH_ENABLED is true but AUTH_USER and AUTH_PASSWORD must both be set"
        )

    app = Flask(__name__)
    app.secret_key = SECRET_KEY
    # Session cookie security
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    csrf.init_app(app)

    # HTTP Basic Auth middleware
    if AUTH_ENABLED:
        @app.before_request
        def check_auth():
            auth = request.authorization
            if not auth or not (auth.username == AUTH_USER and auth.password == AUTH_PASSWORD):
                return Response('Authentication required', 401, {
                    'WWW-Authenticate': 'Basic realm="Login Required"'
                })

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
