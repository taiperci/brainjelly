"""Celery tasks for Brain Jelly."""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

from backend.app.audio import (
    AudioLoaderError,
    load_audio,
)
from backend.app.extensions import db
from backend.app.models import AudioFeature, Track
from backend.celery_app import celery

logger = logging.getLogger(__name__)


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
    try:
        waveform, samplerate = load_audio(file_path_obj)
        duration = waveform.size / float(samplerate)
    except AudioLoaderError as exc:
        logger.warning(
            "process_audio failed to decode %s (%s): %s",
            track_id,
            file_path,
            exc,
        )
        return _handle_processing_error(track_id, exc)
    except Exception as exc:  # noqa: broad-except
        logger.exception("Unexpected error decoding %s: %s", track_id, exc)
        return _handle_processing_error(track_id, exc)

    logger.info(
        "Decoded track %s (%s): samplerate=%s, duration=%.2fs",
        track_id,
        file_path,
        samplerate,
        duration,
    )

    track_data = _update_track_record(
        track_id,
        status="loaded",
        samplerate=int(samplerate) if samplerate is not None else None,
        duration=duration,
        error_message=None,
    )
    extract_features.delay(track_id, str(file_path_obj))
    return track_data


@celery.task(name="backend.app.tasks.tasks.extract_features")
def extract_features(track_id: str, file_path: str) -> dict:
    """Extract placeholder audio features."""
    track = Track.query.get(track_id)
    if track is None:
        return {"status": "error", "message": f"Track {track_id} not found"}

    track.status = "extracting"
    track.error_message = None
    db.session.commit()

    try:
        waveform, samplerate = load_audio(file_path)
        if waveform.size == 0:
            waveform = np.zeros(1, dtype=np.float32)

        spectral_centroid = float(np.mean(np.abs(waveform)))
        rms = float(np.sqrt(np.mean(np.square(waveform))))
        peak_amplitude = float(np.max(np.abs(waveform)))
        mfcc = [0.0] * 13

        features = AudioFeature.query.filter_by(track_id=track_id).one_or_none()
        if features is None:
            features = AudioFeature(track_id=track_id)
            db.session.add(features)

        features.spectral_centroid = spectral_centroid
        features.rms = rms
        features.peak_amplitude = peak_amplitude
        features.mfcc = mfcc

        track.status = "features_ready"
        track.error_message = None
        db.session.commit()

        logger.info("Features ready for track %s", track_id)
        return features.to_dict()
    except AudioLoaderError as exc:
        logger.warning(
            "extract_features failed to decode %s (%s): %s",
            track_id,
            file_path,
            exc,
        )
        db.session.rollback()
        return _set_track_error(track_id, str(exc))
    except Exception as exc:  # noqa: broad-except
        logger.exception("Error extracting features for %s: %s", track_id, exc)
        db.session.rollback()
        return _set_track_error(track_id, str(exc))


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
    logger.warning("Error processing audio for track %s: %s", track_id, exc)
    return _update_track_record(
        track_id,
        status="error",
        samplerate=None,
        duration=None,
        error_message=str(exc),
    )


def _set_track_error(track_id: str, message: str) -> dict:
    """Set track status to error."""
    track = Track.query.get(track_id)
    if track:
        track.status = "error"
        track.error_message = message
        db.session.commit()
    return {"status": "error", "message": message, "track_id": track_id}

