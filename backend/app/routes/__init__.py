"""Route registration for Brain Jelly."""

from flask import Blueprint, Flask, jsonify


def register_routes(app: Flask) -> None:
    """Register application blueprints."""
    api_bp = Blueprint("api", __name__)

    @api_bp.get("/health")
    def health_check():
        """Lightweight health-check endpoint."""
        return jsonify({"status": "ok"})

    app.register_blueprint(api_bp)

