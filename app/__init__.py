"""Flask application factory for the Demo Infrastructure Monitoring Application."""

from flask import Flask

from app.config import Config
from app.db import close_db
from app.extensions import csrf


def create_app(config_class=Config):
    """Create and configure the Flask application."""
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )
    app.config.from_object(config_class)

    csrf.init_app(app)
    app.teardown_appcontext(close_db)

    from app.api.routes import bp as api_bp
    from app.auth.routes import bp as auth_bp
    from app.routes import bp as main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)

    with app.app_context():
        from app.bootstrap import bootstrap_admin, bootstrap_local_server

        bootstrap_admin()
        bootstrap_local_server()

    return app
