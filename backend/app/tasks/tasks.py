"""Celery tasks for Brain Jelly."""

import audioread
from pathlib import Path

from backend.app.state import UPLOAD_STATE
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
                error_state = {"status": "error", "message": str(audioread_error)}
                UPLOAD_STATE[track_id] = error_state
                print(f"Error processing audio for track {track_id}: {audioread_error}")
                return error_state
    else:
        # No soundfile available, use audioread
        try:
            with audioread.audio_open(str(file_path_obj)) as audio:
                samplerate = audio.samplerate
                duration = audio.duration
        except Exception as e:
            error_state = {"status": "error", "message": str(e)}
            UPLOAD_STATE[track_id] = error_state
            print(f"Error processing audio for track {track_id}: {e}")
            return error_state
    
    # Success - update state
    print(f"Loaded file: {file_path}, samplerate={samplerate}, duration={duration:.2f}")
    
    state_data = {
        "status": "loaded",
        "file_path": file_path,
        "duration": duration,
        "samplerate": samplerate
    }
    UPLOAD_STATE[track_id] = state_data
    
    return state_data

