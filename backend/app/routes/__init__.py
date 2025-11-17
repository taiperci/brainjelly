"""Route registration helpers for Brain Jelly."""

from flask import Flask, jsonify


def register_root_routes(app: Flask) -> None:
    """Register routes that live on the root domain."""

    @app.get("/")
    def root():
        """Entry point for the API."""
        return jsonify({"success": True, "data": {"message": "Welcome to the Brain Jelly API"}})

