from flask import Flask


def create_app(config_object: str = "backend.config.Config") -> Flask:
    """Application factory for the Brain Jelly backend."""
    app = Flask(__name__)
    app.config.from_object(config_object)

    _register_blueprints(app)
    _register_extensions(app)
    _register_cli(app)

    return app


def _register_blueprints(app: Flask) -> None:
    """Import and register Flask blueprints."""
    from .routes import register_routes  # local import to avoid circular deps

    register_routes(app)


def _register_extensions(app: Flask) -> None:
    """Initialize Flask extensions."""
    # Placeholder for extension initialization (e.g., db.init_app(app))
    return None


def _register_cli(app: Flask) -> None:
    """Attach custom CLI commands."""
    # Placeholder for Flask CLI command registration
    return None

