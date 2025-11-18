"""Health check endpoints for Brain Jelly."""

from flask import Blueprint, jsonify

from backend.app.tasks.tasks import ping

health_bp = Blueprint("health", __name__)


@health_bp.get("/health/celery")
def celery_health():
    """Check Celery worker availability."""
    try:
        # Dispatch a lightweight test task
        result = ping.delay()
        
        # Wait briefly for the result
        task_result = result.get(timeout=2)
        
        if task_result == "pong":
            return jsonify({"success": True, "celery": "ok"})
        else:
            return jsonify({"success": False, "celery": "unavailable"})
    except Exception:
        return jsonify({"success": False, "celery": "unavailable"})

