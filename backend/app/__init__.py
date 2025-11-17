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

    return app


def _register_blueprints(app: Flask) -> None:
    """Import and register Flask blueprints."""
    from .routes import register_routes  # local import to avoid circular deps

    register_routes(app)


def _register_error_handlers(app: Flask) -> None:
    """Register global JSON error handlers."""

    @app.errorhandler(404)
    def handle_404(error):
        return jsonify({"error": "Not Found"}), 404

    @app.errorhandler(500)
    def handle_500(error):
        return jsonify({"error": "Internal Server Error"}), 500


def _register_extensions(app: Flask) -> None:
    """Initialize Flask extensions."""
    # Placeholder for extension initialization (e.g., db.init_app(app))
    return None


def _register_cli(app: Flask) -> None:
    """Attach custom CLI commands."""
    # Placeholder for Flask CLI command registration
    return None

