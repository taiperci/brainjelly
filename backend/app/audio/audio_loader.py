"""Robust audio loading utilities."""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Tuple

import audioread
import numpy as np
import soundfile as sf

logger = logging.getLogger(__name__)

SUPPORTED_FORMATS = {".wav", ".mp3", ".aif", ".aiff", ".flac"}
MIN_DURATION_SECONDS = 0.5


class AudioLoaderError(Exception):
    """Base class for loader errors."""


class UnsupportedFormatError(AudioLoaderError):
    """Raised when attempting to decode an unsupported format."""


class AudioDecodeError(AudioLoaderError):
    """Raised when decoding fails."""


class EmptyAudioError(AudioLoaderError):
    """Raised when decoding produced no samples."""


class AudioTooShortError(AudioLoaderError):
    """Raised when decoded audio is shorter than the minimum duration."""


def load_audio(path: str | Path) -> Tuple[np.ndarray, int]:
    """Decode audio from disk, normalised to mono float32."""
    source_path = Path(path)
    if not source_path.exists():
        raise AudioDecodeError(f"Audio file not found: {source_path}")

    ext = source_path.suffix.lower()
    if ext not in SUPPORTED_FORMATS:
        raise UnsupportedFormatError(
            f"Unsupported audio format '{ext}'. "
            f"Supported formats: {', '.join(sorted(SUPPORTED_FORMATS))}"
        )

    loaders = [
        ("soundfile", _load_with_soundfile),
        ("audioread", _load_with_audioread),
        ("ffmpeg", _load_with_ffmpeg),
    ]

    last_error: Exception | None = None
    for name, loader in loaders:
        try:
            logger.debug("Attempting %s loader for %s", name, source_path)
            audio, samplerate = loader(source_path)
            audio, samplerate = _post_process(audio, samplerate)
            logger.debug(
                "%s loader succeeded for %s (sr=%s, samples=%s)",
                name,
                source_path,
                samplerate,
                audio.size,
            )
            return audio, samplerate
        except AudioLoaderError as exc:
            last_error = exc
            logger.debug("%s loader raised %s", name, exc, exc_info=True)
        except Exception as exc:  # noqa: broad-except
            last_error = exc
            logger.debug(
                "%s loader encountered unexpected error: %s", name, exc, exc_info=True
            )

    raise AudioDecodeError(
        f"Unable to decode audio file {source_path}: {last_error}"
    ) from last_error


def _load_with_soundfile(path: Path) -> Tuple[np.ndarray, int]:
    data, samplerate = sf.read(path, dtype="float32", always_2d=False)
    return np.asarray(data), int(samplerate)


def _load_with_audioread(path: Path) -> Tuple[np.ndarray, int]:
    with audioread.audio_open(str(path)) as reader:
        samplerate = reader.samplerate or 44100
        buffers: list[np.ndarray] = []
        for chunk in reader:
            if not chunk:
                continue
            np_chunk = np.frombuffer(chunk, dtype=np.int16).astype(np.float32)
            buffers.append(np_chunk / 32768.0)
        if not buffers:
            raise EmptyAudioError("audioread produced no samples")
        audio = np.concatenate(buffers)
        return audio, int(samplerate)


def _load_with_ffmpeg(path: Path) -> Tuple[np.ndarray, int]:
    ffmpeg_binary = os.getenv("FFMPEG_BINARY", "ffmpeg")
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        cmd = [
            ffmpeg_binary,
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(path),
            "-ac",
            "1",
            "-ar",
            "44100",
            "-f",
            "wav",
            str(tmp_path),
        ]
        subprocess.run(cmd, check=True)
        data, samplerate = sf.read(tmp_path, dtype="float32", always_2d=False)
        return np.asarray(data), int(samplerate)
    except subprocess.CalledProcessError as exc:
        raise AudioDecodeError(f"ffmpeg failed to decode {path}") from exc
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            logger.debug("Failed to delete temp file %s", tmp_path, exc_info=True)


def _post_process(audio: np.ndarray, samplerate: int) -> Tuple[np.ndarray, int]:
    if audio.size == 0:
        raise EmptyAudioError("Decoded audio is empty")

    if audio.ndim > 1:
        audio = np.mean(audio, axis=1)

    audio = audio.astype(np.float32, copy=False)
    duration = audio.size / float(samplerate)

    if duration <= 0:
        raise EmptyAudioError("Decoded audio has zero duration")
    if duration < MIN_DURATION_SECONDS:
        raise AudioTooShortError(
            f"Audio duration {duration:.2f}s is less than "
            f"minimum {MIN_DURATION_SECONDS}s"
        )

    return audio, samplerate

