"""Celery tasks for Brain Jelly."""

import audioread
from pathlib import Path

from backend.app.extensions import db
from backend.app.models import Track
from backend.celery_app import celery

try:
    import soundfile as sf
    HAS_SOUNDFILE = True
except ImportError:
    HAS_SOUNDFILE = False


@celery.task(name="ping")
def ping():
    """Lightweight ping task for Celery health checks."""
    return "pong"


@celery.task
def add(x: int, y: int) -> int:
    """Simple math task for testing Celery."""
    return x + y


@celery.task
def process_audio(track_id: str, file_path: str) -> dict:
    """Load audio file and extract basic metadata."""
    file_path_obj = Path(file_path)
    samplerate = None
    duration = None
    
    # First try soundfile
    if HAS_SOUNDFILE:
        try:
            data, samplerate = sf.read(str(file_path_obj))
            duration = len(data) / samplerate
        except Exception as e:
            # If soundfile fails, try audioread as fallback
            try:
                with audioread.audio_open(str(file_path_obj)) as audio:
                    samplerate = audio.samplerate
                    duration = audio.duration
            except Exception as audioread_error:
                return _handle_processing_error(track_id, audioread_error)
    else:
        # No soundfile available, use audioread
        try:
            with audioread.audio_open(str(file_path_obj)) as audio:
                samplerate = audio.samplerate
                duration = audio.duration
        except Exception as e:
            return _handle_processing_error(track_id, e)
    
    # Success - update state
    print(f"Loaded file: {file_path}, samplerate={samplerate}, duration={duration:.2f}")
    
    return _update_track_record(
        track_id,
        status="loaded",
        samplerate=int(samplerate) if samplerate is not None else None,
        duration=duration,
        error_message=None,
    )


def _update_track_record(
    track_id: str,
    status: str,
    samplerate: int | None,
    duration: float | None,
    error_message: str | None,
) -> dict:
    """Persist track metadata updates and return a response dict."""
    track = Track.query.get(track_id)
    if track is None:
        return {
            "track_id": track_id,
            "status": status,
            "samplerate": samplerate,
            "duration": duration,
            "error_message": error_message,
        }

    track.status = status
    track.samplerate = samplerate
    track.duration = duration
    track.error_message = error_message

    db.session.commit()

    data = track.to_dict()
    return data


def _handle_processing_error(track_id: str, exc: Exception) -> dict:
    """Handle processing failure by updating track status."""
    print(f"Error processing audio for track {track_id}: {exc}")
    try:
        return _update_track_record(
            track_id,
            status="error",
            samplerate=None,
            duration=None,
            error_message=str(exc),
        )
    except Exception:
        # If track persistence also fails, still return minimal error info
        return {"status": "error", "message": str(exc), "track_id": track_id}

