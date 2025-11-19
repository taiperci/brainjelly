"""Essentia-based audio feature extraction."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

import numpy as np

HAS_MAXPEAK = False
HAS_MFCC = False
HAS_BPM = False
HAS_KEY = False

try:
    import essentia  # noqa: F401
    import essentia.standard as es

    AVAILABLE = {
        "MonoLoader": hasattr(es, "MonoLoader"),
        "RMS": hasattr(es, "RMS"),
        "SpectralCentroidTime": hasattr(es, "SpectralCentroidTime"),
        "Spectrum": hasattr(es, "Spectrum"),
        "Windowing": hasattr(es, "Windowing"),
        "MFCC": hasattr(es, "MFCC"),
    }
    HAS_MAXPEAK = hasattr(es, "MaxPeak")
    HAS_BPM = hasattr(es, "RhythmExtractor2013")
    HAS_MFCC = (
        AVAILABLE["MonoLoader"]
        and AVAILABLE["Windowing"]
        and AVAILABLE["Spectrum"]
        and AVAILABLE["MFCC"]
    )
    ESSENTIA_AVAILABLE = (
        AVAILABLE["MonoLoader"]
        and AVAILABLE["RMS"]
        and AVAILABLE["SpectralCentroidTime"]
    )
except Exception:  # pragma: no cover - dependency not installed in CI
    ESSENTIA_AVAILABLE = False
    HAS_MAXPEAK = False
    HAS_MFCC = False
    HAS_BPM = False
    es = None

try:
    from essentia.standard import KeyExtractor

    HAS_KEY = True
except ImportError:
    HAS_KEY = False
    KeyExtractor = None


logger = logging.getLogger(__name__)


def _placeholder_features() -> Dict[str, Any]:
    return {
        "spectral_centroid": None,
        "rms": None,
        "peak_amplitude": None,
        "mfcc": [0.0] * 13,
        "bpm": None,
        "key": None,
        "key_strength": None,
    }


def essentia_extraction(track_path):
    """
    Minimal Essentia DSP logic.

    Returns the standard feature dict, or an empty dict to signal fallback.
    """
    if not ESSENTIA_AVAILABLE:
        logger.info("Essentia not available; skipping extraction.")
        return {}

    path = Path(track_path)
    if path.suffix.lower() != ".wav":
        logger.info("Essentia only processes WAV files (got %s); skipping.", path.suffix)
        return {}

    logger.info("Starting Essentia extraction for %s", track_path)

    try:
        loader = es.MonoLoader(filename=str(path))
        audio = loader()

        if audio.size == 0:
            logger.warning("Empty audio buffer; skipping.")
            return {}

        # Correct DSP wiring
        rms_algo = es.RMS()
        centroid_algo = es.SpectralCentroidTime()
        if HAS_MAXPEAK:
            peak_algo = es.MaxPeak()
            peak_value, _ = peak_algo(audio)
            peak_value = float(peak_value)
        else:
            peak_value = float(max(abs(audio)))

        rms_value = float(rms_algo(audio))

        # SpectralCentroidTime works directly on the audio frame
        centroid_value = float(centroid_algo(audio))

        logger.info("Essentia DSP completed successfully.")

        features = _placeholder_features()
        features.update(
            {
                "spectral_centroid": centroid_value,
                "rms": rms_value,
                "peak_amplitude": peak_value,
            }
        )

        if HAS_MFCC and audio.size > 0:
            try:
                logger.info("Starting Essentia MFCC extraction for %s", path)
                frame_generator = es.FrameGenerator(
                    audio, frameSize=2048, hopSize=1024, startFromZero=True
                )
                window = es.Windowing(type="hann")
                spectrum = es.Spectrum()
                mfcc_algo = es.MFCC(numberCoefficients=13)

                mfcc_frames = []
                for frame in frame_generator:
                    windowed = window(frame)
                    spec = spectrum(windowed)
                    _, coeffs = mfcc_algo(spec)
                    mfcc_frames.append(np.asarray(coeffs, dtype=np.float32))

                if mfcc_frames:
                    mean_mfcc = np.mean(mfcc_frames, axis=0)
                    features["mfcc"] = [float(value) for value in mean_mfcc.tolist()]
                    logger.info(
                        "Essentia MFCC extraction completed with %d frames.", len(mfcc_frames)
                    )
                else:
                    logger.warning(
                        "Essentia MFCC extraction produced no frames; keeping placeholder."
                    )
            except Exception as exc:  # noqa: broad-except
                logger.exception("Essentia MFCC extraction failed: %s", exc)

        if HAS_BPM:
            try:
                logger.info("Starting Essentia BPM extraction for %s", path)
                rhythm_extractor = es.RhythmExtractor2013(method="multifeature")
                bpm_value, _, _, _, _ = rhythm_extractor(audio)
                features["bpm"] = float(bpm_value)
                logger.info("Essentia BPM extraction finished for %s", path)
            except Exception as exc:  # noqa: broad-except
                logger.exception("Essentia BPM extraction failed: %s", exc)
        else:
            logger.info("Essentia BPM extractor unavailable; keeping placeholder.")

        if ESSENTIA_AVAILABLE and HAS_KEY and path.suffix.lower() == ".wav":
            try:
                logger.info("Starting key extraction for %s", path)
                key_extractor = KeyExtractor()
                key_value, scale, strength = key_extractor(audio)
                logger.info(
                    "Key extractor raw output for %s: key=%s scale=%s strength=%s",
                    path,
                    key_value,
                    scale,
                    strength,
                )
                formatted_key = (
                    f"{key_value}" if scale.lower() == "major" else f"{key_value}m"
                )
                features["key"] = formatted_key
                features["key_strength"] = float(strength)
                logger.info("Key extraction finished for %s", path)
            except Exception as exc:  # noqa: broad-except
                logger.exception("Essentia key extraction failed: %s", exc)
        else:
            logger.info(
                "Essentia key extraction unavailable (available=%s, has_key=%s, wav=%s); keeping placeholder.",
                ESSENTIA_AVAILABLE,
                HAS_KEY,
                path.suffix.lower() == ".wav",
            )

        return features

    except Exception as exc:  # noqa: broad-except
        logger.exception("Essentia extraction failed: %s", exc)
        return {}

