"""Celery application factory for Brain Jelly."""

from celery import Celery
from flask import Flask

# Create celery instance (will be configured later)
celery = Celery("brainjelly")


def create_celery_app(app: Flask) -> Celery:
    """Create and configure a Celery instance from a Flask app."""
    # Load config from Flask app
    celery.conf.update(app.config)

    # Set default Redis URL if REDIS_URL is not provided
    if not app.config.get("REDIS_URL"):
        celery.conf.broker_url = "redis://localhost:6379/0"
        celery.conf.result_backend = "redis://localhost:6379/0"

    # Auto-discover tasks from backend/app/tasks
    celery.autodiscover_tasks(["backend.app.tasks"])

    class ContextTask(celery.Task):
        """Make celery tasks work with Flask app context."""

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask

    return celery

