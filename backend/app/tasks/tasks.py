"""Celery tasks for Brain Jelly."""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

from backend.app.audio import AudioLoaderError, load_audio
from backend.app.extensions import db
from backend.app.models import AudioFeature, Track
from backend.celery_app import celery
from flask import current_app

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
    extract_features.delay(track_id)
    return track_data


@celery.task(bind=True)
def extract_features(self, track_id):
    from backend.app.models import Track, AudioFeature

    with current_app.app_context():
        db.session.remove()

        track = Track.query.get(track_id)
        if not track:
            return {"error": "Track not found"}

        file_path = track.stored_path
        try:
            waveform, samplerate = load_audio(file_path)
        except AudioLoaderError as exc:
            track.status = "error"
            track.error_message = str(exc)
            db.session.commit()
            return {"error": str(exc)}

        rms = float(np.sqrt(np.mean(waveform**2)))
        spectral_centroid = float(np.mean(np.abs(np.fft.rfft(waveform))))
        peak_amplitude = float(np.max(np.abs(waveform)))

        mfcc = [0.0] * 13  # placeholder

        features = AudioFeature(
            track_id=track_id,
            rms=rms,
            spectral_centroid=spectral_centroid,
            peak_amplitude=peak_amplitude,
            mfcc=mfcc,
        )
        db.session.add(features)

        track.status = "features_ready"
        db.session.commit()

        return features.to_dict()


@celery.task(bind=True)
def compute_similarity_for_track(self, track_id):
    from backend.app.models import Track, AudioFeature, SimilarityScore

    with current_app.app_context():
        db.session.remove()

        source_track = Track.query.get(track_id)
        if not source_track:
            return {"error": "Track not found"}

        source_features = source_track.features
        if not source_features:
            return {"error": "No features for source track"}

        # Clear old scores
        SimilarityScore.query.filter_by(source_track_id=track_id).delete()

        all_features = AudioFeature.query.all()
        computed = 0

        for target in all_features:
            if target.track_id == track_id:
                continue

            dist = float(
                (source_features.rms - target.rms) ** 2
                + (
                    source_features.spectral_centroid
                    - target.spectral_centroid
                )
                ** 2
                + (source_features.peak_amplitude - target.peak_amplitude) ** 2
            )

            score = SimilarityScore(
                source_track_id=track_id,
                target_track_id=target.track_id,
                score=dist,
            )
            db.session.add(score)
            computed += 1

        source_track.has_similarity = True
        db.session.commit()

        return {"computed": computed}


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


# --- Similarity helpers ---------------------------------------------------- #

def _build_feature_vector(feature: AudioFeature) -> dict | None:
    """Return a dictionary of feature values if all required fields exist."""
    if (
        feature.rms is None
        or feature.spectral_centroid is None
        or feature.peak_amplitude is None
    ):
        return None

    if not isinstance(feature.mfcc, (list, tuple)):
        return None

    mfcc = np.asarray(feature.mfcc, dtype=np.float32)
    if mfcc.size == 0:
        return None

    return {
        "rms": float(feature.rms),
        "spectral_centroid": float(feature.spectral_centroid),
        "peak_amplitude": float(feature.peak_amplitude),
        "mfcc": mfcc,
    }


def _calculate_distance(source: dict, target: dict) -> float:
    """Weighted Euclidean distance between two feature vectors."""
    weights = {
        "rms": 1.0,
        "spectral_centroid": 1.0,
        "peak_amplitude": 1.0,
        "mfcc": 0.5,
    }

    total = 0.0

    total += weights["rms"] * (source["rms"] - target["rms"]) ** 2
    total += weights["spectral_centroid"] * (
        source["spectral_centroid"] - target["spectral_centroid"]
    ) ** 2
    total += weights["peak_amplitude"] * (
        source["peak_amplitude"] - target["peak_amplitude"]
    ) ** 2

    src_mfcc = source["mfcc"]
    tgt_mfcc = target["mfcc"]
    length = min(src_mfcc.size, tgt_mfcc.size)
    if length:
        diff = src_mfcc[:length] - tgt_mfcc[:length]
        total += weights["mfcc"] * float(np.sum(diff**2))

    return float(np.sqrt(total))

