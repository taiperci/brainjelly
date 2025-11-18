"""Track listing and detail endpoints."""

from flask import Blueprint, jsonify

from backend.app.models import Track

tracks_bp = Blueprint("tracks", __name__)


@tracks_bp.get("/tracks")
def list_tracks():
    """Return all tracks ordered by creation time."""
    tracks = Track.query.order_by(Track.created_at.desc()).all()
    data = [
        {
            "track_id": track.id,
            "original_filename": track.original_filename,
            "status": track.status,
            "samplerate": track.samplerate,
            "duration": track.duration,
            "error_message": track.error_message,
            "stored_path": track.stored_path,
            "created_at": track.created_at.isoformat() if track.created_at else None,
            "updated_at": track.updated_at.isoformat() if track.updated_at else None,
        }
        for track in tracks
    ]
    return jsonify({"success": True, "data": data})


@tracks_bp.get("/tracks/<track_id>")
def get_track(track_id: str):
    """Return a specific track."""
    track = Track.query.get(track_id)
    if track is None:
        return jsonify({"success": False, "error": "Track not found"}), 404
    return jsonify({"success": True, "data": track.to_dict()})

