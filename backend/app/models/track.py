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
    has_similarity = db.Column(db.Boolean, default=False, nullable=False)
    features = db.relationship(
        "AudioFeature", uselist=False, backref="track", cascade="all, delete-orphan"
    )
    similarity_sources = db.relationship(
        "SimilarityScore",
        foreign_keys="SimilarityScore.source_track_id",
        backref="source_track",
        cascade="all, delete-orphan",
    )
    similarity_targets = db.relationship(
        "SimilarityScore",
        foreign_keys="SimilarityScore.target_track_id",
        backref="target_track",
        cascade="all, delete-orphan",
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def to_dict(self) -> dict:
        """Serialize the track for API responses."""
        data = {
            "track_id": self.id,
            "status": self.status,
            "original_filename": self.original_filename,
            "stored_path": self.stored_path,
            "samplerate": self.samplerate,
            "duration": self.duration,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "has_similarity": bool(self.has_similarity),
        }
        # Include features if available
        if self.features:
            data["features"] = self.features.to_dict()
        else:
            data["features"] = None
        return data

    def __repr__(self) -> str:
        return f"<Track id={self.id} status={self.status}>"

