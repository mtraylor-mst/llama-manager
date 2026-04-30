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
        from services.screen_manager import get_status
        return {
            'server_status': get_status(),
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

    @app.route('/')
    def index():
        from models.configs import get_all_configs
        return render_template('configs/index.html', configs=get_all_configs())

    return app
