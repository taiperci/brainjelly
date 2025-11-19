"""Celery tasks for Brain Jelly."""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

from backend.app.audio import AudioLoaderError, load_audio
from backend.app.audio.essentia_extraction import ESSENTIA_AVAILABLE, essentia_extraction
from backend.app.extensions import db
from backend.app.models import AudioFeature, Track
from backend.celery_app import celery
from flask import current_app
from sqlalchemy.orm import scoped_session, sessionmaker

logger = logging.getLogger(__name__)

@celery.task(name="ping")
def ping():
    """Lightweight ping task for Celery health checks."""
    return "pong"


@celery.task
def add(x: int, y: int) -> int:
    """Simple math task for testing Celery."""
    return x + y


@celery.task(bind=True)
def process_audio(self, track_id: str, file_path: str) -> dict:
    """Load audio file and extract basic metadata."""
    with current_app.app_context():
        try:
            file_path_obj = Path(file_path)
            waveform, samplerate = load_audio(file_path_obj)
            duration = waveform.size / float(samplerate)

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
            extract_features.delay(track_id, file_path)
            db.session.commit()
            return track_data
        except AudioLoaderError as exc:
            logger.warning(
                "process_audio failed to decode %s (%s): %s",
                track_id,
                file_path,
                exc,
            )
            db.session.rollback()
            return _handle_processing_error(track_id, exc)
        except Exception as exc:  # noqa: broad-except
            logger.exception("Unexpected error decoding %s: %s", track_id, exc)
            db.session.rollback()
            raise
        finally:
            db.session.remove()


def basic_extraction(track_path):
    """Extract basic audio features from a track file."""
    waveform, samplerate = load_audio(track_path)

    rms = float(np.sqrt(np.mean(waveform**2)))
    spectral_centroid = float(np.mean(np.abs(np.fft.rfft(waveform))))
    peak_amplitude = float(np.max(np.abs(waveform)))

    mfcc = [0.0] * 13  # placeholder

    placeholder_features = {
        "spectral_centroid": spectral_centroid,
        "rms": rms,
        "peak_amplitude": peak_amplitude,
        "mfcc": mfcc,
        "bpm": None,
        "key": None,
        "key_strength": None,
    }

    current_app.logger.info(f"Essentia available: {ESSENTIA_AVAILABLE}")

    if ESSENTIA_AVAILABLE:
        current_app.logger.info("Using Essentia extraction")
        essentia_features = essentia_extraction(track_path) or {}
        if essentia_features:
            placeholder_features.update(
                {key: value for key, value in essentia_features.items() if value is not None}
            )
        else:
            current_app.logger.info("Essentia returned no features; using placeholders.")

    return placeholder_features


@celery.task(bind=True)
def extract_features(self, track_id, track_path):
    from backend.app.models import Track, AudioFeature

    with current_app.app_context():
        Session = scoped_session(sessionmaker(bind=db.engine))
        session = Session()
        try:
            track = session.query(Track).get(track_id)
            if not track:
                return {"error": "Track not found"}

            try:
                features = basic_extraction(track_path)
            except AudioLoaderError as exc:
                track.status = "error"
                track.error_message = str(exc)
                session.commit()
                return {"error": str(exc)}

            audio_feature = AudioFeature(
                track_id=track_id,
                rms=features["rms"],
                spectral_centroid=features["spectral_centroid"],
                peak_amplitude=features["peak_amplitude"],
                mfcc=features["mfcc"],
                bpm=features["bpm"],
                key=features["key"],
                key_strength=features["key_strength"],
            )
            session.add(audio_feature)

            track.status = "features_ready"

            response = {
                "id": audio_feature.id,
                "track_id": audio_feature.track_id,
                "spectral_centroid": audio_feature.spectral_centroid,
                "rms": audio_feature.rms,
                "peak_amplitude": audio_feature.peak_amplitude,
                "mfcc": audio_feature.mfcc,
            }

            session.commit()

            # Trigger similarity generation for this track
            compute_similarity_for_track.delay(track_id)

            return response
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
            Session.remove()


@celery.task(bind=True)
def compute_similarity_for_track(self, track_id):
    from backend.app.models import Track, AudioFeature, SimilarityScore

    with current_app.app_context():
        Session = scoped_session(sessionmaker(bind=db.engine))
        session = Session()
        try:
            source_track = session.query(Track).get(track_id)
            if source_track is None:
                return {"error": "missing source track"}

            source_features = source_track.features
            if source_features is None:
                return {"error": "No features for source track"}

            source_values = _extract_basic_feature_values(source_features)
            if source_values is None:
                return {"error": "Incomplete source features"}

            # Clear old scores
            session.query(SimilarityScore).filter_by(source_track_id=track_id).delete()

            target_vectors = []
            all_features = session.query(AudioFeature).all()
            computed = 0

            for target in all_features:
                if target.track_id == track_id:
                    continue

                target_values = _extract_basic_feature_values(target)
                if target_values is None:
                    continue

                target_vectors.append(
                    {
                        "track_id": target.track_id,
                        **target_values,
                    }
                )

            for target in target_vectors:
                dist = float(
                    (source_values["rms"] - target["rms"]) ** 2
                    + (
                        source_values["spectral_centroid"]
                        - target["spectral_centroid"]
                    )
                    ** 2
                    + (
                        source_values["peak_amplitude"]
                        - target["peak_amplitude"]
                    )
                    ** 2
                )

                score = SimilarityScore(
                    source_track_id=track_id,
                    target_track_id=target["track_id"],
                    score=dist,
                )
                session.add(score)
                computed += 1

            source_track.has_similarity = True
            session.commit()

            return {"computed": computed}
        except Exception as exc:
            session.rollback()
            logger.exception("compute_similarity_for_track failed: %s", exc)
            raise
        finally:
            session.close()
            Session.remove()


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


def _extract_basic_feature_values(feature: AudioFeature) -> dict | None:
    if (
        feature.rms is None
        or feature.spectral_centroid is None
        or feature.peak_amplitude is None
    ):
        return None

    return {
        "rms": float(feature.rms),
        "spectral_centroid": float(feature.spectral_centroid),
        "peak_amplitude": float(feature.peak_amplitude),
    }

