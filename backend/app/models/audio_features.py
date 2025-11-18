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
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "track_id": self.track_id,
            "spectral_centroid": self.spectral_centroid,
            "rms": self.rms,
            "peak_amplitude": self.peak_amplitude,
            "mfcc": self.mfcc,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<AudioFeature track_id={self.track_id}>"

