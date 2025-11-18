"""Celery tasks for Brain Jelly."""

import audioread
import numpy as np
from pathlib import Path

from backend.app.extensions import db
from backend.app.models import AudioFeature, Track
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
        waveform, samplerate = _load_audio_waveform(file_path)
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

        return features.to_dict()
    except Exception as exc:
        db.session.rollback()
        print(f"Error extracting features for track {track_id}: {exc}")
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
    print(f"Error processing audio for track {track_id}: {exc}")
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


def _load_audio_waveform(file_path: str) -> tuple[np.ndarray, int]:
    """Load audio data as a mono numpy array."""
    last_error: Exception | None = None
    if HAS_SOUNDFILE:
        try:
            data, samplerate = sf.read(file_path, always_2d=False)
            data = np.asarray(data, dtype=np.float32)
            if data.ndim > 1:
                data = np.mean(data, axis=1)
            return data, int(samplerate)
        except Exception as exc:
            last_error = exc

    try:
        with audioread.audio_open(file_path) as audio:
            samplerate = audio.samplerate or 44100
            buffers: list[np.ndarray] = []
            for buf in audio:
                np_buf = np.frombuffer(buf, dtype=np.int16).astype(np.float32)
                if np_buf.size:
                    buffers.append(np_buf / 32768.0)
            if buffers:
                data = np.concatenate(buffers)
            else:
                data = np.zeros(1, dtype=np.float32)
            return data, int(samplerate)
    except Exception as exc:
        raise last_error or exc

