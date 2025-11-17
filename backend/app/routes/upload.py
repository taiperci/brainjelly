"""Upload endpoints for Brain Jelly."""

from pathlib import Path
from uuid import uuid4

from flask import Blueprint, jsonify, request

from backend.app.state import UPLOAD_STATE
from backend.app.tasks.tasks import process_audio

upload_bp = Blueprint("upload", __name__)

# Upload directory
UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@upload_bp.post("/upload")
def upload_track():
    """Accept an audio upload, save the file, and dispatch Celery task."""
    audio_file = request.files.get("file")
    if audio_file is None or audio_file.filename == "":
        return jsonify({"success": False, "error": "Audio file is required"}), 400

    # Generate track ID
    track_id = f"track-{uuid4().hex[:8]}"

    # Create track-specific directory
    track_dir = UPLOAD_DIR / track_id
    track_dir.mkdir(exist_ok=True)

    # Save the file
    original_filename = audio_file.filename
    saved_file_path = track_dir / original_filename
    audio_file.save(str(saved_file_path))

    # Update state
    UPLOAD_STATE[track_id] = {"status": "processing"}

    # Dispatch Celery task
    process_audio.delay(track_id, str(saved_file_path))

    return jsonify({"success": True, "data": {"track_id": track_id}})

