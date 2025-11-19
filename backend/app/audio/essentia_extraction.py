"""Essentia-based audio feature extraction."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

try:
    from essentia.standard import MaxPeak, MonoLoader, RMS, Spectrum, SpectralCentroidTime

    ESSENTIA_AVAILABLE = True
except ImportError:  # pragma: no cover - dependency not installed in CI
    ESSENTIA_AVAILABLE = False


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
        loader = MonoLoader(filename=str(path))
        audio = loader()

        if audio.size == 0:
            logger.warning("Empty audio buffer from Essentia loader; skipping.")
            return {}

        spectrum = Spectrum()
        spectral_centroid_algo = SpectralCentroidTime()
        rms_algo = RMS()
        max_peak_algo = MaxPeak()

        # Compute DSP metrics
        spec = spectrum(audio)
        centroid = float(spectral_centroid_algo(spec))
        rms_value = float(rms_algo(audio))
        peak_value, _ = max_peak_algo(audio)
        peak_value = float(peak_value)

        logger.info("Essentia DSP completed successfully.")
        placeholder = _placeholder_features()
        placeholder.update(
            {
                "spectral_centroid": centroid,
                "rms": rms_value,
                "peak_amplitude": peak_value,
            }
        )
        return placeholder
    except Exception as exc:  # noqa: broad-except
        logger.exception("Essentia extraction failed: %s", exc)
        return {}

