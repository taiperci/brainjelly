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
HAS_FRAME_GENERATOR = False
HAS_SPECTRAL_SHAPE = False

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
        "FrameGenerator": hasattr(es, "FrameGenerator"),
        "SpectralFlux": hasattr(es, "SpectralFlux"),
        "RollOff": hasattr(es, "RollOff"),
        "SpectralFlatness": hasattr(es, "SpectralFlatness"),
    }
    HAS_MAXPEAK = hasattr(es, "MaxPeak")
    HAS_BPM = hasattr(es, "RhythmExtractor2013")
    HAS_FRAME_GENERATOR = AVAILABLE["FrameGenerator"]
    HAS_SPECTRAL_SHAPE = (
        AVAILABLE["Windowing"]
        and AVAILABLE["Spectrum"]
        and AVAILABLE["SpectralFlux"]
        and AVAILABLE["RollOff"]
        and AVAILABLE["SpectralFlatness"]
        and AVAILABLE["FrameGenerator"]
    )
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
    HAS_FRAME_GENERATOR = False
    HAS_SPECTRAL_SHAPE = False
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
        "rms_envelope": [],
        "spectral_flux": None,
        "rolloff": None,
        "flatness": None,
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

        if HAS_FRAME_GENERATOR and audio.size > 0:
            try:
                logger.info("Starting RMS envelope extraction for %s", path)
                frame_generator = es.FrameGenerator(
                    audio, frameSize=1024, hopSize=512, startFromZero=True
                )
                envelope_rms = es.RMS()
                envelope_values = [float(envelope_rms(frame)) for frame in frame_generator]

                if envelope_values:
                    features["rms_envelope"] = envelope_values
                    logger.info(
                        "RMS envelope extraction finished for %s (%d frames).",
                        path,
                        len(envelope_values),
                    )
                else:
                    logger.warning(
                        "RMS envelope extraction produced no frames for %s; keeping placeholder.",
                        path,
                    )
            except Exception as exc:  # noqa: broad-except
                logger.exception("RMS envelope extraction failed for %s: %s", path, exc)
        else:
            logger.info(
                "RMS envelope extraction unavailable (frame_generator=%s, audio_size=%s); keeping placeholder.",
                HAS_FRAME_GENERATOR,
                audio.size,
            )

        if HAS_SPECTRAL_SHAPE and audio.size > 0:
            try:
                logger.info("Starting spectral shape extraction for %s", path)
                frame_generator = es.FrameGenerator(
                    audio, frameSize=2048, hopSize=1024, startFromZero=True
                )
                window = es.Windowing(type="hann")
                spectrum = es.Spectrum()
                flux_algo = es.SpectralFlux()
                rolloff_algo = es.RollOff()
                flatness_algo = es.SpectralFlatness()

                flux_values = []
                rolloff_values = []
                flatness_values = []

                for frame in frame_generator:
                    windowed = window(frame)
                    spec = spectrum(windowed)
                    flux_values.append(float(flux_algo(spec)))
                    rolloff_values.append(float(rolloff_algo(spec)))
                    flatness_values.append(float(flatness_algo(spec)))

                if flux_values:
                    features["spectral_flux"] = float(np.mean(flux_values))
                    features["rolloff"] = float(np.mean(rolloff_values))
                    features["flatness"] = float(np.mean(flatness_values))
                    logger.info(
                        "Spectral shape extraction finished for %s (%d frames).",
                        path,
                        len(flux_values),
                    )
                else:
                    logger.warning(
                        "Spectral shape extraction produced no frames for %s; keeping placeholders.",
                        path,
                    )
            except Exception as exc:  # noqa: broad-except
                logger.exception("Spectral shape extraction failed for %s: %s", path, exc)
        else:
            logger.info(
                "Spectral shape extraction unavailable (has_shape=%s, audio_size=%s); keeping placeholders.",
                HAS_SPECTRAL_SHAPE,
                audio.size,
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

