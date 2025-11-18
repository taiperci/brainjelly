"""Track listing and detail endpoints."""

from flask import Blueprint, jsonify

from backend.app.models import SimilarityScore, Track

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


@tracks_bp.get("/tracks/<track_id>/features")
def get_track_features(track_id: str):
    """Return extracted features for a specific track."""
    track = Track.query.get(track_id)
    if track is None:
        return jsonify({"success": False, "error": "Track not found"}), 404

    if not track.features:
        return jsonify({"success": False, "error": "No features available"}), 404

    return jsonify({"success": True, "data": track.features.to_dict()})


@tracks_bp.get("/tracks/<track_id>/similar")
def get_similar_tracks(track_id: str):
    """Return the top 20 similar tracks for the given track."""
    track = Track.query.get(track_id)
    if track is None:
        return jsonify({"success": False, "error": "Track not found"}), 404

    scores = (
        SimilarityScore.query.filter_by(source_track_id=track_id)
        .join(Track, SimilarityScore.target_track_id == Track.id)
        .order_by(SimilarityScore.score.desc())
        .limit(20)
        .all()
    )

    data = []
    for score in scores:
        target = score.target_track
        data.append(
            {
                "target_track_id": score.target_track_id,
                "score": score.score,
                "original_filename": target.original_filename if target else None,
                "duration": target.duration if target else None,
            }
        )

    return jsonify({"success": True, "data": data})

