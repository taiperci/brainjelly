"""Upload endpoints for Brain Jelly."""

from uuid import uuid4

from flask import Blueprint, jsonify, request

upload_bp = Blueprint("upload", __name__)


@upload_bp.post("/upload")
def upload_track():
    """Accept an audio upload and return a placeholder track identifier."""
    audio_file = request.files.get("file")
    if audio_file is None or audio_file.filename == "":
        return jsonify({"success": False, "error": "Audio file is required"}), 400

    # Placeholder logic: generate a fake track ID instead of storing the file.
    track_id = f"track-{uuid4().hex[:8]}"

    return jsonify({"success": True, "data": {"track_id": track_id}})

