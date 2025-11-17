"""API blueprint containing version-neutral endpoints."""

from flask import Blueprint, jsonify

api_bp = Blueprint("api", __name__)


@api_bp.get("/health")
def health_check():
    """Lightweight health-check endpoint."""
    return jsonify({"success": True, "data": {"status": "ok"}})

