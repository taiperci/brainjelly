"""Application extensions for Brain Jelly."""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def register_models() -> None:
    """Import models so SQLAlchemy is aware of them."""
    from backend.app import models  # noqa: F401

