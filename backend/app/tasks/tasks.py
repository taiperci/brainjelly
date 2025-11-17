"""Celery tasks for Brain Jelly."""

import time

from backend.app.state import UPLOAD_STATE
from backend.celery_app import celery


@celery.task
def add(x: int, y: int) -> int:
    """Simple math task for testing Celery."""
    return x + y


@celery.task
def process_audio(track_id: str, file_path: str) -> dict:
    """Placeholder audio processing task."""
    print(f"Processing audio for track {track_id} at {file_path}")
    
    # Simulate processing with a short sleep
    time.sleep(2)
    
    # Update state
    UPLOAD_STATE[track_id] = {"status": "done"}
    
    return {"track_id": track_id, "status": "processed"}

