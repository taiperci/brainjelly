"""Route registration for Brain Jelly."""

from flask import Blueprint, Flask


def register_routes(app: Flask) -> None:
    """Register application blueprints."""
    api_bp = Blueprint("api", __name__)

    # Placeholder: register route handlers with api_bp here

    app.register_blueprint(api_bp)

