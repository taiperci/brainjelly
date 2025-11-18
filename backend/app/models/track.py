"""Track model definition."""

from datetime import datetime

from backend.app.extensions import db


class Track(db.Model):
    """Represents an uploaded track and its processing state."""

    __tablename__ = "tracks"

    id = db.Column(db.String(64), primary_key=True)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_path = db.Column(db.String(1024), nullable=False)
    status = db.Column(db.String(64), nullable=False, default="uploaded")
    samplerate = db.Column(db.Integer, nullable=True)
    duration = db.Column(db.Float, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    features = db.relationship(
        "AudioFeature", uselist=False, backref="track", cascade="all, delete-orphan"
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def to_dict(self) -> dict:
        """Serialize the track for API responses."""
        return {
            "track_id": self.id,
            "status": self.status,
            "original_filename": self.original_filename,
            "stored_path": self.stored_path,
            "samplerate": self.samplerate,
            "duration": self.duration,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def __repr__(self) -> str:
        return f"<Track id={self.id} status={self.status}>"

