from backend.app import create_app
from backend.celery_app import create_celery_app

flask_app = create_app()
celery = create_celery_app(flask_app)

