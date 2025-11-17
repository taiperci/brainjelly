"""Track listing and detail endpoints."""

from flask import Blueprint, jsonify

tracks_bp = Blueprint("tracks", __name__)

PLACEHOLDER_TRACKS = [
    {"id": "track-1", "title": "Placeholder Track 1", "status": "processing"},
    {"id": "track-2", "title": "Placeholder Track 2", "status": "ready"},
]


@tracks_bp.get("/tracks")
def list_tracks():
    """Return all placeholder tracks."""
    return jsonify({"success": True, "data": PLACEHOLDER_TRACKS})


@tracks_bp.get("/tracks/<track_id>")
def get_track(track_id: str):
    """Return a specific placeholder track."""
    track = next((item for item in PLACEHOLDER_TRACKS if item["id"] == track_id), None)
    if track is None:
        return jsonify({"success": False, "error": "Track not found"}), 404
    return jsonify({"success": True, "data": track})

