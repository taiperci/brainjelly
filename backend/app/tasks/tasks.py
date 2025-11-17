"""Celery tasks for Brain Jelly."""

from backend.celery_app import celery


@celery.task
def add(x: int, y: int) -> int:
    """Simple math task for testing Celery."""
    return x + y


@celery.task
def process_audio(track_id: str) -> dict:
    """Placeholder audio processing task."""
    print(f"Processing audio for track {track_id}")
    return {"track_id": track_id}

