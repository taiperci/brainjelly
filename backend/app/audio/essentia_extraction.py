"""Essentia-based audio feature extraction."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

HAS_MAXPEAK = False

try:
    import essentia  # noqa: F401
    import essentia.standard as es

    AVAILABLE = {
        "MonoLoader": hasattr(es, "MonoLoader"),
        "RMS": hasattr(es, "RMS"),
        "SpectralCentroidTime": hasattr(es, "SpectralCentroidTime"),
        "Spectrum": hasattr(es, "Spectrum"),
    }
    HAS_MAXPEAK = hasattr(es, "MaxPeak")
    ESSENTIA_AVAILABLE = (
        AVAILABLE["MonoLoader"]
        and AVAILABLE["RMS"]
        and AVAILABLE["SpectralCentroidTime"]
    )
except Exception:  # pragma: no cover - dependency not installed in CI
    ESSENTIA_AVAILABLE = False
    HAS_MAXPEAK = False
    es = None


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
        return features

    except Exception as exc:  # noqa: broad-except
        logger.exception("Essentia extraction failed: %s", exc)
        return {}

