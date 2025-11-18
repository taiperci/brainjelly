"""Similarity score model definition."""

from datetime import datetime

from backend.app.extensions import db


class SimilarityScore(db.Model):
    """Stores similarity between two tracks."""

    __tablename__ = "similarity_scores"

    id = db.Column(db.Integer, primary_key=True)
    source_track_id = db.Column(
        db.String(64), db.ForeignKey("tracks.id"), nullable=False
    )
    target_track_id = db.Column(
        db.String(64), db.ForeignKey("tracks.id"), nullable=False
    )
    score = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        db.UniqueConstraint(
            "source_track_id",
            "target_track_id",
            name="uq_similarity_source_target",
        ),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_track_id": self.source_track_id,
            "target_track_id": self.target_track_id,
            "score": self.score,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

