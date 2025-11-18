"""Track listing and detail endpoints."""

from flask import Blueprint, jsonify

from backend.app.models import Track

tracks_bp = Blueprint("tracks", __name__)


@tracks_bp.get("/tracks")
def list_tracks():
    """Return the latest uploaded tracks."""
    tracks = (
        Track.query.order_by(Track.created_at.desc())
        .limit(50)
        .all()
    )
    data = [track.to_dict() for track in tracks]
    return jsonify({"success": True, "data": data})


@tracks_bp.get("/tracks/<track_id>")
def get_track(track_id: str):
    """Return a specific track."""
    track = Track.query.get(track_id)
    if track is None:
        return jsonify({"success": False, "error": "Track not found"}), 404
    return jsonify({"success": True, "data": track.to_dict()})

