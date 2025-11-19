"""Audio feature model definition."""

from datetime import datetime

from backend.app.extensions import db


class AudioFeature(db.Model):
    """Stores extracted audio features for a track."""

    __tablename__ = "audio_features"

    id = db.Column(db.Integer, primary_key=True)
    track_id = db.Column(
        db.String(64), db.ForeignKey("tracks.id"), unique=True, nullable=False
    )
    bpm = db.Column(db.Float, nullable=True)
    key = db.Column(db.String(32), nullable=True)
    key_strength = db.Column(db.Float, nullable=True)
    spectral_centroid = db.Column(db.Float, nullable=True)
    rms = db.Column(db.Float, nullable=True)
    peak_amplitude = db.Column(db.Float, nullable=True)
    mfcc = db.Column(db.JSON, nullable=True)
    rms_envelope = db.Column(db.JSON, nullable=True)
    spectral_flux = db.Column(db.Float, nullable=True)
    rolloff = db.Column(db.Float, nullable=True)
    flatness = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __init__(self, **kwargs):
        self.rms_envelope = kwargs.pop("rms_envelope", None)
        self.spectral_flux = kwargs.pop("spectral_flux", None)
        self.rolloff = kwargs.pop("rolloff", None)
        self.flatness = kwargs.pop("flatness", None)
        super().__init__(**kwargs)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "track_id": self.track_id,
            "bpm": self.bpm,
            "key": self.key,
            "key_strength": self.key_strength,
            "spectral_centroid": self.spectral_centroid,
            "rms": self.rms,
            "peak_amplitude": self.peak_amplitude,
            "mfcc": self.mfcc,
            "rms_envelope": self.rms_envelope,
            "spectral_flux": self.spectral_flux,
            "rolloff": self.rolloff,
            "flatness": self.flatness,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<AudioFeature track_id={self.track_id}>"

