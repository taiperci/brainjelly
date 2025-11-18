"""Upload endpoints for Brain Jelly."""

import logging
from pathlib import Path
from uuid import uuid4

from flask import Blueprint, jsonify, request

from backend.app.audio import AudioLoaderError, load_audio
from backend.app.extensions import db
from backend.app.models import Track
from backend.app.tasks.tasks import process_audio

upload_bp = Blueprint("upload", __name__)
logger = logging.getLogger(__name__)

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

    # Validate audio decoding before persisting
    try:
        load_audio(str(saved_file_path))
    except AudioLoaderError as exc:
        logger.warning("Upload failed audio validation for %s: %s", saved_file_path, exc)
        saved_file_path.unlink(missing_ok=True)
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"Unable to process audio file: {exc}",
                }
            ),
            400,
        )
    except Exception as exc:  # noqa: broad-except
        logger.exception("Unexpected error validating upload %s", saved_file_path)
        saved_file_path.unlink(missing_ok=True)
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Unexpected error while validating audio upload.",
                }
            ),
            500,
        )

    # Persist track metadata
    track = Track(
        id=track_id,
        original_filename=original_filename,
        stored_path=str(saved_file_path),
        status="processing",
    )
    db.session.add(track)
    db.session.commit()

    # Dispatch Celery task
    process_audio.delay(track_id, str(saved_file_path))

    return jsonify({"success": True, "data": {"track_id": track_id}})

