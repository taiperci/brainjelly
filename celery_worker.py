from backend.app import create_app

from backend.celery_app import celery

# Create Flask app
app = create_app()

# Bind the Celery instance to the Flask app context
celery.conf.update(app.config)

# Important: configure broker + backend explicitly
celery.conf.broker_url = app.config["CELERY_BROKER_URL"]
celery.conf.result_backend = app.config["CELERY_RESULT_BACKEND"]

# So Celery auto-discovers tasks AFTER Flask is ready
celery.autodiscover_tasks(["backend.app"])

