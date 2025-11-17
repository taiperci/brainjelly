"""Route registration for Brain Jelly."""

from flask import Flask, jsonify

from .api import api_bp


def register_routes(app: Flask) -> None:
    """Register application blueprints and root routes."""
    app.register_blueprint(api_bp, url_prefix="/api")

    @app.get("/")
    def root():
        """Entry point for the API."""
        return jsonify({"message": "Welcome to the Brain Jelly API"})

