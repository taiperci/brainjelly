import os

from flask import Flask, jsonify

from backend.config import get_config


def create_app(env_name: str | None = None) -> Flask:
    """Application factory for the Brain Jelly backend."""
    app = Flask(__name__)
    config_class = get_config(env_name or os.getenv("FLASK_ENV"))
    app.config.from_object(config_class)

    _register_blueprints(app)
    _register_error_handlers(app)
    _register_extensions(app)
    _register_cli(app)

    if app.config.get("FLASK_ENV") != "production":
        from backend.app.extensions import db
        from backend.app.models import Track  # noqa: F401

        with app.app_context():
            db.create_all()

    return app


def _register_blueprints(app: Flask) -> None:
    """Import and register Flask blueprints."""
    from .routes import register_root_routes  # local import to avoid circular deps
    from .routes.api import api_bp
    from .routes.health import health_bp
    from .routes.upload import upload_bp
    from .routes.tracks import tracks_bp

    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(upload_bp, url_prefix="/api")
    app.register_blueprint(tracks_bp, url_prefix="/api")

    register_root_routes(app)


def _register_error_handlers(app: Flask) -> None:
    """Register global JSON error handlers."""

    @app.errorhandler(404)
    def handle_404(error):
        return jsonify({"success": False, "error": "Not Found"}), 404

    @app.errorhandler(500)
    def handle_500(error):
        return jsonify({"success": False, "error": "Internal Server Error"}), 500


def _register_extensions(app: Flask) -> None:
    """Initialize Flask extensions."""
    from backend.app.extensions import db
    from backend.celery_app import create_celery_app

    db.init_app(app)
    create_celery_app(app)


def _register_cli(app: Flask) -> None:
    """Attach custom CLI commands."""
    # Placeholder for Flask CLI command registration
    return None

